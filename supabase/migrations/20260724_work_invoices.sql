-- Zepo Trabajo (F1) · El otro lado del dinero: lo que te deben.
-- Distinto de payment_requests (cobros entre USUARIOS de Zepo): aqui la contraparte es un
-- cliente externo que NO tiene cuenta -> se guarda como contacto libre del propio usuario.
-- items va en JSONB (no se consulta por item, solo se muestra) -> una tabla menos que mantener.
-- RLS owner-only + default-deny: GRANT explicito a authenticated, REVOKE a anon (tools/lint-rls.py).

-- ── clientes (contrapartes externas) ─────────────────────────────
CREATE TABLE IF NOT EXISTS public.work_clients (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  name       text NOT NULL CHECK (length(trim(name)) > 0 AND length(name) <= 120),
  whatsapp   text CHECK (whatsapp IS NULL OR length(whatsapp) <= 32),
  email      text CHECK (email IS NULL OR length(email) <= 160),
  archived   boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS work_clients_user ON public.work_clients(user_id, archived);
ALTER TABLE public.work_clients ENABLE ROW LEVEL SECURITY;
CREATE POLICY wc_select_own ON public.work_clients FOR SELECT USING (user_id = auth.uid());
CREATE POLICY wc_insert_own ON public.work_clients FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY wc_update_own ON public.work_clients FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY wc_delete_own ON public.work_clients FOR DELETE USING (user_id = auth.uid());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.work_clients TO authenticated;
GRANT ALL ON public.work_clients TO service_role;
REVOKE ALL ON public.work_clients FROM anon;

-- ── proformas / cobros ───────────────────────────────────────────
-- client_name esta desnormalizado a proposito: si se borra el cliente, la proforma
-- (que ya puede tener un ingreso ligado) sigue siendo legible.
CREATE TABLE IF NOT EXISTS public.work_invoices (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  client_id   uuid REFERENCES public.work_clients(id) ON DELETE SET NULL,
  client_name text NOT NULL CHECK (length(trim(client_name)) > 0 AND length(client_name) <= 120),
  space_id    uuid REFERENCES public.spaces(id) ON DELETE SET NULL,
  number      text CHECK (number IS NULL OR length(number) <= 24),
  concept     text NOT NULL CHECK (length(trim(concept)) > 0 AND length(concept) <= 240),
  items       jsonb NOT NULL DEFAULT '[]'::jsonb,
  amount      numeric(12,2) NOT NULL CHECK (amount > 0 AND amount <= 9999999),
  tax_pct     numeric(5,2) NOT NULL DEFAULT 0 CHECK (tax_pct >= 0 AND tax_pct <= 100),
  currency    text NOT NULL DEFAULT 'USD' CHECK (length(currency) = 3),
  issue_date  date NOT NULL DEFAULT CURRENT_DATE,
  due_date    date,
  status      text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','sent','paid','void')),
  paid_at     timestamptz,
  proof_path  text,                                            -- comprobante en Storage (F3)
  income_expense_id uuid REFERENCES public.expenses(id) ON DELETE SET NULL,  -- ingreso ligado (F2)
  last_nudge_at timestamptz,                                   -- anti-spam del recordatorio (F5)
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS work_invoices_user_status ON public.work_invoices(user_id, status, due_date);
CREATE INDEX IF NOT EXISTS work_invoices_client ON public.work_invoices(client_id);
ALTER TABLE public.work_invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY wi_select_own ON public.work_invoices FOR SELECT USING (user_id = auth.uid());
CREATE POLICY wi_insert_own ON public.work_invoices FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY wi_update_own ON public.work_invoices FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY wi_delete_own ON public.work_invoices FOR DELETE USING (user_id = auth.uid());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.work_invoices TO authenticated;
GRANT ALL ON public.work_invoices TO service_role;
REVOKE ALL ON public.work_invoices FROM anon;

-- ── comprobantes (F3): bucket privado, una carpeta por usuario ───
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('comprobantes', 'comprobantes', false, 5242880,
        ARRAY['image/jpeg','image/png','image/webp','application/pdf'])
ON CONFLICT (id) DO NOTHING;

-- El path SIEMPRE empieza con el uid: '<uid>/<invoice_id>.jpg'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_policies
                 WHERE schemaname = 'storage' AND tablename = 'objects'
                   AND policyname = 'comprobantes_own') THEN
    CREATE POLICY comprobantes_own ON storage.objects FOR ALL TO authenticated
      USING (bucket_id = 'comprobantes' AND (storage.foldername(name))[1] = auth.uid()::text)
      WITH CHECK (bucket_id = 'comprobantes' AND (storage.foldername(name))[1] = auth.uid()::text);
  END IF;
END $$;
