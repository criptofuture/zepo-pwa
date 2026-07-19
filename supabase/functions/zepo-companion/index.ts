// zepo-companion · "Zepi", el asistente financiero dentro de Zepo (Max-only)
// Chat + insight-del-día vía Vertex AI (Gemini). Reusa el patrón GCP_SA_JSON de categorize-ai.
// Candado de plan SERVER-SIDE: lee users.plan con el JWT del usuario (RLS = solo su fila).

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { create as createJWT } from "https://deno.land/x/djwt@v3.0.2/mod.ts";
import { SYSTEM_PROMPT } from "./prompt.ts";
import { runQueryRecords } from "./tools.ts";
import { sanitizeIntent } from "./intents.ts";

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
    // Acción con confirmación (agente escritor): el edge SOLO la sanitiza; el cliente
    // la ejecuta tras la tarjeta "¿Registro esto?". Unión plana: kind decide qué campos van.
    intent: {
      type: "OBJECT",
      properties: {
        kind: { type: "STRING" },
        items: {
          type: "ARRAY",
          items: {
            type: "OBJECT",
            properties: {
              amount: { type: "NUMBER" },
              description: { type: "STRING" },
              category: { type: "STRING" },
              is_income: { type: "BOOLEAN" },
              date: { type: "STRING" },
            },
            // Lección F1: sin required el modelo omite campos de objetos anidados
            // (omitía date y "ayer" se registraba como hoy).
            required: ["amount", "description", "category", "date"],
          },
        },
        amount: { type: "NUMBER" },
        category: { type: "STRING" },
        total: { type: "NUMBER" },
        description: { type: "STRING" },
        person: { type: "STRING" },
      },
      required: ["kind"],
    },
    // F4: memoria de largo plazo — hechos durables que el usuario compartió.
    // El edge los persiste en zepi_memory con el JWT del usuario (cero llamadas extra).
    memory_update: {
      type: "OBJECT",
      properties: {
        set: {
          type: "ARRAY",
          items: {
            type: "OBJECT",
            properties: { key: { type: "STRING" }, value: { type: "STRING" } },
            required: ["key", "value"],
          },
        },
        forget: { type: "ARRAY", items: { type: "STRING" } },
        summary: { type: "STRING" },
      },
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

    const body = await req.json().catch(() => ({}));
    const mode = body.mode === "insight" ? "insight" : body.mode === "tool" ? "tool" : body.mode === "stt" ? "stt" : "chat";

    // Candado de plan REAL (no solo UI): la RLS de users solo deja leer la propia fila.
    // F5 probadita: pro/elite entran al CHAT con cupo mensual; insight y voz siguen Max-only.
    const { data: planRow, error: planErr } = await supa.from("users").select("plan").eq("id", user.id).single();
    const plan = String(planRow?.plan || "");
    if (planErr || !["pro", "elite", "max"].includes(plan)) throw new Error("plan_required");
    if ((mode === "insight" || mode === "tool") && plan !== "max") throw new Error("plan_required");

    // F3 voz: ejecución directa de query_records para los tool-calls de Gemini Live
    // (mismo RLS del usuario, mismos agregados; el cliente reenvía el resultado al modelo).
    if (mode === "tool") {
      const t = typeof body.tool === "object" && body.tool ? body.tool : {};
      let result: Record<string, unknown>;
      try { result = await runQueryRecords(supa, user.id, t); }
      catch (e) { result = { error: "tool_failed: " + (e instanceof Error ? e.message : String(e)) }; }
      return new Response(JSON.stringify({ result }), { headers: { ...cors, "Content-Type": "application/json" } });
    }

    // Dictado (botón 🎤 del chat): transcribe un audio corto a texto y lo devuelve.
    // Disponible pro/elite/max — NO descuenta cupo: el mensaje que el usuario mande
    // con ese texto es el turno que cuenta. El audio nunca se guarda.
    if (mode === "stt") {
      const audioB64 = typeof body.audio === "string" ? body.audio : "";
      const mime = typeof body.mime === "string" && /^audio\/[a-z0-9.+-]{2,30}$/i.test(body.mime) ? body.mime : "audio/wav";
      if (audioB64.length < 1000) throw new Error("empty_input");
      if (audioB64.length > 2_800_000) throw new Error("audio_too_long"); // ~2MB ≈ 60s de WAV 16k mono
      const sttToken = await getAccessToken();
      const sttEndpoint = `https://${GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/${GCP_PROJECT}/locations/${GCP_LOCATION}/publishers/google/models/${MODEL}:generateContent`;
      const sttRes = await fetch(sttEndpoint, {
        method: "POST",
        headers: { Authorization: `Bearer ${sttToken}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [{ role: "user", parts: [
            { inlineData: { mimeType: mime, data: audioB64 } },
            { text: "Transcribe el audio a texto plano en el idioma hablado (español latino por defecto). Devuelve SOLO la transcripción literal, sin comillas ni comentarios. Si no se oye habla, devuelve una cadena vacía." },
          ] }],
          generationConfig: { temperature: 0, maxOutputTokens: 512, thinkingConfig: { thinkingBudget: 0 } },
        }),
      });
      if (!sttRes.ok) { console.error("[stt]", sttRes.status, await sttRes.text()); throw new Error(`vertex_${sttRes.status}`); }
      const sttJson = await sttRes.json();
      const sttText = String(sttJson?.candidates?.[0]?.content?.parts?.[0]?.text || "").trim();
      return new Response(JSON.stringify({ text: sttText }), { headers: { ...cors, "Content-Type": "application/json" } });
    }
    const snapshotRaw = typeof body.snapshot === "object" && body.snapshot ? JSON.stringify(body.snapshot) : "{}";
    const snapshot = snapshotRaw.slice(0, MAX_SNAPSHOT_CHARS);
    // "Hoy" para validar fechas de intents: el del cliente (su zona horaria) si es ISO válido.
    const snapToday = typeof body.snapshot === "object" && body.snapshot ? String((body.snapshot as any).today || "") : "";
    const todayISO = /^\d{4}-\d{2}-\d{2}$/.test(snapToday) ? snapToday : new Date().toISOString().slice(0, 10);

    // F5: cupo mensual server-side para la probadita Pro/Elite (Max no cuenta).
    // zepi_usage es server-only: el usuario no puede leer ni inflar su contador.
    const QUOTA: Record<string, number> = { pro: 10, elite: 25 };
    let quota: { used: number; limit: number } | null = null;
    let svc: any = null;
    const quotaMonth = todayISO.slice(0, 7);
    if (plan !== "max") {
      svc = createClient(SUPABASE_URL, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
      const { data: uRow } = await svc.from("zepi_usage").select("msgs").eq("user_id", user.id).eq("month", quotaMonth).maybeSingle();
      const used = Number(uRow?.msgs) || 0;
      const limit = QUOTA[plan] || 0;
      if (used >= limit) {
        // Cupo agotado: respuesta de upsell fija, SIN llamada al modelo (costo cero).
        return new Response(JSON.stringify({
          text: `Este mes ya usamos los ${limit} mensajes de tu plan 🙈 Con Max charlamos sin límite. Nos leemos el próximo mes — o antes 😉`,
          title: null, actions: [{ label: "Ver plan Max", target: "plans" }], shot: null, intent: null,
          quota: { used, limit }, quota_exhausted: true,
        }), { headers: { ...cors, "Content-Type": "application/json" } });
      }
      quota = { used, limit };
    }

    // F4: memoria de largo plazo del usuario (JWT del usuario → RLS su propia fila)
    let memRow: { facts?: Record<string, unknown>; summary?: string } | null = null;
    try {
      const { data } = await supa.from("zepi_memory").select("facts,summary").eq("user_id", user.id).maybeSingle();
      memRow = data;
    } catch (_) { /* sin memoria no se bloquea el chat */ }
    const memText = memRow && ((memRow.summary || "").trim() || Object.keys(memRow.facts || {}).length > 0)
      ? "MEMORY=" + JSON.stringify({ facts: memRow.facts || {}, summary: memRow.summary || "" }).slice(0, 2500) + "\n"
      : "";

    let contents: { role: string; parts: { text: string }[] }[];
    if (mode === "insight") {
      contents = [{ role: "user", parts: [{ text: "MODE=insight\n" + memText + "SNAPSHOT=" + snapshot }] }];
    } else {
      const msgs: any[] = Array.isArray(body.messages) ? body.messages.slice(-MAX_MESSAGES) : [];
      const history = msgs
        .filter((m) => m && typeof m.text === "string" && (m.role === "user" || m.role === "model"))
        .map((m) => ({ role: m.role, parts: [{ text: String(m.text).slice(0, MAX_MSG_CHARS) }] }));
      if (history.length === 0 || history[history.length - 1].role !== "user") throw new Error("empty_input");
      // El snapshot (y la memoria) viajan pegados al ÚLTIMO mensaje del usuario
      // (contexto fresco, sin duplicarlo por turno)
      const last = history[history.length - 1];
      last.parts[0].text = memText + "SNAPSHOT=" + snapshot + "\n\nUSER_MESSAGE: " + last.parts[0].text;
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
    // Además: ronda correctiva única si suelta un placeholder ("Déjame revisar…") SIN
    // pedir la tool — modo de falla real visto en QA (respuesta muda sin datos).
    const dbg: any[] = [];
    const PLACEHOLDER_RE = /^\s*(d[ée]jame\s+(revisar|ver|checar|consultar)|un\s+momento|dame\s+un\s+segundo)/i;
    let rounds = 0;
    let nudged = false;
    while (mode === "chat") {
      if (out?.tool?.name === "query_records" && rounds < MAX_TOOL_ROUNDS) {
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
        continue;
      }
      if (!nudged && rounds === 0 && !out?.tool?.name && PLACEHOLDER_RE.test(String(out?.text || ""))) {
        nudged = true;
        if (body.debug === true) dbg.push({ nudge: String(out?.text || "").slice(0, 60) });
        contents.push({ role: "model", parts: [{ text: JSON.stringify({ text: out.text }) }] });
        contents.push({
          role: "user",
          parts: [{ text: "(Your last message was a stalling placeholder with NO tool request. If you need history, emit tool query_records NOW; otherwise answer directly with real numbers from SNAPSHOT/MEMORY.)" }],
        });
        out = await askModel(contents);
        continue;
      }
      break;
    }
    // Agente escritor: si el modelo emitió un intent, sanitizarlo. Si viene malformado,
    // UNA ronda de reintento con INTENT_ERROR= (mismo patrón que TOOL_RESULT).
    let intent: Record<string, unknown> | null = null;
    for (let tries = 0; mode === "chat" && out?.intent?.kind && tries < 2; tries++) {
      const r = await sanitizeIntent(supa, out.intent, todayISO, planRow.plan);
      if (body.debug === true) dbg.push({ rawIntent: out.intent, sanitized: r });
      if (r.ok) { intent = r.ok; break; }
      console.log("[intent-error]", r.err);
      if (tries === 1) break;
      contents.push({ role: "model", parts: [{ text: JSON.stringify({ intent: out.intent }) }] });
      contents.push({
        role: "user",
        parts: [{ text: "INTENT_ERROR=" + r.err + "\n(Fix the intent and answer again, or answer WITHOUT intent explaining the issue to the user.)" }],
      });
      out = await askModel(contents);
    }
    // F4: persistir memory_update (JWT del usuario — RLS limita a su propia fila).
    // Tope de tamaño server-side: 40 hechos, key 40 chars, value 200, summary 1000.
    if (mode === "chat" && out?.memory_update && typeof out.memory_update === "object") {
      try {
        const mu = out.memory_update;
        const facts: Record<string, string> = {};
        for (const [k, v] of Object.entries((memRow?.facts as Record<string, unknown>) || {})) facts[String(k).slice(0, 40)] = String(v).slice(0, 200);
        (Array.isArray(mu.set) ? mu.set.slice(0, 10) : []).forEach((p: any) => {
          const k = String(p?.key || "").trim().slice(0, 40);
          const v = String(p?.value || "").trim().slice(0, 200);
          if (k && v) facts[k] = v;
        });
        (Array.isArray(mu.forget) ? mu.forget.slice(0, 10) : []).forEach((k: any) => { delete facts[String(k || "").trim().slice(0, 40)]; });
        const keys = Object.keys(facts);
        if (keys.length > 40) keys.slice(0, keys.length - 40).forEach((k) => delete facts[k]);
        const summary = typeof mu.summary === "string" && mu.summary.trim() ? mu.summary.slice(0, 1000) : (memRow?.summary || "");
        await supa.from("zepi_memory").upsert({ user_id: user.id, facts, summary, updated_at: new Date().toISOString() });
        if (body.debug === true) dbg.push({ memory_update: mu });
      } catch (e) { console.log("[memory]", e instanceof Error ? e.message : String(e)); }
    }

    // Si tras las rondas el modelo sigue pidiendo tool, su text es el placeholder
    // ("Déjame revisar…") — no dejarlo llegar al usuario como si fuera la respuesta.
    if (mode === "chat" && out?.tool?.name && (typeof out.text !== "string" || out.text.trim().length < 60)) {
      out = { ...out, text: "No pude completar esa consulta ahora mismo. ¿Lo intentamos de nuevo?" };
    }
    if (mode === "chat" && intent && (typeof out.text !== "string" || !out.text.trim())) {
      out = { ...out, text: "Te lo dejé listo — confírmalo aquí abajo 👇" };
    }
    if (mode === "chat" && (typeof out?.text !== "string" || !out.text.trim())) {
      out = { ...out, text: "No pude completar esa consulta ahora mismo. ¿Lo intentamos de nuevo?" };
    }

    // Sanitizar contra las listas blancas — el cliente solo recibe destinos/shots válidos
    const actions = (Array.isArray(out.actions) ? out.actions : [])
      .filter((a: any) => a && typeof a.label === "string" && VALID_TARGETS.includes(a.target))
      .slice(0, 2);
    const shot = typeof out.shot === "string" && VALID_SHOTS.includes(out.shot) ? out.shot : null;

    // F5: contar el turno DESPUÉS de responder bien (un turno = un mensaje del cupo)
    if (quota && svc) {
      try {
        await svc.from("zepi_usage").upsert({ user_id: user.id, month: quotaMonth, msgs: quota.used + 1 });
        quota = { used: quota.used + 1, limit: quota.limit };
      } catch (e) { console.log("[quota]", e instanceof Error ? e.message : String(e)); }
    }

    return new Response(JSON.stringify({
      text: typeof out.text === "string" ? out.text : "",
      title: typeof out.title === "string" ? out.title : null,
      actions,
      shot,
      // Acción sanitizada (o null): el cliente la muestra como tarjeta de confirmación.
      intent,
      // Cupo de la probadita Pro/Elite (null para Max = ilimitado)
      quota,
      // Solo con body.debug=true (QA): los args reales de la tool. Data del propio usuario.
      ...(body.debug === true ? { _dbg: dbg } : {}),
    }), { headers: { ...cors, "Content-Type": "application/json" } });
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    const status = msg === "unauthorized" || msg === "no_auth" ? 401
      : msg === "plan_required" ? 403
      : msg === "empty_input" || msg === "audio_too_long" ? 400 : 500;
    return new Response(JSON.stringify({ error: msg }), { status, headers: { ...cors, "Content-Type": "application/json" } });
  }
});
