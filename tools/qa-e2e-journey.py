#!/usr/bin/env python3
"""
QA E2E (nube): Journey 30 dias + trials (v178).

Flujo real contra Supabase con la cuenta free@zepo.test (plan free REAL):
  1. baseline: sin gastos, sin fila de journey, sin trial
  2. login -> loadJourney crea la fila (backfilled) y la tarjeta Home es visible
  3. guardar un gasto real (saveExpense) -> mision exp_first + racha 1 + persiste en BD
  4. reclamar ch1 con misiones incompletas -> el RPC lo RECHAZA
  5. completar ch1 (misiones cliente + >=3 gastos reales) -> reclamar ch1 ->
     users.trial_plan='pro' vigente y userPlan/hasPlan('pro') = true (candado free levantado)
  6. anti-trampa: escribir 'rewards' directo como usuario -> el trigger lo descarta
  7. reclamar 'final' sin capitulos previos -> RECHAZADO
  8. cleanup total (trial a NULL, journey y gastos QA fuera) — OBLIGATORIO:
     otros E2E (plan-gating) asumen free@zepo.test sin trial.
Sale 1 si algo falla. Limpia siempre (admin).
"""
import sys, os, json, socket, threading, http.server, functools, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

PWA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cfg
CFG = qa_cfg.load(PWA_DIR)
URL, SK = CFG["url"], CFG["secret_key"]
EMAIL = "free@zepo.test"; PASS = "ZepoQA2026!"
H = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json",
     "Prefer": "return=representation"}


def admin(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(URL + path, headers=H, method=method, data=data)
    try:
        with urllib.request.urlopen(r) as resp:
            t = resp.read().decode() or "[]"
            return resp.status, (json.loads(t) if t[:1] in "[{" else t)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def user_id():
    s, u = admin("GET", "/auth/v1/admin/users?page=1&per_page=200")
    if isinstance(u, dict):
        for x in u.get("users", []):
            if x.get("email") == EMAIL:
                return x["id"]
    return None


def cleanup(uid):
    admin("PATCH", f"/rest/v1/users?id=eq.{uid}",
          {"trial_plan": None, "trial_until": None, "journey_discount": False})
    admin("DELETE", f"/rest/v1/zepo_journey?user_id=eq.{uid}")
    admin("DELETE", f"/rest/v1/expenses?user_id=eq.{uid}")


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def serve(port):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PWA_DIR)
    srv = http.server.HTTPServer(("127.0.0.1", port), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start(); return srv


LOGIN = """
async ([email, password]) => {
  document.documentElement.classList.remove('browser-mode');
  const g = document.getElementById('install-gate'); if (g) g.remove();
  const c = window.Alpine.$data(document.querySelector('#app'));
  c.authMode='login'; c.authEmail=email; c.authPassword=password;
  await c.handleAuth(); return c.authError || '';
}
"""


def run():
    uid = user_id()
    if not uid:
        print("[FALLA] no encontre free@zepo.test"); return 1
    cleanup(uid)

    port = free_port(); serve(port)
    url = f"http://127.0.0.1:{port}/index.html"
    fails = []

    def check(name, ok, extra=""):
        print(("  [PASS] " if ok else "  [FALLA] ") + name + (" " + str(extra) if extra and not ok else ""))
        if not ok:
            fails.append(name)

    try:
        with sync_playwright() as p:
            browser = p.webkit.launch()
            page = browser.new_context(viewport={"width": 390, "height": 844}).new_page()
            page.on("dialog", lambda d: d.accept())
            page.goto(url, wait_until="domcontentloaded"); page.wait_for_timeout(1200)
            page.wait_for_function("()=>window.Alpine && window.Alpine.$data(document.querySelector('#app'))", timeout=15000)
            err = page.evaluate(LOGIN, [EMAIL, PASS])
            if err:
                print("[FALLA] login:", err); browser.close(); cleanup(uid); return 1
            page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.user;}", timeout=20000)

            # 1. loadJourney crea la fila y hace backfill
            page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!c.jrn && c.jrn.backfilled;}", timeout=20000)
            s, rows = admin("GET", f"/rest/v1/zepo_journey?user_id=eq.{uid}&select=*")
            check("fila zepo_journey creada", s == 200 and isinstance(rows, list) and len(rows) == 1, rows)

            # 2. tarjeta Home visible (sin misiones aun, sin dismiss)
            vis = page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return c.jrnCardVisible;}")
            check("tarjeta journey visible en Home", vis is True)

            # 3. guardar un gasto REAL por el metodo del app -> mision + racha
            page.evaluate("""async ()=>{
              const c = window.Alpine.$data(document.querySelector('#app'));
              c.openNew();
              c.form.amount = '7.77'; c.form.category = 'food';
              c.form.description = 'QA journey gasto';
              await c.saveExpense();
            }""")
            page.wait_for_function("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return !!(c.jrn && c.jrn.missions.exp_first);}", timeout=10000)
            got = page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return {streak:c.jrn.streak_days, cat:!!c.jrn.missions.cat_assign};}")
            check("mision exp_first marcada", True)
            check("racha = 1 tras primer registro", got["streak"] == 1, got)
            check("cat_assign marcada (categoria valida)", got["cat"] is True)

            # 4. persistencia (debounce ~900ms)
            page.wait_for_timeout(1800)
            s, rows = admin("GET", f"/rest/v1/zepo_journey?user_id=eq.{uid}&select=missions,streak_days")
            mis = (rows[0].get("missions") or {}) if (s == 200 and rows) else {}
            check("misiones persistidas en BD", "exp_first" in mis, rows)

            # 5. reclamo prematuro de ch1 -> rechazado
            res = page.evaluate("""async ()=>{
              const c = window.Alpine.$data(document.querySelector('#app'));
              const { data } = await sb.rpc('zepo_claim_journey_reward', { p_chapter: 'ch1' });
              return data;
            }""")
            check("RPC rechaza ch1 incompleto", isinstance(res, dict) and not res.get("ok") and res.get("error") == "missions_incomplete", res)

            # 6. completar ch1: misiones (cliente) + >=3 gastos reales (admin)
            today = page.evaluate("()=>localDate()")
            admin("POST", "/rest/v1/expenses", [
                {"user_id": uid, "amount": 1.11, "category": "food", "description": "QA journey seed 1", "date": today, "is_income": False},
                {"user_id": uid, "amount": 2.22, "category": "transport", "description": "QA journey seed 2", "date": today, "is_income": False},
            ])
            page.evaluate("""async ()=>{
              const c = window.Alpine.$data(document.querySelector('#app'));
              const ts = new Date().toISOString();
              ['exp_first','inc_first','cat_assign','pm_add','streak_3'].forEach(k => { if (!c.jrn.missions[k]) c.jrn.missions[k] = ts; });
              await c._jrnSave();
            }""")
            res = page.evaluate("""async ()=>{
              const c = window.Alpine.$data(document.querySelector('#app'));
              const ch = c.JRN_CHAPTERS[0];
              await c.jrnClaim(ch);
              return { rewards: c.jrn.rewards, plan: c.userPlan, has: c.hasPlan('pro'), trial: c.trialPlan };
            }""")
            check("reclamo ch1 acredita en cliente", isinstance(res, dict) and "ch1" in (res.get("rewards") or {}), res)
            check("userPlan sube a pro por trial", res.get("plan") == "pro" and res.get("has") is True, res)
            s, urow = admin("GET", f"/rest/v1/users?id=eq.{uid}&select=trial_plan,trial_until,plan")
            u = urow[0] if (s == 200 and urow) else {}
            check("BD: trial_plan=pro + trial_until futuro", u.get("trial_plan") == "pro" and (u.get("trial_until") or "") > "2026", u)
            check("BD: plan pagado sigue free", u.get("plan") == "free", u)

            # 7. anti-trampa: rewards directo como usuario -> trigger lo descarta
            page.evaluate("""async ()=>{
              await sb.from('zepo_journey').update({ rewards: { ch1: 'x', ch2: 'x', ch3: 'x', ch4: 'x', final: 'x' } }).eq('user_id', (window.Alpine.$data(document.querySelector('#app'))).user.id);
            }""")
            s, rows = admin("GET", f"/rest/v1/zepo_journey?user_id=eq.{uid}&select=rewards")
            rw = (rows[0].get("rewards") or {}) if (s == 200 and rows) else {}
            check("trigger protege rewards (solo ch1 legitimo)", ("ch1" in rw) and ("ch4" not in rw) and ("final" not in rw), rw)

            # 8. reclamar final sin capitulos -> rechazado
            res = page.evaluate("""async ()=>{
              const { data } = await sb.rpc('zepo_claim_journey_reward', { p_chapter: 'final' });
              return data;
            }""")
            check("RPC rechaza final prematuro", isinstance(res, dict) and not res.get("ok"), res)

            # 9. dismiss oculta la tarjeta y persiste
            page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));c.jrnDismissCard();}")
            vis = page.evaluate("()=>{const c=window.Alpine.$data(document.querySelector('#app'));return c.jrnCardVisible;}")
            check("dismiss oculta la tarjeta", vis is False)

            browser.close()
    finally:
        cleanup(uid)
        s, urow = admin("GET", f"/rest/v1/users?id=eq.{uid}&select=trial_plan")
        if not (s == 200 and urow and urow[0].get("trial_plan") is None):
            print("[FALLA] cleanup: trial_plan NO quedo NULL — arreglar a mano"); fails.append("cleanup")

    print()
    if fails:
        print(f"[FALLA] qa-e2e-journey: {len(fails)} fallas: {fails}")
        return 1
    print("[OK] qa-e2e-journey: TODO PASS")
    return 0


if __name__ == "__main__":
    sys.exit(run())
