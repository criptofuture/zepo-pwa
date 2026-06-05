-- FIX prod (2026-06-05): "marcar pagado" daba "Error al marcar pago" (error 23514).
-- El CHECK de payment_requests.status NO incluia 'paid', pero la app lo usa
-- (claimPayment -> status 'paid' = "esperando confirmacion"; loadPaymentRequests
-- y deboPaidWaiting filtran 'paid'). Fix aditivo: agregar 'paid' al conjunto permitido.
-- Detectado por tools/qa-e2e-payreq.py. Aplicado via Management API.
ALTER TABLE public.payment_requests DROP CONSTRAINT payment_requests_status_check;
ALTER TABLE public.payment_requests ADD CONSTRAINT payment_requests_status_check
  CHECK (status = ANY (ARRAY['pending','accepted','settled','declined','cancelled','paid']));
