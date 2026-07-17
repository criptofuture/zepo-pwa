-- D17: spaces, patrimony_items y recurring_templates tenian service_role SOLO con
-- REFERENCES/TRIGGER/TRUNCATE -- sin SELECT/INSERT/UPDATE/DELETE. Cualquier script admin o Edge
-- Function con la secret_key recibia 403 EN SILENCIO contra estas 3 tablas (asi se descubrio: un
-- cleanup de QA fallo mudo y dejo 6 espacios huerfanos). expenses SI los tenia.
-- OJO regla del CLAUDE.md: "service_role bypassa" vale para RLS, NO para los GRANT -- desde el
-- default-deny hay que concederlos explicitamente (igual que ya se hizo en zepo_journey/expenses).
-- service_role es server-only (nunca en el browser) -> conceder DML completo es seguro y esperado.

GRANT SELECT, INSERT, UPDATE, DELETE ON public.spaces              TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.patrimony_items     TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.recurring_templates TO service_role;
