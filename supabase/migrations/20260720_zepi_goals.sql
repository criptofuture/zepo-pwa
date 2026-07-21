-- Fase 6 (#4) · Motor de metas de Zepi. Progreso COMPUTADO en el cliente (evita drift):
--   save  -> suma de lifetimeSavingsByMonth desde baseline (o expenses en memoria si no es Max)
--   limit -> gasto del mes vs target (categoria o total)
--   debt  -> unico con current_amount PERSISTIDO: el usuario actualiza el saldo restante
-- RLS owner-only (una meta es dato del propio usuario, sin entitlement -> no hace falta RPC/guard).
-- Default-deny: GRANT explicito a authenticated, REVOKE a anon (cumple tools/lint-rls.py).

CREATE TABLE IF NOT EXISTS public.zepi_goals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('save','limit','debt')),
  title text NOT NULL,
  target_amount numeric(12,2) NOT NULL CHECK (target_amount > 0 AND target_amount <= 9999999),
  category text,                                   -- solo 'limit'; null = total
  baseline_amount numeric(12,2) NOT NULL DEFAULT 0,
  current_amount numeric(12,2),                    -- solo 'debt': saldo restante
  baseline_date date NOT NULL DEFAULT CURRENT_DATE,
  deadline date,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','done','archived')),
  space_id uuid REFERENCES public.spaces(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS zepi_goals_user_active ON public.zepi_goals(user_id, status);
ALTER TABLE public.zepi_goals ENABLE ROW LEVEL SECURITY;
CREATE POLICY goals_select_own ON public.zepi_goals FOR SELECT USING (user_id = auth.uid());
CREATE POLICY goals_insert_own ON public.zepi_goals FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY goals_update_own ON public.zepi_goals FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY goals_delete_own ON public.zepi_goals FOR DELETE USING (user_id = auth.uid());
GRANT SELECT, INSERT, UPDATE, DELETE ON public.zepi_goals TO authenticated;
GRANT ALL ON public.zepi_goals TO service_role;
REVOKE ALL ON public.zepi_goals FROM anon;
