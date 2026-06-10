#!/usr/bin/env python3
"""
QA en iPHONES REALES (BrowserStack) — Safari de verdad, no Chromium ni WebKit-desktop.

Por qué: ni Chromium (preview) ni WebKit-desktop reproducen el safe-area REAL del
dispositivo ni el teclado físico de iOS. Esto sí: corre en iPhones reales en la nube,
mide el inset REAL (env(safe-area-inset-bottom)) y saca screenshots de home/tour.

Credenciales: NUNCA en código. Se leen de ~/.claude/skills/browserstack/config.json.
Uso:  python tools/qa-browserstack-ios.py [URL]   (default: dev de Zepo)
Salida: medidas REALES + PNGs en %TEMP%/zepo-bstack/.
"""
import sys, os, json, time

CFG = os.path.expanduser(r"~/.claude/skills/browserstack/config.json")
OUT = os.path.join(os.environ.get("TEMP", "."), "zepo-bstack")
os.makedirs(OUT, exist_ok=True)
DEV_URL = "https://dev.zepo-bca.pages.dev/pwa/"
DEMO_EMAIL, DEMO_PASS = "demo@zepo.test", "ZepoDemo2026!"
DEVICES = [("iPhone 11", "16"), ("iPhone 15 Pro", "17")]

def load_creds():
    c = json.load(open(CFG, encoding="utf-8"))
    if not c.get("username") or not c.get("access_key"):
        print("Pega username + access_key en", CFG); sys.exit(2)
    return c["username"], c["access_key"], c.get("hub", "https://hub-cloud.browserstack.com/wd/hub")

REMOVE_GATE = ("document.documentElement.classList.remove('browser-mode');"
               "var g=document.getElementById('install-gate'); if(g) g.remove();"
               "return getComputedStyle(document.documentElement).getPropertyValue('--safe-bottom').trim();")
LOGIN = ("var done=arguments[arguments.length-1];"
         "var c=window.Alpine.$data(document.querySelector('#app'));"
         "c.authMode='login'; c.authEmail=arguments[0]; c.authPassword=arguments[1];"
         "Promise.resolve(c.handleAuth()).then(function(){done(c.authError||'');});")
MEASURE = """
var vh=window.innerHeight;
var bar=document.querySelector('.tab-bar'); var item=document.querySelector('.tab-item');
if(!bar) return {ok:false};
var b=bar.getBoundingClientRect(), i=item?item.getBoundingClientRect():null;
var sb=getComputedStyle(document.documentElement).getPropertyValue('--safe-bottom').trim();
var sbb=getComputedStyle(document.documentElement).getPropertyValue('--safe-bottom-bar').trim();
return {ok:true, vh:vh, safeBottom:sb, safeBottomBar:sbb, barTop:Math.round(b.top),
        barH:Math.round(b.height), flush:Math.round(vh-b.bottom), labelGap:i?Math.round(vh-i.bottom):null,
        barBg:getComputedStyle(bar).backgroundColor};
"""

def wait_alpine(drv, timeout=60):
    end = time.time() + timeout
    chk = ("try{var c=window.Alpine&&window.Alpine.$data(document.querySelector('#app'));"
           "return !!(c&&typeof c.handleAuth==='function');}catch(e){return false;}")
    while time.time() < end:
        try:
            if drv.execute_script("return (function(){" + chk + "})();"): return True
        except Exception:
            pass
        time.sleep(1.5)
    return False

def run_device(name, osv, user, key, hub, url):
    from selenium import webdriver
    opts = webdriver.ChromeOptions()
    opts.set_capability("browserName", "safari")
    opts.set_capability("bstack:options", {
        "deviceName": name, "osVersion": osv, "realMobile": "true",
        "userName": user, "accessKey": key,
        "projectName": "Zepo", "buildName": "ios-qa-v127", "sessionName": name,
    })
    tag = name.replace(" ", "")
    print(f"\n=== {name} (iOS {osv}) ===\nConectando...")
    drv = webdriver.Remote(command_executor=hub, options=opts)
    try:
        drv.set_page_load_timeout(70); drv.set_script_timeout(45)
        drv.get(url); time.sleep(3)
        safe = drv.execute_script(REMOVE_GATE)
        print(f"  safe-bottom REAL (env) = {safe!r}")
        if not wait_alpine(drv):
            print("  [FALLA] Alpine no cargó a tiempo"); return
        err = drv.execute_async_script(LOGIN, DEMO_EMAIL, DEMO_PASS)
        if err:
            print("  [FALLA] login:", err); return
        time.sleep(5)
        for theme in ("light", "dark"):
            drv.execute_script(
                "var d=document.documentElement;"
                "if(arguments[0]==='dark')d.setAttribute('data-theme','dark');else d.removeAttribute('data-theme');"
                "var c=window.Alpine.$data(document.querySelector('#app'));"
                "c.showOnbV2=false;c.showWelcomeCarousel=false;c.sheetOpen=false;c.a7Active=false;c.tab='home';", theme)
            time.sleep(1.4)
            drv.save_screenshot(os.path.join(OUT, f"{tag}-home-{theme}.png"))
            m = drv.execute_script(MEASURE)
            print(f"  [{theme}] {m}")
        # Simula el PWA INSTALADO: inyecta safe-bottom=34 (lo que reporta el iPhone con
        # home-indicator). Mide el reserve real que verá Alvaro instalado.
        drv.execute_script("var d=document.documentElement; d.removeAttribute('data-theme');"
                           "var s=document.createElement('style'); s.textContent=':root{--safe-bottom:34px !important;}'; document.head.appendChild(s);")
        time.sleep(1.0)
        drv.save_screenshot(os.path.join(OUT, f"{tag}-home-inset34.png"))
        print(f"  [inset34 = PWA instalado] {drv.execute_script(MEASURE)}")
        # Tour flotante: paso escribir
        drv.execute_script("var c=window.Alpine.$data(document.querySelector('#app'));"
                           "c._a7done();c.a7Active=true;c.a7Step=1;c.openNew();")
        time.sleep(1.8)
        drv.save_screenshot(os.path.join(OUT, f"{tag}-tour-write.png"))
        # Paso REVISAR/GUARDAR: fuerza el resultado y verifica que el globito final NO
        # tape el textarea (va arriba, sobre el resultado).
        drv.execute_script("var c=window.Alpine.$data(document.querySelector('#app'));"
                           "c.parsedItems=[{description:'sopa',amount:5,category:'food'}]; c.analyzed=true;")
        time.sleep(1.6)
        drv.save_screenshot(os.path.join(OUT, f"{tag}-tour-review.png"))
        sv = drv.execute_script("""
          var pop=document.querySelector('.driver-popover'); var ta=document.querySelector('#a7-desc');
          if(!pop||!ta) return {shown:false};
          var p=pop.getBoundingClientRect(), a=ta.getBoundingClientRect();
          return {shown:true, overlapsTextarea:(p.bottom>a.top+6 && p.top<a.bottom-6), popTop:Math.round(p.top), taTop:Math.round(a.top)};
        """)
        print(f"  [tour revisar] globito vs textarea -> {sv}")
        drv.execute_script("var c=window.Alpine.$data(document.querySelector('#app'));"
                           "c._a7done();c.sheetOpen=false;c.a7Active=false;c.parsedItems=[];")
        print(f"  screenshots -> {tag}-home-*/tour-write/tour-review.png")
    finally:
        drv.quit()

def main():
    user, key, hub = load_creds()
    url = sys.argv[1] if len(sys.argv) > 1 else DEV_URL
    print("URL:", url)
    for name, osv in DEVICES:
        try:
            run_device(name, osv, user, key, hub, url)
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
    print("\nScreenshots reales en:", OUT)

if __name__ == "__main__":
    main()
