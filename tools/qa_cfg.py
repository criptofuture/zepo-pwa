"""Ubica config.json sin depender de donde este el checkout.

Los scripts de QA asumian config.json exactamente dos carpetas arriba del PWA. Eso
solo es cierto dentro del monorepo: en una mesa (git worktree) la ruta apunta a la
carpeta del usuario y todos fallaban con FileNotFoundError antes de correr nada.
Aqui se busca subiendo por el arbol, con ZEPO_CONFIG para forzar una ruta.
"""
import json
import os


def load(pwa_dir, section="supabase"):
    cands = []
    env = os.environ.get("ZEPO_CONFIG")
    if env:
        cands.append(env)
    d = os.path.abspath(pwa_dir)
    for _ in range(6):
        cands.append(os.path.join(d, "config.json"))
        nd = os.path.dirname(d)
        if nd == d:
            break
        d = nd
    cands.append(os.path.expanduser("~/lynoia/clients/zepo/config.json"))
    for p in cands:
        if p and os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)[section]
    raise SystemExit(
        "No encuentro config.json. Busque en:\n  " + "\n  ".join(cands)
        + "\nDefine ZEPO_CONFIG=<ruta al config.json> si esta en otro lado."
    )


SUPABASE_ENV = os.path.expanduser("~/.config/lynoia/supabase.env")


def supabase_token():
    """Token de la Management API de Supabase. NUNCA imprimirlo.

    Vive en ~/.config/lynoia/supabase.env (SUPABASE_ACCESS_TOKEN), fuera del repo. La skill
    supabase y su config.json se retiraron (16-sep-2026): quien leia esa ruta caia con
    FileNotFoundError antes de probar nada. La variable de entorno, si esta, manda.
    """
    tok = os.environ.get("SUPABASE_ACCESS_TOKEN", "").strip()
    if not tok and os.path.exists(SUPABASE_ENV):
        with open(SUPABASE_ENV, encoding="utf-8") as fh:
            for line in fh:
                k, _, v = line.strip().partition("=")
                if k.strip() == "SUPABASE_ACCESS_TOKEN" and v.strip():
                    tok = v.strip().strip('"').strip("'")
    if not tok:
        raise SystemExit("No encuentro SUPABASE_ACCESS_TOKEN en el entorno ni en " + SUPABASE_ENV)
    return tok


def mgmt(pwa_dir):
    """(token, project_ref) para la Management API. El ref sale de la url del config.json."""
    host = load(pwa_dir)["url"].split("//", 1)[-1]
    return supabase_token(), host.split(".", 1)[0]
