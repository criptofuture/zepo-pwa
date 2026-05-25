// parse-bank-statement · Extracts transactions from bank statement text via Gemini 2.5 Flash
// Receives raw text (extracted client-side from PDF), returns structured transactions.
// Reuses GCP_SA_JSON + Vertex AI auth from categorize-ai.

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { create as createJWT } from "https://deno.land/x/djwt@v3.0.2/mod.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_ANON_KEY = Deno.env.get("SUPABASE_ANON_KEY")!;
const GCP_SA_JSON = Deno.env.get("GCP_SA_JSON")!;
const GCP_PROJECT = Deno.env.get("GCP_PROJECT") || "gen-lang-client-0934320964";
const GCP_LOCATION = Deno.env.get("GCP_LOCATION") || "us-central1";
const MODEL = "gemini-2.5-flash";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, content-type, x-client-info, apikey",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

const PROMPT = `Eres un parser de estados de cuenta bancarios. Recibes texto extraido de un PDF bancario.

Tu tarea: extraer CADA transaccion como un objeto JSON.

REGLAS:
1. Extrae TODAS las transacciones. No omitas ninguna.
2. Fechas: convierte al formato YYYY-MM-DD. Si el PDF no muestra el ano, usa el ano del periodo del estado de cuenta.
3. Montos: numeros positivos siempre. Sin simbolo de moneda.
4. Tipo: "debit" para gastos/cargos/retiros/compras/pagos, "credit" para depositos/transferencias recibidas/abonos.
5. Descripcion: texto descriptivo de la transaccion tal como aparece, limpio (sin numeros de referencia internos si son irrelevantes).
6. Si hay un saldo, NO lo incluyas como transaccion.
7. Si hay totales/resumen al final, NO los incluyas.
8. Si una linea NO es claramente una transaccion (es un encabezado, pie de pagina, informacion de cuenta), IGNORALA.

CATEGORIAS para gastos (debit): food, transport, market, health, rent, fun, shop, coffee, pets, savings, invest_out, gym, education, travel, other
CATEGORIAS para ingresos (credit): salary, freelance, business, investment, gift, refund, rental, sale, other_income

Clasifica cada transaccion en la categoria mas probable basandote en la descripcion.

Responde UNICAMENTE un JSON array de objetos. Sin texto adicional.`;

const SCHEMA = {
  type: "ARRAY",
  items: {
    type: "OBJECT",
    properties: {
      date: { type: "STRING", description: "YYYY-MM-DD" },
      amount: { type: "NUMBER", description: "Monto positivo sin simbolo" },
      description: { type: "STRING", description: "Descripcion de la transaccion" },
      type: { type: "STRING", enum: ["debit", "credit"] },
      category: { type: "STRING" },
    },
    required: ["date", "amount", "description", "type", "category"],
  },
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
    const text = typeof body.text === "string" ? body.text : "";
    if (!text || text.length < 20) throw new Error("text_too_short");
    // Limit to ~30KB of text (about 50 pages)
    const truncated = text.slice(0, 30000);

    const accessToken = await getAccessToken();
    const endpoint = `https://${GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/${GCP_PROJECT}/locations/${GCP_LOCATION}/publishers/google/models/${MODEL}:generateContent`;

    const vertexRes = await fetch(endpoint, {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
      body: JSON.stringify({
        systemInstruction: { role: "system", parts: [{ text: PROMPT }] },
        contents: [{ role: "user", parts: [{ text: truncated }] }],
        generationConfig: {
          temperature: 0,
          responseMimeType: "application/json",
          responseSchema: SCHEMA,
          maxOutputTokens: 65536,
          thinkingConfig: { thinkingBudget: 0 },
        },
      }),
    });

    if (!vertexRes.ok) {
      const errText = await vertexRes.text();
      console.error("[vertex]", vertexRes.status, errText);
      throw new Error(`vertex_${vertexRes.status}`);
    }

    const vertexJson = await vertexRes.json();
    const resultText = vertexJson?.candidates?.[0]?.content?.parts?.[0]?.text || "[]";
    let transactions: any[] = [];
    try { transactions = JSON.parse(resultText); } catch { transactions = []; }

    // Validate and clean each transaction
    const EXP_KEYS = ["food","transport","market","health","rent","fun","shop","coffee","pets","savings","invest_out","gym","education","travel","other"];
    const INC_KEYS = ["salary","freelance","business","investment","gift","refund","rental","sale","other_income"];

    transactions = transactions
      .filter((t: any) => t.date && t.amount > 0 && t.description)
      .map((t: any) => {
        const isIncome = t.type === "credit";
        const validCats = isIncome ? INC_KEYS : EXP_KEYS;
        const category = validCats.includes(t.category) ? t.category : (isIncome ? "other_income" : "other");
        return {
          date: String(t.date).slice(0, 10),
          amount: Math.round(Number(t.amount) * 100) / 100,
          description: String(t.description).slice(0, 200),
          is_income: isIncome,
          category,
        };
      });

    return new Response(
      JSON.stringify({ transactions, count: transactions.length }),
      { headers: { ...cors, "Content-Type": "application/json" } }
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    const status = msg === "unauthorized" || msg === "no_auth" ? 401 : msg === "text_too_short" ? 400 : 500;
    return new Response(JSON.stringify({ error: msg }), { status, headers: { ...cors, "Content-Type": "application/json" } });
  }
});
