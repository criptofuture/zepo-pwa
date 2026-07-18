// zepo-companion · "Zepi", el asistente financiero dentro de Zepo (Max-only)
// Chat + insight-del-día vía Vertex AI (Gemini). Reusa el patrón GCP_SA_JSON de categorize-ai.
// Candado de plan SERVER-SIDE: lee users.plan con el JWT del usuario (RLS = solo su fila).

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { create as createJWT } from "https://deno.land/x/djwt@v3.0.2/mod.ts";
import { SYSTEM_PROMPT } from "./prompt.ts";
import { runQueryRecords } from "./tools.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const GCP_SA_JSON = Deno.env.get("GCP_SA_JSON")!;
const GCP_PROJECT = Deno.env.get("GCP_PROJECT") || "gen-lang-client-0934320964";
const GCP_LOCATION = Deno.env.get("GCP_LOCATION") || "us-central1";
const MODEL = Deno.env.get("ZEPI_MODEL") || "gemini-2.5-flash";

const MAX_MESSAGES = 12;        // historial que aceptamos del cliente
const MAX_MSG_CHARS = 1000;     // por mensaje
const MAX_SNAPSHOT_CHARS = 6000;
const MAX_TOOL_ROUNDS = 2;      // consultas históricas por turno (presupuesto de 60s del edge)

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, content-type, x-client-info, apikey",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

let _tokenCache: { token: string; exp: number } | null = null;

async function getAccessToken(): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  if (_tokenCache && _tokenCache.exp > now + 60) return _tokenCache.token;
  const sa = JSON.parse(GCP_SA_JSON);
  const pem = sa.private_key as string;
  const pemBody = pem.replace(/-----BEGIN PRIVATE KEY-----/g, "").replace(/-----END PRIVATE KEY-----/g, "").replace(/\s+/g, "");
  const der = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const cryptoKey = await crypto.subtle.importKey("pkcs8", der.buffer, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const jwt = await createJWT(
    { alg: "RS256", typ: "JWT", kid: sa.private_key_id },
    { iss: sa.client_email, scope: "https://www.googleapis.com/auth/cloud-platform", aud: "https://oauth2.googleapis.com/token", iat: now, exp: now + 3600 },
    cryptoKey,
  );
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion: jwt }),
  });
  if (!res.ok) throw new Error("oauth_failed: " + await res.text());
  const json = await res.json();
  _tokenCache = { token: json.access_token, exp: now + (json.expires_in || 3600) };
  return _tokenCache.token;
}

// Destinos navegables válidos (lista blanca compartida con el cliente — zepiGo)
const VALID_TARGETS = ["home","history","budgets","cuentas","dash","patrimonio","settings","plans","notifications","newExpense","spaces","paymethods","categories","recurring","export"];
// Screenshots de la guía (deben existir en /pwa/guide/<id>.webp)
const VALID_SHOTS = ["home","add-expense","split","budgets","budget-edit","cuentas","dash","history","patrimonio","spaces","paymethods","categories","settings","plans"];

const RESPONSE_SCHEMA = {
  type: "OBJECT",
  properties: {
    text: { type: "STRING" },
    title: { type: "STRING" },
    shot: { type: "STRING" },
    actions: {
      type: "ARRAY",
      items: {
        type: "OBJECT",
        properties: { label: { type: "STRING" }, target: { type: "STRING" } },
        required: ["label", "target"],
      },
    },
    // Consulta histórica (agente lector): el edge la ejecuta y re-llama al modelo.
    // El cliente NUNCA ve este campo — se resuelve server-side.
    tool: {
      type: "OBJECT",
      properties: {
        name: { type: "STRING" },
        date_from: { type: "STRING" },
        date_to: { type: "STRING" },
        category: { type: "STRING" },
        is_income: { type: "BOOLEAN" },
        search: { type: "STRING" },
        group_by: { type: "STRING" },
      },
      // Si el modelo emite tool, el schema lo OBLIGA a incluir las fechas
      // (sin esto las omitía y la consulta moría por formato).
      required: ["name", "date_from", "date_to"],
    },
  },
  required: ["text"],
};

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });
  if (req.method !== "POST") return new Response(JSON.stringify({ error: "method_not_allowed" }), { status: 405, headers: { ...cors, "Content-Type": "application/json" } });

  try {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) throw new Error("no_auth");
    const supa = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, { global: { headers: { Authorization: authHeader } } });
    const { data: { user }, error: authErr } = await supa.auth.getUser(authHeader.replace("Bearer ", ""));
    if (authErr || !user) throw new Error("unauthorized");

    // Candado Max REAL (no solo UI): la RLS de users solo deja leer la propia fila.
    const { data: planRow, error: planErr } = await supa.from("users").select("plan").eq("id", user.id).single();
    if (planErr || !planRow || planRow.plan !== "max") throw new Error("plan_required");

    const body = await req.json().catch(() => ({}));
    const mode = body.mode === "insight" ? "insight" : "chat";
    const snapshotRaw = typeof body.snapshot === "object" && body.snapshot ? JSON.stringify(body.snapshot) : "{}";
    const snapshot = snapshotRaw.slice(0, MAX_SNAPSHOT_CHARS);

    let contents: { role: string; parts: { text: string }[] }[];
    if (mode === "insight") {
      contents = [{ role: "user", parts: [{ text: "MODE=insight\nSNAPSHOT=" + snapshot }] }];
    } else {
      const msgs: any[] = Array.isArray(body.messages) ? body.messages.slice(-MAX_MESSAGES) : [];
      const history = msgs
        .filter((m) => m && typeof m.text === "string" && (m.role === "user" || m.role === "model"))
        .map((m) => ({ role: m.role, parts: [{ text: String(m.text).slice(0, MAX_MSG_CHARS) }] }));
      if (history.length === 0 || history[history.length - 1].role !== "user") throw new Error("empty_input");
      // El snapshot viaja pegado al ÚLTIMO mensaje del usuario (contexto fresco, sin duplicarlo por turno)
      const last = history[history.length - 1];
      last.parts[0].text = "SNAPSHOT=" + snapshot + "\n\nUSER_MESSAGE: " + last.parts[0].text;
      contents = history;
    }

    const accessToken = await getAccessToken();
    const endpoint = `https://${GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/${GCP_PROJECT}/locations/${GCP_LOCATION}/publishers/google/models/${MODEL}:generateContent`;

    const askModel = async (msgs: typeof contents): Promise<any> => {
      const vertexRes = await fetch(endpoint, {
        method: "POST",
        headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          systemInstruction: { role: "system", parts: [{ text: SYSTEM_PROMPT }] },
          contents: msgs,
          generationConfig: {
            temperature: 0.7,
            responseMimeType: "application/json",
            responseSchema: RESPONSE_SCHEMA,
            maxOutputTokens: 1024,
            thinkingConfig: { thinkingBudget: 0 },
          },
        }),
      });
      if (!vertexRes.ok) {
        console.error("[vertex]", vertexRes.status, await vertexRes.text());
        throw new Error(`vertex_${vertexRes.status}`);
      }
      const vertexJson = await vertexRes.json();
      const rawText = vertexJson?.candidates?.[0]?.content?.parts?.[0]?.text || "{}";
      try { return JSON.parse(rawText); } catch { return { text: rawText }; }
    };

    let out: any = await askModel(contents);

    // Agente lector: si el modelo pide query_records, ejecutarla (RLS del propio usuario)
    // y devolverle SOLO agregados como TOOL_RESULT. Máx 2 rondas; luego responde sí o sí.
    const dbg: any[] = [];
    let rounds = 0;
    while (mode === "chat" && out?.tool?.name === "query_records" && rounds < MAX_TOOL_ROUNDS) {
      rounds++;
      console.log("[tool]", JSON.stringify(out.tool));
      let result: Record<string, unknown>;
      try { result = await runQueryRecords(supa, user.id, out.tool); }
      catch (e) { result = { error: "tool_failed: " + (e instanceof Error ? e.message : String(e)) }; }
      if (body.debug === true) dbg.push({ tool: out.tool, result });
      contents.push({ role: "model", parts: [{ text: JSON.stringify({ tool: out.tool }) }] });
      contents.push({
        role: "user",
        parts: [{
          text: "TOOL_RESULT=" + JSON.stringify(result) + "\n" + (rounds >= MAX_TOOL_ROUNDS
            ? "(Answer the user NOW with these numbers; no more tool calls.)"
            : "(Answer the user now, or request ONE more query only if strictly needed.)"),
        }],
      });
      out = await askModel(contents);
    }
    // Si tras las rondas el modelo sigue pidiendo tool, su text es el placeholder
    // ("Déjame revisar…") — no dejarlo llegar al usuario como si fuera la respuesta.
    if (mode === "chat" && out?.tool?.name && (typeof out.text !== "string" || out.text.trim().length < 60)) {
      out = { ...out, text: "No pude completar esa consulta ahora mismo. ¿Lo intentamos de nuevo?" };
    }
    if (mode === "chat" && (typeof out?.text !== "string" || !out.text.trim())) {
      out = { ...out, text: "No pude completar esa consulta ahora mismo. ¿Lo intentamos de nuevo?" };
    }

    // Sanitizar contra las listas blancas — el cliente solo recibe destinos/shots válidos
    const actions = (Array.isArray(out.actions) ? out.actions : [])
      .filter((a: any) => a && typeof a.label === "string" && VALID_TARGETS.includes(a.target))
      .slice(0, 2);
    const shot = typeof out.shot === "string" && VALID_SHOTS.includes(out.shot) ? out.shot : null;

    return new Response(JSON.stringify({
      text: typeof out.text === "string" ? out.text : "",
      title: typeof out.title === "string" ? out.title : null,
      actions,
      shot,
      // Solo con body.debug=true (QA): los args reales de la tool. Data del propio usuario.
      ...(body.debug === true ? { _dbg: dbg } : {}),
    }), { headers: { ...cors, "Content-Type": "application/json" } });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    const status = msg === "unauthorized" || msg === "no_auth" ? 401
      : msg === "plan_required" ? 403
      : msg === "empty_input" ? 400 : 500;
    return new Response(JSON.stringify({ error: msg }), { status, headers: { ...cors, "Content-Type": "application/json" } });
  }
});
