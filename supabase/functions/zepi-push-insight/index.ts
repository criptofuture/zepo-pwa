// zepi-push-insight · F7: Zepi proactivo. Corre 1 vez al dia (pg_cron + pg_net),
// computa UN insight real por usuario Max con push activo y lo manda como notificacion
// con deep-link ?open=zepi. Maximo 1 push/dia por usuario (zepi_push_log) y SOLO si el
// modelo dice que hay algo que valga la pena (send=false -> silencio, no spam).
// Auth: header X-Zepi-Secret == ZEPI_CRON_SECRET (verify_jwt off: lo llama pg_net).

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { create as createJWT } from "https://deno.land/x/djwt@v3.0.2/mod.ts";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const CRON_SECRET = Deno.env.get("ZEPI_CRON_SECRET") || "";
const GCP_SA_JSON = Deno.env.get("GCP_SA_JSON")!;
const GCP_PROJECT = Deno.env.get("GCP_PROJECT") || "gen-lang-client-0934320964";
const GCP_LOCATION = Deno.env.get("GCP_LOCATION") || "us-central1";
const MODEL = Deno.env.get("ZEPI_MODEL") || "gemini-2.5-flash";
const VAPID_PUBLIC = Deno.env.get("VAPID_PUBLIC_KEY")!;
const VAPID_PRIVATE = Deno.env.get("VAPID_PRIVATE_KEY")!;
const VAPID_EMAIL = Deno.env.get("VAPID_EMAIL") ?? "hola@zepo.app";

const MAX_USERS_PER_RUN = 20; // presupuesto de 60s del edge

// ── OAuth de Vertex (mismo patron GCP_SA_JSON de zepo-companion) ─────────────
let _tok: { token: string; exp: number } | null = null;
async function gcpToken(): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  if (_tok && _tok.exp > now + 60) return _tok.token;
  const sa = JSON.parse(GCP_SA_JSON);
  const pemBody = String(sa.private_key).replace(/-----BEGIN PRIVATE KEY-----/g, "").replace(/-----END PRIVATE KEY-----/g, "").replace(/\s+/g, "");
  const der = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));
  const key = await crypto.subtle.importKey("pkcs8", der.buffer, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  const jwt = await createJWT({ alg: "RS256", typ: "JWT", kid: sa.private_key_id },
    { iss: sa.client_email, scope: "https://www.googleapis.com/auth/cloud-platform", aud: "https://oauth2.googleapis.com/token", iat: now, exp: now + 3600 }, key);
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion: jwt }),
  });
  if (!res.ok) throw new Error("oauth_failed");
  const j = await res.json();
  _tok = { token: j.access_token, exp: now + (j.expires_in || 3600) };
  return _tok.token;
}

// ── Web Push (copiado de send-daily-push: VAPID ES256 + POST simple) ─────────
function b64urlDecode(s: string): Uint8Array {
  const pad = s.length % 4 === 0 ? 0 : 4 - (s.length % 4);
  return Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat(pad)), (c) => c.charCodeAt(0));
}
function b64urlEncode(buf: ArrayBuffer): string {
  return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}
async function importVapidPrivate(b64url: string): Promise<CryptoKey> {
  const raw = b64urlDecode(b64url);
  const header = new Uint8Array([
    0x30, 0x41, 0x02, 0x01, 0x00, 0x30, 0x13,
    0x06, 0x07, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x02, 0x01,
    0x06, 0x08, 0x2a, 0x86, 0x48, 0xce, 0x3d, 0x03, 0x01, 0x07,
    0x04, 0x27, 0x30, 0x25, 0x02, 0x01, 0x01, 0x04, 0x20,
  ]);
  const pkcs8 = new Uint8Array(header.length + raw.length);
  pkcs8.set(header); pkcs8.set(raw, header.length);
  return crypto.subtle.importKey("pkcs8", pkcs8, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
}
async function vapidJwt(audience: string): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  const h = b64urlEncode(new TextEncoder().encode(JSON.stringify({ typ: "JWT", alg: "ES256" })));
  const p = b64urlEncode(new TextEncoder().encode(JSON.stringify({ aud: audience, exp: now + 43200, sub: `mailto:${VAPID_EMAIL}` })));
  const input = `${h}.${p}`;
  const sig = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, await importVapidPrivate(VAPID_PRIVATE), new TextEncoder().encode(input));
  const der = new Uint8Array(sig);
  let off = 2; const rLen = der[3]; off = 4;
  const r = der.slice(off, off + rLen); off += rLen;
  const sLen = der[off + 1]; off += 2;
  const s = der.slice(off, off + sLen);
  const raw = new Uint8Array(64);
  raw.set(r.slice(-32), 32 - Math.min(r.length, 32));
  raw.set(s.slice(-32), 64 - Math.min(s.length, 32));
  return `${input}.${b64urlEncode(raw.buffer)}`;
}
async function sendPush(sub: { endpoint: string; p256dh: string; auth_key: string }, payload: string): Promise<boolean> {
  const url = new URL(sub.endpoint);
  const jwt = await vapidJwt(`${url.protocol}//${url.host}`);
  const body = new TextEncoder().encode(payload);
  const res = await fetch(sub.endpoint, {
    method: "POST",
    headers: { "Authorization": `vapid t=${jwt},k=${VAPID_PUBLIC}`, "TTL": "86400", "Content-Type": "application/json", "Content-Length": String(body.length) },
    body,
  });
  return res.ok || res.status === 201;
}

// ── Snapshot server-side por usuario (agregados, nunca filas al prompt) ──────
const r2 = (x: number) => Math.round((Number(x) || 0) * 100) / 100;
async function buildSnapshot(sb: any, userId: string): Promise<Record<string, unknown> | null> {
  const now = new Date();
  const ym = (d: Date) => d.toISOString().slice(0, 7);
  const curStart = ym(now) + "-01";
  const prev = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1));
  const prevStart = ym(prev) + "-01";
  const { data: rows } = await sb.from("expenses")
    .select("amount,category,date,is_income,is_split,split_status,split_pending")
    .eq("user_id", userId).gte("date", prevStart).limit(1000);
  if (!rows || rows.length < 3) return null; // sin datos no hay insight honesto
  const agg = (from: string, to: string) => {
    const byCat: Record<string, number> = {};
    let expenses = 0, income = 0;
    for (const r of rows) {
      const d = String(r.date);
      if (d < from || d >= to) continue;
      const amt = Number(r.amount) || 0;
      if (r.is_income) { income += amt; continue; }
      expenses += amt;
      byCat[String(r.category || "other")] = (byCat[String(r.category || "other")] || 0) + amt;
    }
    return { expenses: r2(expenses), income: r2(income), byCat: Object.fromEntries(Object.entries(byCat).map(([k, v]) => [k, r2(v)])) };
  };
  const nextMonth = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1));
  const snap: Record<string, unknown> = {
    today: now.toISOString().slice(0, 10),
    month: agg(curStart, ym(nextMonth) + "-01"),
    prevMonth: agg(prevStart, curStart),
  };
  const pend = rows.filter((r: any) => r.is_split && r.split_status === "pendiente" && Number(r.split_pending) > 0);
  if (pend.length) snap.cobrosPendientes = { n: pend.length, total: r2(pend.reduce((s: number, r: any) => s + Number(r.split_pending), 0)) };
  const { data: buds } = await sb.from("budgets").select("category,amount")
    .eq("user_id", userId).eq("month", now.getUTCMonth() + 1).eq("year", now.getUTCFullYear()).limit(30);
  if (buds && buds.length) snap.budgets = buds.map((b: any) => ({ cat: b.category || "total", amount: Number(b.amount) }));
  // Metas activas (Fase 6) — v1: nudge por deadline/existencia (sin recomputar ritmo server-side)
  const { data: goals } = await sb.from("zepi_goals").select("kind,title,target_amount,current_amount,deadline")
    .eq("user_id", userId).eq("status", "active").limit(10);
  if (goals && goals.length) {
    const todayISO = now.toISOString().slice(0, 10);
    snap.goals = goals.map((g: any) => {
      const o: Record<string, unknown> = { kind: g.kind, title: g.title, target: Number(g.target_amount) };
      if (g.deadline) { o.deadline = g.deadline; o.daysLeft = Math.round((new Date(g.deadline + "T00:00:00Z").getTime() - new Date(todayISO + "T00:00:00Z").getTime()) / 86400000); }
      if (g.kind === "debt" && g.current_amount != null) o.remaining = Number(g.current_amount);
      return o;
    });
  }
  return snap;
}

const PUSH_PROMPT = `You are Zepi, the financial companion inside Zepo (LatAm expense tracker). You get a SNAPSHOT of one user's aggregated numbers (current month, previous month, budgets, pending split collections). Decide if there is ONE push-notification-worthy insight TODAY.
Return ONLY JSON: { "send": boolean, "title": string, "body": string }.
- send=true ONLY for something genuinely useful: budget nearly blown, a category clearly spiking vs prev month, old pending collections, a goal with a close deadline (SNAPSHOT.goals[].daysLeft small) or clear progress on one, or a real win (spending way down). Otherwise send=false.
- Spanish (LatAm, "tú"). title <= 40 chars, punchy, no emoji spam (max 1). body <= 110 chars, concrete numbers from SNAPSHOT only.
- Never invent numbers. Never mention "snapshot".`;

async function insightFor(snap: Record<string, unknown>): Promise<{ send: boolean; title: string; body: string } | null> {
  const token = await gcpToken();
  const endpoint = `https://${GCP_LOCATION}-aiplatform.googleapis.com/v1/projects/${GCP_PROJECT}/locations/${GCP_LOCATION}/publishers/google/models/${MODEL}:generateContent`;
  const res = await fetch(endpoint, {
    method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      systemInstruction: { role: "system", parts: [{ text: PUSH_PROMPT }] },
      contents: [{ role: "user", parts: [{ text: "SNAPSHOT=" + JSON.stringify(snap) }] }],
      generationConfig: {
        temperature: 0.5, responseMimeType: "application/json", maxOutputTokens: 256,
        responseSchema: { type: "OBJECT", properties: { send: { type: "BOOLEAN" }, title: { type: "STRING" }, body: { type: "STRING" } }, required: ["send", "title", "body"] },
        thinkingConfig: { thinkingBudget: 0 },
      },
    }),
  });
  if (!res.ok) { console.error("[vertex]", res.status, await res.text()); return null; }
  const j = await res.json();
  try { return JSON.parse(j?.candidates?.[0]?.content?.parts?.[0]?.text || "{}"); } catch { return null; }
}

serve(async (req) => {
  if (!CRON_SECRET || req.headers.get("X-Zepi-Secret") !== CRON_SECRET) {
    return new Response(JSON.stringify({ error: "unauthorized" }), { status: 401, headers: { "Content-Type": "application/json" } });
  }
  const sb = createClient(SUPABASE_URL, SERVICE_KEY, { auth: { persistSession: false } });
  const today = new Date().toISOString().slice(0, 10);

  // Usuarios Max con push activo y sin insight procesado hoy
  const { data: maxUsers } = await sb.from("users").select("id").eq("plan", "max").limit(500);
  const ids = (maxUsers || []).map((u: any) => u.id);
  if (!ids.length) return new Response(JSON.stringify({ checked: 0, sent: 0 }), { headers: { "Content-Type": "application/json" } });
  const { data: subs } = await sb.from("push_subscriptions").select("user_id,endpoint,p256dh,auth_key").in("user_id", ids);
  const { data: logged } = await sb.from("zepi_push_log").select("user_id").eq("day", today).in("user_id", ids);
  const done = new Set((logged || []).map((l: any) => l.user_id));
  const byUser: Record<string, any[]> = {};
  (subs || []).forEach((s: any) => { if (!done.has(s.user_id)) (byUser[s.user_id] = byUser[s.user_id] || []).push(s); });

  let checked = 0, sent = 0;
  for (const [userId, userSubs] of Object.entries(byUser).slice(0, MAX_USERS_PER_RUN)) {
    checked++;
    let title = "", pushed = false;
    try {
      const snap = await buildSnapshot(sb, userId);
      if (snap) {
        const ins = await insightFor(snap);
        if (ins && ins.send === true && ins.title && ins.body) {
          title = String(ins.title).slice(0, 60);
          const payload = JSON.stringify({
            title: "Zepi · " + title,
            body: String(ins.body).slice(0, 140),
            icon: "https://app.zepo.lynoia.com/icons/icon-192.png",
            badge: "https://app.zepo.lynoia.com/icons/favicon-32.png",
            url: "https://app.zepo.lynoia.com/pwa/?open=zepi",
          });
          for (const s of userSubs) {
            try { if (await sendPush(s, payload)) pushed = true; } catch (_) { /* endpoint muerto */ }
          }
          if (pushed) sent++;
        }
      }
    } catch (e) { console.error("[user]", userId, e instanceof Error ? e.message : String(e)); }
    // Log SIEMPRE (aunque send=false): 1 evaluacion por dia, sin re-quemar el modelo
    try { await sb.from("zepi_push_log").upsert({ user_id: userId, day: today, sent: pushed, title }); } catch (_) {}
  }

  return new Response(JSON.stringify({ checked, sent, day: today }), { headers: { "Content-Type": "application/json" } });
});
