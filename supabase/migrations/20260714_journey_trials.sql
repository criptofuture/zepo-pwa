-- ============================================================
-- ZEPO — Trials del Journey (F2). 2026-07-14.
-- Recompensas: ch1→Pro 7d · ch2→Elite 7d · ch3→Max 7d ·
-- ch4→50% dto 1er mes · final→1 MES de Max (decisión Alvaro).
-- El trial vive en users.trial_plan/trial_until y NO toca users.plan
-- (el cron de renovaciones ni el checkout se enteran; expira solo).
-- Idempotente.
-- ============================================================

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS trial_plan  TEXT CHECK (trial_plan IN ('pro','elite','max')),
  ADD COLUMN IF NOT EXISTS trial_until TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS journey_discount BOOLEAN NOT NULL DEFAULT FALSE;

-- Rango efectivo del plan (server-side): max(plan pagado, trial vigente).
-- Reemplaza al helper de 20260609_max_plan_rls.sql — mismas policies lo usan.
CREATE OR REPLACE FUNCTION public.zepo_plan_rank()
RETURNS INT
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT COALESCE((
    SELECT GREATEST(
      CASE u.plan WHEN 'max' THEN 3 WHEN 'elite' THEN 2 WHEN 'pro' THEN 1 ELSE 0 END,
      CASE WHEN u.trial_until > NOW() THEN
        CASE u.trial_plan WHEN 'max' THEN 3 WHEN 'elite' THEN 2 WHEN 'pro' THEN 1 ELSE 0 END
      ELSE 0 END)
    FROM public.users u WHERE u.id = auth.uid()
  ), 0);
$$;
REVOKE ALL ON FUNCTION public.zepo_plan_rank() FROM public;
GRANT EXECUTE ON FUNCTION public.zepo_plan_rank() TO authenticated, anon, service_role;

-- RPC de reclamo de premios. SECURITY DEFINER: valida misiones + actividad
-- REAL en la BD (anti-spoof) y otorga el trial/descuento. 1 vez por capítulo.
CREATE OR REPLACE FUNCTION public.zepo_claim_journey_reward(p_chapter TEXT)
RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  v_me   UUID := auth.uid();
  v_j    public.zepo_journey%ROWTYPE;
  v_req  TEXT[];
  v_missing INT;
  v_trial TEXT;
  v_now  TIMESTAMPTZ := NOW();
  v_res  JSONB;
BEGIN
  IF v_me IS NULL THEN RETURN jsonb_build_object('ok', FALSE, 'error', 'no_auth'); END IF;
  SELECT * INTO v_j FROM public.zepo_journey WHERE user_id = v_me;
  IF NOT FOUND THEN RETURN jsonb_build_object('ok', FALSE, 'error', 'no_journey'); END IF;
  IF v_j.rewards ? p_chapter THEN RETURN jsonb_build_object('ok', FALSE, 'error', 'already_claimed'); END IF;

  -- Espejo server-side del catálogo de misiones del front (JRN_CHAPTERS).
  v_req := CASE p_chapter
    WHEN 'ch1'   THEN ARRAY['exp_first','inc_first','cat_assign','pm_add','streak_3']
    WHEN 'ch2'   THEN ARRAY['ai_text','ai_voice','cat_custom','budget_set','exp_edit','multi_item']
    WHEN 'ch3'   THEN ARRAY['ocr_photo','recurring_set','budget_cat','dash_visit','export_data']
    WHEN 'ch4'   THEN ARRAY['friend_add','split_save','pr_send','pr_accept','pr_paid','zepi_chat']
    WHEN 'final' THEN ARRAY['streak_7','streak_14','month_review','budget_kept']
    ELSE NULL END;
  IF v_req IS NULL THEN RETURN jsonb_build_object('ok', FALSE, 'error', 'bad_chapter'); END IF;

  SELECT COUNT(*) INTO v_missing FROM unnest(v_req) m WHERE NOT (v_j.missions ? m);
  IF v_missing > 0 THEN
    RETURN jsonb_build_object('ok', FALSE, 'error', 'missions_incomplete', 'missing', v_missing);
  END IF;

  -- Verificación de actividad REAL (las misiones jsonb las escribe el cliente):
  IF p_chapter = 'ch1' AND (SELECT COUNT(*) FROM public.expenses WHERE user_id = v_me) < 3 THEN
    RETURN jsonb_build_object('ok', FALSE, 'error', 'not_enough_activity');
  END IF;
  IF p_chapter = 'ch2' AND NOT EXISTS (SELECT 1 FROM public.budgets WHERE user_id = v_me) THEN
    RETURN jsonb_build_object('ok', FALSE, 'error', 'not_enough_activity');
  END IF;
  IF p_chapter = 'ch4' AND NOT EXISTS (SELECT 1 FROM public.payment_requests WHERE from_user_id = v_me OR to_user_id = v_me) THEN
    RETURN jsonb_build_object('ok', FALSE, 'error', 'not_enough_activity');
  END IF;
  IF p_chapter = 'final' THEN
    IF NOT (v_j.rewards ?& ARRAY['ch1','ch2','ch3','ch4']) THEN
      RETURN jsonb_build_object('ok', FALSE, 'error', 'chapters_incomplete');
    END IF;
    IF (SELECT COUNT(*) FROM public.expenses WHERE user_id = v_me) < 20 THEN
      RETURN jsonb_build_object('ok', FALSE, 'error', 'not_enough_activity');
    END IF;
  END IF;

  -- Otorgar el premio.
  IF p_chapter = 'final' THEN
    -- 1 MES DE MAX: si ya es Max PAGADO vigente → +30 días de plan;
    -- si no → trial Max 30 días (encadena sobre trial vigente).
    IF (SELECT plan FROM public.users WHERE id = v_me) = 'max'
       AND (SELECT plan_expires_at FROM public.users WHERE id = v_me) > v_now THEN
      UPDATE public.users SET plan_expires_at = plan_expires_at + INTERVAL '30 days' WHERE id = v_me;
      v_res := jsonb_build_object('ok', TRUE, 'reward', 'max_extended_30d');
    ELSE
      UPDATE public.users SET
        trial_plan  = 'max',
        trial_until = GREATEST(COALESCE(trial_until, v_now), v_now) + INTERVAL '30 days'
        WHERE id = v_me;
      v_res := jsonb_build_object('ok', TRUE, 'reward', 'max_trial_30d');
    END IF;
  ELSIF p_chapter = 'ch4' THEN
    UPDATE public.users SET journey_discount = TRUE WHERE id = v_me;
    v_res := jsonb_build_object('ok', TRUE, 'reward', 'discount_50_first_month');
  ELSE
    v_trial := CASE p_chapter WHEN 'ch1' THEN 'pro' WHEN 'ch2' THEN 'elite' WHEN 'ch3' THEN 'max' END;
    -- Encadena: el tiempo restante del trial anterior se suma; el plan del
    -- trial solo puede SUBIR (nunca degrada un trial mayor vigente).
    UPDATE public.users u SET
      trial_plan = CASE WHEN u.trial_until > v_now AND
          (CASE u.trial_plan WHEN 'max' THEN 3 WHEN 'elite' THEN 2 WHEN 'pro' THEN 1 ELSE 0 END) >
          (CASE v_trial      WHEN 'max' THEN 3 WHEN 'elite' THEN 2 WHEN 'pro' THEN 1 ELSE 0 END)
        THEN u.trial_plan ELSE v_trial END,
      trial_until = GREATEST(COALESCE(u.trial_until, v_now), v_now) + INTERVAL '7 days'
      WHERE u.id = v_me;
    v_res := jsonb_build_object('ok', TRUE, 'reward', v_trial || '_trial_7d');
  END IF;

  -- Sella el reclamo (el guard exige la bandera transaction-local).
  PERFORM set_config('zepo.allow_rewards', '1', TRUE);
  UPDATE public.zepo_journey
    SET rewards = rewards || jsonb_build_object(p_chapter, v_now)
    WHERE user_id = v_me;
  PERFORM set_config('zepo.allow_rewards', '0', TRUE);

  RETURN v_res;
END $$;

REVOKE ALL ON FUNCTION public.zepo_claim_journey_reward(TEXT) FROM public;
GRANT EXECUTE ON FUNCTION public.zepo_claim_journey_reward(TEXT) TO authenticated;
