#!/usr/bin/env python3
"""
QA E2E REAL: relay de voz de Zepi (F3) — live.zepo.lynoia.com -> Vertex Live API.

 1. /health responde 200 con el modelo pineado.
 2. WS sin token -> rechazado (el relay no deja pasar anonimos).
 3. WS con token de usuario FREE -> rechazado (voz es Max-only).
 4. WS con token MAX + setup -> Vertex contesta setupComplete (sesion Live real abierta).
 5. Turno de texto "responde solo: hola" -> llega serverContent con audio o texto + turnComplete.

No prueba microfono/altavoz (eso es certificacion en iPhone); prueba TODO el camino
de red y auth que la voz usa. USO: python tools/qa-zepi-live.py
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
except Exception:
    pass

TOOLS = os.path.dirname(os.path.abspath(__file__))
PWA = os.path.dirname(TOOLS)
ZEPO_CFG = "C:/Users/alvar/lynoia/clients/zepo/config.json"
PASSWORD = "ZepoQA2026!"
RELAY = "live.zepo.lynoia.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) lynoia-cli/1.0"

try:
    from websockets.sync.client import connect as ws_connect
    from websockets.exceptions import InvalidStatus
except ImportError:
    print("SKIP: falta el paquete websockets (pip install websockets)")
    sys.exit(0)

z = json.load(open(ZEPO_CFG, encoding="utf-8"))
sb = z.get("supabase", z)
BASE = (sb.get("url") or "").rstrip("/")
html = open(os.path.join(PWA, "index.html"), encoding="utf-8").read()
PUB = re.search(r"sb_publishable_[A-Za-z0-9_-]+", html).group(0)


def login(email):
    last = None
    for wait in (0, 8, 20):
        if wait:
            time.sleep(wait)
        try:
            body = json.dumps({"email": email, "password": PASSWORD}).encode()
            r = urllib.request.Request(f"{BASE}/auth/v1/token?grant_type=password", data=body, method="POST",
                                       headers={"apikey": PUB, "Content-Type": "application/json", "User-Agent": UA})
            return json.loads(urllib.request.urlopen(r, timeout=30).read().decode())["access_token"]
        except Exception as e:
            last = e
            print(f"  ... login {email} fallo ({e}); reintento")
    raise RuntimeError(f"login imposible: {last}")


def try_ws(token, do_session=False):
    """Devuelve (conectado, setup_ok, got_content, got_turn_complete)."""
    url = f"wss://{RELAY}/ws" + (f"?token={token}" if token else "")
    try:
        ws = ws_connect(url, open_timeout=20, close_timeout=5, max_size=10 * 1024 * 1024)
    except Exception:
        return False, False, False, False
    setup_ok = got_content = got_turn = False
    try:
        if do_session:
            ws.send(json.dumps({"setup": {
                "model": "ignored-el-relay-lo-pinea",
                "generationConfig": {"responseModalities": ["AUDIO"]},
            }}))
            deadline = time.time() + 30
            while time.time() < deadline:
                try:
                    raw = ws.recv(timeout=max(1, deadline - time.time()))
                except Exception:
                    break
                msg = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8", "ignore"))
                if "setupComplete" in msg:
                    setup_ok = True
                    ws.send(json.dumps({"clientContent": {
                        "turns": [{"role": "user", "parts": [{"text": "responde solo: hola"}]}],
                        "turnComplete": True,
                    }}))
                    deadline = time.time() + 40
                if "serverContent" in msg:
                    sc = msg["serverContent"]
                    if sc.get("modelTurn") or sc.get("outputTranscription"):
                        got_content = True
                    if sc.get("turnComplete"):
                        got_turn = True
                        break
    finally:
        try:
            ws.close()
        except Exception:
            pass
    return True, setup_ok, got_content, got_turn


def main():
    print("=== QA Zepi voz (relay + Vertex Live reales) ===")
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond)))
        print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

    req = urllib.request.Request(f"https://{RELAY}/health", headers={"User-Agent": UA})
    h = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
    check("1. /health 200 con modelo pineado", h.get("ok") is True and "live" in str(h.get("model", "")), f"h={h}")

    ok, _, _, _ = try_ws(None)
    check("2. WS sin token -> rechazado", not ok)

    jwt_free = login("free@zepo.test")
    ok_f, _, _, _ = try_ws(jwt_free)
    check("3. WS con token free -> rechazado (voz Max-only)", not ok_f)

    jwt_max = login("max@zepo.test")
    ok_m, setup_ok, got_content, got_turn = try_ws(jwt_max, do_session=True)
    check("4. WS max + setup -> setupComplete de Vertex", ok_m and setup_ok)
    check("5. turno de texto -> serverContent + turnComplete", got_content and got_turn,
          f"content={got_content} turn={got_turn}")

    passed = sum(1 for _, ok2 in results if ok2)
    print(f"\n{passed}/{len(results)} PASS")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"FATAL: {type(e).__name__}: {e}")
        sys.exit(1)
