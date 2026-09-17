-- DESHACER 20260916_payment_requests_guard.sql si rompe un paso legitimo de la app.
-- Vuelve a abrir el hueco: usarlo solo como parche de minutos mientras se corrige.
-- Aplicar: python tools/db-fixes/apply-migration.py tools/db-fixes/2026-09-16-payreq-guard-REVERT.sql
BEGIN;
DROP TRIGGER IF EXISTS payment_requests_guard ON public.payment_requests;
DROP FUNCTION IF EXISTS public.payment_requests_guard();
GRANT UPDATE ON public.payment_requests TO authenticated;
COMMIT;
