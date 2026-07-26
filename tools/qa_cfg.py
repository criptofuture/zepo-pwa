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
