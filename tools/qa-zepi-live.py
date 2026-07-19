#!/usr/bin/env python3
"""
QA E2E REAL: relay de voz de Zepi (F3) — live.zepo.lynoia.com -> Vertex Live API.

 1. /health responde 200 con el modelo pineado.
 2. WS sin token -> rechazado (el relay no deja pasar anonimos).
 3. WS con token de usuario FREE -> rechazado (voz es Max-only).
 4. WS con token MAX + setup -> Vertex contesta setupComplete (sesion Live real abierta).
 5. VOZ REAL (TTS 16k PCM16, mismo formato del cliente) por realtimeInput -> Zepi
    responde con AUDIO + turnComplete. (native-audio IGNORA turnos de texto — la
    prueba tiene que ser audio->audio como en la app.)

No prueba microfono/altavoz (eso es certificacion en iPhone); prueba TODO el camino
de red y auth que la voz usa. USO: python tools/qa-zepi-live.py
"""
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
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


def make_tts_pcm():
    """Voz real con Windows TTS: PCM16 crudo 16k mono (formato exacto del cliente) + 1.5s
    de silencio al final para que el VAD del modelo cierre el turno."""
    path = os.path.join(tempfile.gettempdir(), "zepi-qa-live.wav")
    ps = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$es = $s.GetInstalledVoices() | Where-Object {{ $_.VoiceInfo.Culture.Name -like 'es-*' -and $_.Enabled }} | Select-Object -First 1
if ($es) {{ $s.SelectVoice($es.VoiceInfo.Name); $phrase = 'hola zepi, saludame en una frase corta' }}
else {{ $phrase = 'hello zepi, say hi back in one short sentence' }}
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile('{path}', $fmt)
$s.Speak($phrase)
$s.Dispose()
"""
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, timeout=60)
    if not os.path.exists(path):
        raise RuntimeError(f"TTS local fallo: rc={out.returncode} err={(out.stderr or '')[-200:]}")
    return open(path, "rb").read()[44:] + b"\x00" * 48000


def try_ws(token, do_session=False, pcm=None):
    """Devuelve (conectado, setup_ok, got_audio, got_turn_complete)."""
    url = f"wss://{RELAY}/ws" + (f"?token={token}" if token else "")
    try:
        ws = ws_connect(url, open_timeout=20, close_timeout=5, max_size=10 * 1024 * 1024)
    except Exception:
        return False, False, False, False
    setup_ok = got_audio = got_turn = False
    try:
        if do_session:
            ws.send(json.dumps({"setup": {
                "model": "ignored-el-relay-lo-pinea",
                "generationConfig": {"responseModalities": ["AUDIO"]},
                "inputAudioTranscription": {}, "outputAudioTranscription": {},
            }}))
            deadline = time.time() + 45
            while time.time() < deadline:
                try:
                    raw = ws.recv(timeout=max(1, deadline - time.time()))
                except Exception:
                    break
                msg = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8", "ignore"))
                if "setupComplete" in msg:
                    setup_ok = True
                    # voz como la manda la app: chunks de 100ms por realtimeInput
                    for i in range(0, len(pcm or b""), 3200):
                        ws.send(json.dumps({"realtimeInput": {"audio": {
                            "data": base64.b64encode(pcm[i:i + 3200]).decode(),
                            "mimeType": "audio/pcm;rate=16000",
                        }}}))
                    deadline = time.time() + 45
                if "serverContent" in msg:
                    sc = msg["serverContent"]
                    for p in ((sc.get("modelTurn") or {}).get("parts") or []):
                        if (p.get("inlineData") or {}).get("data"):
                            got_audio = True
                    if sc.get("turnComplete"):
                        got_turn = True
                        if got_audio:
                            break
    finally:
        try:
            ws.close()
        except Exception:
            pass
    return True, setup_ok, got_audio, got_turn


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
    pcm = make_tts_pcm()
    ok_m, setup_ok, got_audio, got_turn = try_ws(jwt_max, do_session=True, pcm=pcm)
    check("4. WS max + setup -> setupComplete de Vertex", ok_m and setup_ok)
    check("5. voz real (realtimeInput) -> Zepi contesta con AUDIO + turnComplete",
          got_audio and got_turn, f"audio={got_audio} turn={got_turn}")

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
