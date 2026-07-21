// intents.ts — acciones con confirmación de Zepi (F2 registrar / F6 presupuesto+split).
// El modelo emite `intent` dentro de su JSON; aquí SOLO se sanitiza (whitelist de tipos,
// montos, fechas, categorías). El edge NUNCA escribe: el CLIENTE ejecuta tras la tarjeta
// "¿Registro esto?" reutilizando los flujos probados (saveMultiItems / saveBudgets / hoja "+").

import { normDay, resolveCategory } from "./tools.ts";

const MAX_ITEMS = 10;
const MAX_AMOUNT = 99999;
const MAX_BUDGET = 999999;
const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

const INCOME_KEYS = new Set(["salary", "freelance", "business", "investment", "gift", "refund", "rental", "sale", "other_income"]);

const r2 = (x: number) => Math.round((Number(x) || 0) * 100) / 100;

// Resuelve a UNA key de BD: prefiere la que coincide en gasto/ingreso y evita la legacy "taxi".
function pickCategory(input: unknown, custom: Record<string, string>, wantIncome: boolean): string | null {
  if (typeof input !== "string" || !input.trim()) return null;
  const keys = resolveCategory(input.slice(0, 40), custom);
  if (keys.length === 0) return null;
  const match = keys.find((k) => k !== "taxi" && INCOME_KEYS.has(k) === wantIncome);
  return match || keys.find((k) => k !== "taxi") || keys[0];
}

function cleanText(s: unknown, max: number): string {
  return String(s ?? "").replace(/\s+/g, " ").trim().slice(0, max);
}

// Fecha del registro: ISO válida y NUNCA futura; cualquier cosa rara cae a hoy.
function cleanDay(s: unknown, today: string): string {
  const d = normDay(s, false);
  if (!ISO_DAY.test(d) || d < "2000-01-01") return today;
  return d > today ? today : d;
}

export async function sanitizeIntent(
  supa: any,
  raw: any,
  today: string,
  plan: string,
): Promise<{ ok?: Record<string, unknown>; err?: string }> {
  const kind = String(raw?.kind || "");
  if (!["add_records", "set_budget", "split_handoff", "edit_record", "mark_paid", "accept_cobro", "remind_whatsapp", "delete_record", "set_goal"].includes(kind)) {
    return { err: `unknown intent kind "${kind.slice(0, 24)}"` };
  }

  // Labels de categorías propias del usuario (RLS: solo las suyas)
  const custom: Record<string, string> = {};
  try {
    const { data } = await supa.from("zepo_custom_categories").select("key,label").limit(200);
    (data || []).forEach((c: any) => { if (c.key && c.label) custom[c.key] = String(c.label); });
  } catch (_) { /* sin labels custom no se bloquea */ }

  if (kind === "add_records") {
    const rawItems = Array.isArray(raw.items) ? raw.items.slice(0, MAX_ITEMS) : [];
    if (rawItems.length === 0) {
      return { err: "add_records needs items[] with at least one {amount, description, category}" };
    }
    const items: Record<string, unknown>[] = [];
    for (const it of rawItems) {
      const amount = r2(Number(it?.amount));
      if (!Number.isFinite(amount) || amount <= 0 || amount > MAX_AMOUNT) {
        return { err: `invalid amount "${String(it?.amount).slice(0, 20)}" (each item needs amount > 0 and <= ${MAX_AMOUNT})` };
      }
      const isIncome = it?.is_income === true;
      items.push({
        amount,
        description: cleanText(it?.description, 80),
        category: pickCategory(it?.category, custom, isIncome) || (isIncome ? "other_income" : "other"),
        is_income: isIncome,
        date: cleanDay(it?.date, today),
      });
    }
    return { ok: { kind, items } };
  }

  if (kind === "set_budget") {
    const amount = r2(Number(raw?.amount));
    if (!Number.isFinite(amount) || amount <= 0 || amount > MAX_BUDGET) {
      return { err: `invalid budget amount (must be > 0 and <= ${MAX_BUDGET})` };
    }
    const catRaw = cleanText(raw?.category, 40);
    const elitePlus = plan === "elite" || plan === "max";
    // El TOTAL de Elite+ se deriva de las categorías (fijarlo directo lo pisaría a 0);
    // Pro solo tiene total. Espejo exacto de saveBudgets() en el cliente.
    if (elitePlus && !catRaw) {
      return { err: "this user is Elite/Max: their TOTAL budget is computed from category budgets — ask WHICH category to budget (category is required)" };
    }
    if (!elitePlus && catRaw) {
      return { err: "per-category budgets need Elite; this user can only set the TOTAL monthly budget (omit category) — you may offer the Elite upgrade" };
    }
    let category: string | null = null;
    if (catRaw) {
      category = pickCategory(catRaw, custom, false);
      if (!category) return { err: `unknown category "${catRaw}" — use the exact labels the user sees in the app` };
    }
    return { ok: { kind, amount, category } };
  }

  // Acciones sobre un registro EXISTENTE (#3): el edge NO tiene el mapa de tokens.
  // Solo valida la FORMA del id ordinal (r#/c#); el cliente lo resuelve a la fila real.
  const REF_R = /^r\d{1,3}$/;
  const REF_C = /^c\d{1,3}$/;

  if (kind === "edit_record") {
    const id = String(raw?.id || "");
    if (!REF_R.test(id)) {
      return { err: `invalid record id "${id.slice(0, 12)}" — reference a record from SNAPSHOT.recentRecords by its "r#" token (never a uuid)` };
    }
    const p = (raw?.patch && typeof raw.patch === "object") ? raw.patch : {};
    const patch: Record<string, unknown> = {};
    if (p.amount !== undefined) {
      const amount = r2(Number(p.amount));
      if (!Number.isFinite(amount) || amount <= 0 || amount > MAX_AMOUNT) {
        return { err: `invalid amount "${String(p.amount).slice(0, 20)}" (must be > 0 and <= ${MAX_AMOUNT})` };
      }
      patch.amount = amount;
    }
    if (p.description !== undefined) patch.description = cleanText(p.description, 80);
    if (p.category !== undefined) {
      const category = pickCategory(p.category, custom, false);
      if (!category) return { err: `unknown category "${cleanText(p.category, 40)}" — use the exact labels the user sees` };
      patch.category = category;
    }
    if (p.date !== undefined) patch.date = cleanDay(p.date, today);
    if (Object.keys(patch).length === 0) {
      return { err: "edit_record needs patch{} with at least one field to change (amount, description, category or date)" };
    }
    return { ok: { kind, id, patch } };
  }

  if (kind === "mark_paid" || kind === "accept_cobro" || kind === "remind_whatsapp") {
    const id = String(raw?.id || "");
    if (!REF_C.test(id)) {
      return { err: `invalid cobro id "${id.slice(0, 12)}" — reference a pending cobro from SNAPSHOT.cobros by its "c#" token (never a uuid)` };
    }
    return { ok: { kind, id } };
  }

  if (kind === "delete_record") {
    // Solo valida la FORMA del ref-token (r#). El edge NO tiene el mapa: el CLIENTE resuelve
    // el uuid real (RLS), muestra la fila completa y pide 2a confirmación (askConfirm) antes de
    // borrar. SIEMPRE 1 registro — jamás borrado masivo. Un id alucinado no resuelve → no borra.
    // Solo r# (registros); c# son cobros y se cancelan por otra vía, no por delete_record.
    const id = String(raw?.id || "").trim();
    if (!/^r\d{1,3}$/.test(id)) {
      return { err: `delete_record needs a valid record ref id like "r3" from SNAPSHOT.recentRecords (got "${id.slice(0, 24)}")` };
    }
    return { ok: { kind, id } };
  }

  if (kind === "set_goal") {
    const gk = String(raw?.goal_kind || "");
    if (!["save", "limit", "debt"].includes(gk)) {
      return { err: `set_goal needs goal_kind = "save" | "limit" | "debt"` };
    }
    const target = r2(Number(raw?.target_amount));
    if (!Number.isFinite(target) || target <= 0 || target > 9999999) {
      return { err: `invalid target_amount (must be > 0 and <= 9999999)` };
    }
    const title = cleanText(raw?.title, 80);
    let category: string | null = null;
    if (gk === "limit") {
      const catRaw = cleanText(raw?.category, 40);
      if (catRaw) {
        category = pickCategory(catRaw, custom, false);
        if (!category) return { err: `unknown category "${catRaw}" — use the exact labels the user sees` };
      }
    }
    // deadline SI puede ser futura (a diferencia de la fecha de un registro): no se clampa.
    let deadline: string | null = null;
    const dl = normDay(raw?.deadline, false);
    if (ISO_DAY.test(dl) && dl >= "2000-01-01") deadline = dl;
    return { ok: { kind, goal_kind: gk, title, target_amount: target, category, deadline } };
  }

  // split_handoff — solo pre-llena la hoja "+"; el usuario elige personas y guarda allá.
  const total = r2(Number(raw?.total));
  if (!Number.isFinite(total) || total <= 0 || total > MAX_AMOUNT) {
    return { err: `invalid split total (must be > 0 and <= ${MAX_AMOUNT})` };
  }
  return {
    ok: {
      kind,
      total,
      description: cleanText(raw?.description, 80),
      person: cleanText(raw?.person, 40) || null,
      category: pickCategory(raw?.category, custom, false),
    },
  };
}
