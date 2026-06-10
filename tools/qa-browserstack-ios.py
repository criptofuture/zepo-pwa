#!/usr/bin/env python3
"""
QA en un iPHONE 11 REAL (BrowserStack) — Safari de verdad, no Chromium ni WebKit-desktop.

Por qué: ni Chromium (preview) ni WebKit-desktop (qa-ios-webkit.py) reproducen el
safe-area REAL del home-indicator ni el teclado físico de iOS. Esto sí: corre en un
iPhone 11 real en la nube, mide el inset REAL del dispositivo, y saca screenshots de
home / tour / teclado para ver lo que ve Alvaro.

Credenciales: NUNCA en código. Se leen de ~/.claude/skills/browserstack/config.json
(username + access_key). Si está vacío, el script avisa y sale.

Uso:  python tools/qa-browserstack-ios.py [URL]
      (default: https://dev.zepo-bca.pages.dev/pwa/)
Salida: medidas REALES + PNGs en %TEMP%/zepo-bstack/.
"""
import sys, os, json, time

CFG = os.path.expanduser(r"~/.claude/skills/browserstack/config.json")
OUT = os.path.join(os.environ.get("TEMP", "."), "zepo-bstack")
os.makedirs(OUT, exist_ok=True)
DEV_URL = "https://dev.zepo-bca.pages.dev/pwa/"
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"

def load_creds():
    if not os.path.exists(CFG):
        print("FALTA config:", CFG); sys.exit(2)
    c = json.load(open(CFG, encoding="utf-8"))
    u, k = c.get("username", ""), c.get("access_key", "")
    if not u or not k:
        print("Pega tu BrowserStack username + access_key en:", CFG); sys.exit(2)
    return u, k, c.get("hub", "https://hub-cloud.browserstack.com/wd/hub")

PREP = """
document.documentElement.classList.remove('browser-mode');
var g = document.getElementById('install-gate'); if (g) g.remove();
return getComputedStyle(document.documentElement).getPropertyValue('--safe-bottom');
"""
LOGIN = """
var done = arguments[arguments.length - 1];
var c = window.Alpine.$data(document.querySelector('#app'));
c.authMode='login'; c.authEmail=arguments[0]; c.authPassword=arguments[1];
Promise.resolve(c.handleAuth()).then(function(){ done(c.authError || ''); });
"""
MEASURE_BAR = """
var vh = window.innerHeight;
var bar = document.querySelector('.tab-bar');
var item = document.querySelector('.tab-item');
var sb = getComputedStyle(document.documentElement).getPropertyValue('--safe-bottom');
if (!bar) return {ok:false};
var b = bar.getBoundingClientRect(), i = item ? item.getBoundingClientRect() : null;
return {ok:true, vh:vh, safeBottom:sb.trim(), barH:Math.round(b.height),
        flush:Math.round(vh-b.bottom), labelGap: i?Math.round(vh-i.bottom):null};
"""

def main():
    user, key, hub = load_creds()
    url = sys.argv[1] if len(sys.argv) > 1 else DEV_URL
    from selenium import webdriver
    opts = webdriver.ChromeOptions()
    opts.set_capability("browserName", "safari")
    opts.set_capability("bstack:options", {
        "deviceName": "iPhone 11", "osVersion": "16", "realMobile": "true",
        "userName": user, "accessKey": key,
        "projectName": "Zepo", "buildName": "ios-qa", "sessionName": "home+tour+teclado",
    })
    print("Conectando a iPhone 11 real (BrowserStack)...")
    drv = webdriver.Remote(command_executor=hub, options=opts)
    try:
        drv.set_page_load_timeout(60)
        drv.get(url)
        time.sleep(3)
        safe = drv.execute_script(PREP)
        print("safe-bottom REAL del dispositivo (pre-login):", safe)
        drv.set_script_timeout(40)
        err = drv.execute_async_script(LOGIN, DEMO_EMAIL, DEMO_PASS)
        if err:
            print("LOGIN FALLA:", err); return 1
        time.sleep(5)
        for theme in ("light", "dark"):
            drv.execute_script(
                "if(arguments[0]==='dark')document.documentElement.setAttribute('data-theme','dark');"
                "else document.documentElement.removeAttribute('data-theme');"
                "var c=window.Alpine.$data(document.querySelector('#app'));"
                "c.showOnbV2=false;c.showWelcomeCarousel=false;c.sheetOpen=false;c.a7Active=false;c.tab='home';", theme)
            time.sleep(1.2)
            drv.save_screenshot(os.path.join(OUT, f"real-home-{theme}.png"))
            m = drv.execute_script(MEASURE_BAR)
            print(f"[{theme}] BARRA real -> {m}")
            # Tour: abrir sheet + globito flotante
            drv.execute_script("var c=window.Alpine.$data(document.querySelector('#app'));"
                               "c._a7done();c.a7Active=true;c.a7Step=1;c.openNew();")
            time.sleep(1.6)
            drv.save_screenshot(os.path.join(OUT, f"real-tour-{theme}.png"))
            # Teclado real: tocar el textarea
            try:
                ta = drv.find_element("id", "a7-desc"); ta.click(); time.sleep(2.0)
                drv.save_screenshot(os.path.join(OUT, f"real-keyboard-{theme}.png"))
            except Exception as e:
                print("  (no pude tocar el textarea:", e, ")")
            drv.execute_script("var c=window.Alpine.$data(document.querySelector('#app'));"
                               "c._a7done();c.sheetOpen=false;c.a7Active=false;document.activeElement&&document.activeElement.blur();")
            time.sleep(1.0)
        print("\nScreenshots reales en:", OUT)
        return 0
    finally:
        drv.quit()

if __name__ == "__main__":
    sys.exit(main())
