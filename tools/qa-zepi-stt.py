#!/usr/bin/env python3
"""
QA E2E REAL: dictado de Zepi (mode=stt en zepo-companion, edge desplegado).

 1. free -> 403 (el dictado es de la probadita pro+, no free).
 2. max sin audio -> 400 empty_input.
 3. max con audio gigante -> 400 audio_too_long (tope ~60s).
 4. max con WAV de VOZ REAL (TTS de Windows) -> 200 y la transcripcion trae la frase.
 5. pro con el mismo WAV -> 200 (el dictado NO es Max-only; alimenta el cupo del chat).

El WAV se sintetiza al vuelo con System.Speech (Windows PowerShell 5) a 16k mono PCM16 —
el MISMO formato que arma el cliente (_zdWav). USO: python tools/qa-zepi-stt.py
"""
import base64
import json
import os
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
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) lynoia-cli/1.0"

z = json.load(open(ZEPO_CFG, encoding="utf-8"))
sb = z.get("supabase", z)
BASE = (sb.get("url") or "").rstrip("/")
import re
html = open(os.path.join(PWA, "index.html"), encoding="utf-8").read()
PUB = re.search(r"sb_publishable_[A-Za-z0-9_-]+", html).group(0)
FN = f"{BASE}/functions/v1/zepo-companion"


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


def call_stt(jwt, audio_b64, mime="audio/wav"):
    body = json.dumps({"mode": "stt", "audio": audio_b64, "mime": mime}).encode()
    req = urllib.request.Request(FN, data=body, method="POST",
                                 headers={"apikey": PUB, "Authorization": f"Bearer {jwt}",
                                          "Content-Type": "application/json", "User-Agent": UA})
    try:
        resp = urllib.request.urlopen(req, timeout=90)
        return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def make_tts_wav():
    """Sintetiza voz real (16k mono PCM16) con Windows PowerShell 5. Devuelve (b64, keywords)."""
    path = os.path.join(tempfile.gettempdir(), "zepi-qa-stt.wav")
    ps = f"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$es = $s.GetInstalledVoices() | Where-Object {{ $_.VoiceInfo.Culture.Name -like 'es-*' -and $_.Enabled }} | Select-Object -First 1
if ($es) {{ $s.SelectVoice($es.VoiceInfo.Name); $phrase = 'cinco dolares de almuerzo y tres de taxi'; $lang = 'es' }}
else {{ $phrase = 'five dollars for lunch and three for taxi'; $lang = 'en' }}
$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile('{path}', $fmt)
$s.Speak($phrase)
$s.Dispose()
Write-Output $lang
"""
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True, timeout=60)
    lang = (out.stdout or "").strip().splitlines()[-1] if out.stdout else ""
    if lang not in ("es", "en") or not os.path.exists(path):
        raise RuntimeError(f"TTS local fallo: rc={out.returncode} out={out.stdout[-200:]} err={out.stderr[-200:]}")
    raw = open(path, "rb").read()
    kw = ["almuerzo", "taxi", "cinco"] if lang == "es" else ["lunch", "taxi", "five"]
    print(f"  (TTS {lang}, WAV {len(raw)} bytes)")
    return base64.b64encode(raw).decode(), kw


def main():
    print("=== QA Zepi dictado (mode=stt, edge + Vertex reales) ===")
    results = []

    def check(name, cond, extra=""):
        results.append((name, bool(cond)))
        print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))

    audio_b64, keywords = make_tts_wav()

    jwt_free = login("free@zepo.test")
    st, j = call_stt(jwt_free, audio_b64)
    check("1. free -> 403 (probadita pro+ solamente)", st == 403, f"st={st} j={j}")

    jwt_max = login("max@zepo.test")
    st, j = call_stt(jwt_max, "")
    check("2. max sin audio -> 400 empty_input", st == 400 and j.get("error") == "empty_input", f"st={st} j={j}")

    st, j = call_stt(jwt_max, "A" * 2_900_000)
    check("3. max audio gigante -> 400 audio_too_long", st == 400 and j.get("error") == "audio_too_long", f"st={st} j={j}")

    st, j = call_stt(jwt_max, audio_b64)
    text = str(j.get("text") or "").lower()
    check("4. max WAV con voz -> 200 y transcripcion con la frase",
          st == 200 and any(k in text for k in keywords), f"st={st} text={text[:120]!r}")

    jwt_pro = login("pro@zepo.test")
    st, j = call_stt(jwt_pro, audio_b64)
    text_p = str(j.get("text") or "").lower()
    check("5. pro WAV con voz -> 200 (dictado no es Max-only)",
          st == 200 and any(k in text_p for k in keywords), f"st={st} text={text_p[:120]!r}")

    passed = sum(1 for _, ok in results if ok)
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
