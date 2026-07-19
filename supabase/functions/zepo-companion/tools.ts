// tools.ts — herramienta de consulta histórica de Zepi (agente lector, F1).
// El modelo pide la consulta vía el campo `tool` de su JSON de salida; el edge la ejecuta
// vía PostgREST con el JWT del usuario (RLS = solo sus filas) y devuelve SOLO agregados,
// nunca filas crudas. Los montos NUMERIC llegan como string por JSON → siempre Number().

export type ToolArgs = {
  name?: string;
  date_from?: string;
  date_to?: string;
  category?: string;
  is_income?: boolean;
  search?: string;
  group_by?: string;
};

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;
const PAGE = 1000;          // tope real de PostgREST por request
const MAX_PAGES = 5;        // 5000 filas máx por consulta (límite 60s del edge)
const MAX_RANGE_DAYS = 731; // ~24 meses

// Mismo mapa estándar del cliente (CATEGORIES + INCOME_CATEGORIES + legacy en index.html).
const STD_CATS: Record<string, string> = {
  food: "Comida", transport: "Transporte", market: "Mercado", health: "Salud",
  rent: "Vivienda", fun: "Ocio", shop: "Compras", coffee: "Café", pets: "Mascotas",
  savings: "Ahorro", invest_out: "Inversión", gym: "Gym", education: "Educación",
  travel: "Viaje", other: "Otro",
  salary: "Sueldo", freelance: "Freelance", business: "Negocio", investment: "Inversión",
  gift: "Regalo", refund: "Reembolso", rental: "Arriendo", sale: "Venta", other_income: "Otro",
  taxi: "Transporte",
};

const r2 = (x: number) => Math.round((Number(x) || 0) * 100) / 100;

function daysBetween(a: string, b: string): number {
  return Math.round((new Date(b + "T00:00:00Z").getTime() - new Date(a + "T00:00:00Z").getTime()) / 86400000);
}

// El modelo a veces manda "2025-3-5", "2025-03" (mes solo) o un ISO con hora.
// Normalizamos a YYYY-MM-DD en vez de rebotar el turno entero por formato.
export function normDay(s: unknown, endOfMonth: boolean): string {
  const str = String(s ?? "").trim().replace(/\//g, "-");
  const full = str.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (full) return `${full[1]}-${full[2].padStart(2, "0")}-${full[3].padStart(2, "0")}`;
  const ym = str.match(/^(\d{4})-(\d{1,2})$/);
  if (ym) {
    const y = Number(ym[1]), mo = Number(ym[2]);
    if (mo >= 1 && mo <= 12) {
      const day = endOfMonth ? new Date(Date.UTC(y, mo, 0)).getUTCDate() : 1;
      return `${ym[1]}-${ym[2].padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    }
  }
  return str; // inválido: lo atrapa ISO_DAY y el modelo recibe el error
}

// Acepta id ("food") o label visible ("Comida"), sin distinguir mayúsculas/acentos exactos.
// Devuelve TODAS las keys de BD que matchean (ej. "Transporte" → transport + taxi).
export function resolveCategory(input: string, custom: Record<string, string>): string[] {
  const norm = (s: string) => String(s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").trim();
  const want = norm(input);
  const keys: string[] = [];
  for (const [k, label] of Object.entries({ ...STD_CATS, ...custom })) {
    if (norm(k) === want || norm(label) === want) keys.push(k);
  }
  return [...new Set(keys)];
}

export async function runQueryRecords(supa: any, userId: string, t: ToolArgs): Promise<Record<string, unknown>> {
  const from = normDay(t.date_from, false);
  const to = normDay(t.date_to, true);
  if (!ISO_DAY.test(from) || !ISO_DAY.test(to)) {
    return { error: `invalid dates (got date_from="${String(t.date_from)}", date_to="${String(t.date_to)}"); retry ONCE with full ISO dates, e.g. {"date_from":"2025-03-01","date_to":"2025-03-31"}` };
  }
  if (from > to) return { error: "date_from must be <= date_to" };
  if (daysBetween(from, to) > MAX_RANGE_DAYS) return { error: "range too big: max 24 months per query" };

  // Labels de categorías propias del usuario (RLS: solo las suyas)
  const custom: Record<string, string> = {};
  try {
    const { data } = await supa.from("zepo_custom_categories").select("key,label").limit(200);
    (data || []).forEach((c: any) => { if (c.key && c.label) custom[c.key] = String(c.label); });
  } catch (_) { /* sin labels custom no se bloquea la consulta */ }

  let catKeys: string[] | null = null;
  let categoryNote: string | null = null;
  let search = typeof t.search === "string" ? t.search.trim() : "";
  if (typeof t.category === "string" && t.category.trim()) {
    catKeys = resolveCategory(t.category.slice(0, 40), custom);
    if (catKeys.length === 0) {
      catKeys = null;
      categoryNote = `category "${t.category.slice(0, 40)}" not found; showing all categories instead`;
    }
  }
  // Guardia: el modelo a veces pone la CATEGORÍA en search ("Transporte") — un ilike
  // sobre descripciones daría $0 (respuesta falsa). Si search matchea una categoría
  // conocida y no hay category, lo remapeamos.
  if (!catKeys && search) {
    const asCat = resolveCategory(search.slice(0, 40), custom);
    if (asCat.length > 0) {
      catKeys = asCat;
      search = "";
      categoryNote = `search "${t.search}" matched a category; filtered by category instead`;
    }
  }

  const rows: any[] = [];
  let truncated = false;
  for (let page = 0; page < MAX_PAGES; page++) {
    let q = supa.from("expenses")
      .select("amount,category,date,is_income,description")
      .eq("user_id", userId)
      .gte("date", from).lte("date", to)
      .order("date", { ascending: false }).order("id", { ascending: false })
      .range(page * PAGE, page * PAGE + PAGE - 1);
    if (catKeys) q = q.in("category", catKeys);
    if (typeof t.is_income === "boolean") q = q.eq("is_income", t.is_income);
    if (search) {
      q = q.ilike("description", "%" + search.slice(0, 40).replace(/[%,()]/g, "") + "%");
    }
    const { data, error } = await q;
    if (error) return { error: "query_failed: " + error.message };
    rows.push(...(data || []));
    if (!data || data.length < PAGE) break;
    if (page === MAX_PAGES - 1) truncated = true;
  }

  const label = (k: string) => custom[k] || STD_CATS[k] || k;
  let expensesTotal = 0, incomeTotal = 0;
  const byCat: Record<string, { total: number; n: number }> = {};
  const byMonth: Record<string, { expenses: number; income: number }> = {};
  for (const r of rows) {
    const amt = Number(r.amount) || 0;
    if (r.is_income) incomeTotal += amt; else expensesTotal += amt;
    const cl = label(String(r.category || "other")) + (r.is_income ? " (ingreso)" : "");
    byCat[cl] = byCat[cl] || { total: 0, n: 0 };
    byCat[cl].total += amt; byCat[cl].n++;
    const m = String(r.date).slice(0, 7);
    byMonth[m] = byMonth[m] || { expenses: 0, income: 0 };
    if (r.is_income) byMonth[m].income += amt; else byMonth[m].expenses += amt;
  }

  const out: Record<string, unknown> = {
    period: { from, to },
    scope: "all_spaces",
    count: rows.length,
    expenses_total: r2(expensesTotal),
    income_total: r2(incomeTotal),
    by_category: Object.entries(byCat)
      .sort((a, b) => b[1].total - a[1].total).slice(0, 12)
      .map(([cat, v]) => ({ cat, total: r2(v.total), n: v.n })),
    top_records: [...rows]
      .sort((a, b) => (Number(b.amount) || 0) - (Number(a.amount) || 0)).slice(0, 5)
      .map((r) => ({ d: String(r.description || "").slice(0, 40), amt: r2(Number(r.amount)), date: String(r.date).slice(0, 10), cat: label(String(r.category || "other")), income: !!r.is_income })),
  };
  if (Object.keys(byMonth).length > 1 || t.group_by === "month") {
    out.by_month = Object.entries(byMonth).sort()
      .map(([m, v]) => ({ month: m, expenses: r2(v.expenses), income: r2(v.income) }));
  }
  if (categoryNote) out.note = categoryNote;
  if (truncated) out.truncated = "more than 5000 rows; totals are partial, narrow the range";
  return out;
}
