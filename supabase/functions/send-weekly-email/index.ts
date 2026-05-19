// send-weekly-email · Resumen semanal de gastos por usuario
// Llamado por n8n cron diariamente. Filtra usuarios cuyo weekly_day
// coincida con el día actual (en su timezone) y envía via Resend.
//
// Requiere secrets:
//   RESEND_API_KEY   = re_xxxxxxxxxxxx   (resend.com → API Keys)
//   FROM_EMAIL       = Zepo <hola@zepo.app>

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { buildWeeklyEmail, getCatMeta } from "./email-template.ts";

const SUPABASE_URL     = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_SERVICE = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const RESEND_API_KEY   = Deno.env.get("RESEND_API_KEY")!;
const FROM_EMAIL       = Deno.env.get("FROM_EMAIL") ?? "Zepo <hola@zepo.app>";
const APP_URL          = "https://app.zepo.lynoia.com";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, content-type, apikey",
};

// ── Helpers ───────────────────────────────────────────────────────

function weekLabel(from: Date, to: Date): string {
  const opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "long" };
  const fmtDate = (d: Date) => d.toLocaleDateString("es-EC", opts);
  const year = to.getFullYear();
  return `${fmtDate(from)} – ${fmtDate(to)} ${year}`;
}

async function sendEmail(to: string, subject: string, html: string): Promise<boolean> {
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ from: FROM_EMAIL, to, subject, html }),
  });
  if (!res.ok) {
    const err = await res.text();
    console.error("[resend]", res.status, err);
  }
  return res.ok;
}

// ── Main ─────────────────────────────────────────────────────────

serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: cors });

  const sb = createClient(SUPABASE_URL, SUPABASE_SERVICE, {
    auth: { persistSession: false },
  });

  const nowUtc  = new Date();
  const todayDow = nowUtc.getUTCDay(); // 0=dom…6=sáb (en UTC, ajustamos por TZ abajo)

  // Buscar usuarios con resumen semanal activo
  const { data: settings } = await sb
    .from("user_settings")
    .select("user_id, weekly_day, weekly_time, timezone_offset")
    .eq("notif_weekly", true);

  if (!settings || settings.length === 0) {
    return new Response(JSON.stringify({ sent: 0 }), { headers: { ...cors, "Content-Type": "application/json" } });
  }

  // Filtrar usuarios cuyo día de la semana (en su TZ) coincide con hoy
  const targetUsers: string[] = [];
  for (const s of settings) {
    const tzOffset = Number(s.timezone_offset) || -5;
    const localDow = ((todayDow + Math.floor((nowUtc.getUTCHours() + tzOffset) / 24)) % 7 + 7) % 7;
    if (localDow === Number(s.weekly_day)) {
      targetUsers.push(s.user_id as string);
    }
  }

  if (targetUsers.length === 0) {
    return new Response(JSON.stringify({ sent: 0, checked: settings.length }), {
      headers: { ...cors, "Content-Type": "application/json" },
    });
  }

  // Rango de fechas: últimos 7 días
  const weekEnd   = new Date(nowUtc);
  const weekStart = new Date(nowUtc);
  weekStart.setDate(weekStart.getDate() - 7);
  const startISO = weekStart.toISOString().slice(0, 10);
  const endISO   = weekEnd.toISOString().slice(0, 10);

  let sent = 0;
  const errors: string[] = [];

  for (const userId of targetUsers) {
    try {
      // Email del usuario
      const { data: userData } = await sb.auth.admin.getUserById(userId);
      const email    = userData?.user?.email;
      const meta     = userData?.user?.user_metadata ?? {};
      const userName = (meta.full_name || meta.name || email?.split("@")[0] || "Usuario") as string;
      if (!email) continue;

      // Gastos de la semana
      const { data: expenses } = await sb
        .from("expenses")
        .select("amount, category, is_income, date")
        .eq("user_id", userId)
        .gte("date", startISO)
        .lte("date", endISO);

      const rows = expenses ?? [];
      const totalGastos   = rows.filter(e => !e.is_income).reduce((s, e) => s + Number(e.amount), 0);
      const totalIngresos = rows.filter(e =>  e.is_income).reduce((s, e) => s + Number(e.amount), 0);
      const balance       = totalIngresos - totalGastos;

      // Top categorías de gasto
      const catTotals: Record<string, number> = {};
      for (const e of rows.filter(r => !r.is_income)) {
        catTotals[e.category] = (catTotals[e.category] ?? 0) + Number(e.amount);
      }
      const topCategories = Object.entries(catTotals)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5)
        .map(([key, amount]) => {
          const { label, emoji } = getCatMeta(key);
          return { label, emoji, amount, pct: totalGastos > 0 ? Math.round(amount / totalGastos * 100) : 0 };
        });

      // Cobros pendientes
      const { data: splits } = await sb
        .from("expenses")
        .select("split_pending")
        .eq("user_id", userId)
        .eq("is_split", true)
        .eq("split_status", "pendiente");

      const pendingCobros = (splits ?? []).reduce((s, e) => s + Number(e.split_pending ?? 0), 0);

      // Construir y enviar email
      const html = buildWeeklyEmail({
        userName,
        weekLabel: weekLabel(weekStart, weekEnd),
        totalGastos,
        totalIngresos,
        balance,
        numTransacciones: rows.length,
        topCategories,
        pendingCobros,
        appUrl: APP_URL,
      });

      const ok = await sendEmail(email, `Tu resumen semanal · ${weekLabel(weekStart, weekEnd)}`, html);
      if (ok) sent++;
      else errors.push(userId);
    } catch (e) {
      errors.push(`${userId}: ${(e as Error).message}`);
      console.error("[weekly-email]", userId, e);
    }
  }

  return new Response(JSON.stringify({ sent, total: targetUsers.length, errors }), {
    headers: { ...cors, "Content-Type": "application/json" },
  });
});
