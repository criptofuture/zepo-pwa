-- ============================================================
-- ZEPO — Journey 30 días (F1): progreso de misiones, rachas y
-- premios por usuario. 2026-07-14.
-- missions/streak los escribe el CLIENTE (bajo riesgo);
-- rewards SOLO los escribe el RPC de reclamo (guard por trigger).
-- Idempotente: seguro de correr varias veces.
-- ============================================================

CREATE TABLE IF NOT EXISTS public.zepo_journey (
  user_id       UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
  started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  missions      JSONB NOT NULL DEFAULT '{}'::jsonb,  -- {mission_id: iso_ts}
  rewards       JSONB NOT NULL DEFAULT '{}'::jsonb,  -- {ch1..ch4,final: iso_ts} — solo RPC
  streak_days   INT NOT NULL DEFAULT 0,
  streak_best   INT NOT NULL DEFAULT 0,
  streak_last   DATE,
  streak_graces INT NOT NULL DEFAULT 0,   -- perdones usados en la racha actual (máx 1)
  backfilled    BOOLEAN NOT NULL DEFAULT FALSE,
  dismissed     BOOLEAN NOT NULL DEFAULT FALSE,  -- ocultó la tarjeta del Home
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.zepo_journey ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS jrn_select_own ON public.zepo_journey;
CREATE POLICY jrn_select_own ON public.zepo_journey
  FOR SELECT USING (user_id = auth.uid());

DROP POLICY IF EXISTS jrn_insert_own ON public.zepo_journey;
CREATE POLICY jrn_insert_own ON public.zepo_journey
  FOR INSERT WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS jrn_update_own ON public.zepo_journey;
CREATE POLICY jrn_update_own ON public.zepo_journey
  FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

GRANT SELECT, INSERT, UPDATE ON public.zepo_journey TO authenticated;
GRANT ALL ON public.zepo_journey TO service_role;  -- default-deny del proyecto: el grant NO es implícito
REVOKE ALL ON public.zepo_journey FROM anon;

-- Guard: un usuario autenticado NO puede escribir 'rewards' ni retroceder
-- 'started_at' por REST directo. El RPC de reclamo levanta la bandera
-- transaction-local 'zepo.allow_rewards' antes de su UPDATE.
-- service_role / SQL directo (sin JWT de usuario) no se bloquea.
CREATE OR REPLACE FUNCTION public.zepo_journey_guard()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
  v_role TEXT := COALESCE(NULLIF(current_setting('request.jwt.claims', TRUE), '')::jsonb->>'role', '');
  v_allow BOOLEAN := COALESCE(current_setting('zepo.allow_rewards', TRUE), '') = '1';
BEGIN
  IF v_role = 'authenticated' AND NOT v_allow THEN
    IF TG_OP = 'UPDATE' THEN
      NEW.rewards := OLD.rewards;
      NEW.started_at := OLD.started_at;
    ELSE
      NEW.rewards := '{}'::jsonb;
    END IF;
  END IF;
  IF TG_OP = 'UPDATE' THEN NEW.updated_at := NOW(); END IF;
  RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_zepo_journey_guard ON public.zepo_journey;
CREATE TRIGGER trg_zepo_journey_guard
  BEFORE INSERT OR UPDATE ON public.zepo_journey
  FOR EACH ROW EXECUTE FUNCTION public.zepo_journey_guard();
