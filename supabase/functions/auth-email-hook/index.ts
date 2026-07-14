// auth-email-hook — Supabase Send Email Hook compartido Zepo + Elé.
// Recibe el webhook de Auth (firmado), detecta la app por redirect_to y envía
// el correo con la marca correcta vía Resend (from por-app, plantilla por-app).
// Deploy: --no-verify-jwt (la seguridad es la firma del webhook, no JWT).

import { Webhook } from "https://esm.sh/standardwebhooks@1.0.0";
import { buildEmail } from "./templates.ts";

const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") ?? "";
const HOOK_SECRET = (Deno.env.get("SEND_EMAIL_HOOK_SECRET") ?? "").replace("v1,whsec_", "");

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function detectApp(url: string): "zepo" | "ele" {
  return /(^|\/\/|\.)((app|guia)\.)?ele\.lynoia\.com/i.test(url) ? "ele" : "zepo";
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ error: { http_code: 405, message: "method not allowed" } }, 405);
  if (!HOOK_SECRET) return json({ error: { http_code: 500, message: "hook secret not configured" } }, 500);

  const payload = await req.text();
  const headers = Object.fromEntries(req.headers);

  let evt: {
    user: { email: string };
    email_data: {
      token: string;
      token_hash: string;
      redirect_to: string;
      email_action_type: string;
      site_url: string;
      token_new?: string;
      token_hash_new?: string;
    };
  };
  try {
    evt = new Webhook(HOOK_SECRET).verify(payload, headers) as typeof evt;
  } catch {
    return json({ error: { http_code: 401, message: "invalid webhook signature" } }, 401);
  }

  const d = evt.email_data;
  const dest = d.redirect_to || d.site_url || "";
  const app = detectApp(dest);
  const verifyUrl =
    `${Deno.env.get("SUPABASE_URL")}/auth/v1/verify` +
    `?token=${encodeURIComponent(d.token_hash)}` +
    `&type=${encodeURIComponent(d.email_action_type)}` +
    `&redirect_to=${encodeURIComponent(dest)}`;

  const mail = buildEmail(app, d.email_action_type, verifyUrl, d.token);

  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${RESEND_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: mail.from,
      to: [evt.user.email],
      subject: mail.subject,
      html: mail.html,
    }),
  });

  if (!r.ok) {
    const detail = await r.text();
    console.error("resend_error", r.status, detail.slice(0, 300));
    return json({ error: { http_code: 500, message: `resend ${r.status}` } }, 500);
  }

  return json({});
});
