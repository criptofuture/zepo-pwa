"""Deja 2 cobros de ejemplo de demo (emisor) a qa-to (receptor) para probar a mano el rechazo de
cobros (v203) en el celular: uno dividido con otra persona y uno dividido solo con qa-to.
Uso: python tools/qa-siembra-cobros-prueba.py          -> siembra (borra antes los de una corrida anterior)
     python tools/qa-siembra-cobros-prueba.py limpiar  -> los borra
Ojo: qa-e2e-settle.py usa las mismas cuentas y los salda; sembrar justo antes de probar.
Todo lleva la marca [PRUEBA] en la descripción."""
import sys, importlib.util
import os
spec = importlib.util.spec_from_file_location("rj", os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa-e2e-rechazo-cobro.py"))
rj = importlib.util.module_from_spec(spec); spec.loader.exec_module(rj)
MARK = "[PRUEBA]"


def limpiar():
    rj.admin("DELETE", "/rest/v1/payment_requests?description=like.*%5BPRUEBA%5D*")
    rj.admin("DELETE", "/rest/v1/expenses?description=like.*%5BPRUEBA%5D*")


limpiar()
if len(sys.argv) > 1 and sys.argv[1] == "limpiar":
    print("limpio"); sys.exit(0)
snd, rcv = rj.user_id(rj.SENDER_EMAIL, rj.SENDER_PASS), rj.user_id(rj.RECV_EMAIL, rj.RECV_PASS)
T = rj.TODAY
base = {"user_id": snd, "category": "food", "date": T, "is_income": False, "is_split": True, "split_status": "pendiente"}
st, r1 = rj.admin("POST", "/rest/v1/expenses", {**base, "amount": 12.5, "description": "Pizza del viernes " + MARK,
    "split_total": 37.5, "split_pct": 33.34, "split_pending": 25, "split_persona": "QA To, Pedro",
    "split_people": [{"name": "QA To", "pct": 33.33, "user_id": rcv}, {"name": "Pedro", "pct": 33.33, "user_id": None}]}, ret=True)
st, r2 = rj.admin("POST", "/rest/v1/expenses", {**base, "amount": 10, "description": "Cena en casa " + MARK,
    "split_total": 20, "split_pct": 50, "split_pending": 10, "split_persona": "QA To",
    "split_people": [{"name": "QA To", "pct": 50, "user_id": rcv}]}, ret=True)
p = {"from_user_id": snd, "to_user_id": rcv, "category": "food", "expense_date": T, "status": "pending"}
for amt, desc, oid in [(12.5, "Pizza del viernes " + MARK, r1[0]["id"]), (10, "Cena en casa " + MARK, r2[0]["id"])]:
    st, _ = rj.admin("POST", "/rest/v1/payment_requests", {**p, "amount": amt, "description": desc, "origin_expense_id": oid})
    print(desc, st)
