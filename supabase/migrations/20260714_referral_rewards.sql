-- ============================================================
-- ZEPO — Recompensa de referidos (F4). 2026-07-14.
-- El vínculo referrer↔referred ya existe (20260529000001_referrals.sql);
-- esto añade el PREMIO: cuando el referido se ACTIVA (≥5 registros),
-- AMBOS ganan 30 días de Pro (trial encadenado, nunca degrada).
-- Idempotente.
-- ============================================================

-- Helper interno: otorga/encadena un trial a un usuario. NO expuesto a clientes.
CREATE OR REPLACE FUNCTION public.zepo_grant_trial(p_user UUID, p_plan TEXT, p_days INT)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE v_now TIMESTAMPTZ := NOW();
BEGIN
  UPDATE public.users u SET
    trial_plan = CASE WHEN u.trial_until > v_now AND
        (CASE u.trial_plan WHEN 'max' THEN 3 WHEN 'elite' THEN 2 WHEN 'pro' THEN 1 ELSE 0 END) >
        (CASE p_plan       WHEN 'max' THEN 3 WHEN 'elite' THEN 2 WHEN 'pro' THEN 1 ELSE 0 END)
      THEN u.trial_plan ELSE p_plan END,
    trial_until = GREATEST(COALESCE(u.trial_until, v_now), v_now) + (p_days || ' days')::INTERVAL
    WHERE u.id = p_user;
END $$;
REVOKE ALL ON FUNCTION public.zepo_grant_trial(UUID, TEXT, INT) FROM public;
REVOKE ALL ON FUNCTION public.zepo_grant_trial(UUID, TEXT, INT) FROM anon, authenticated;

-- RPC: el REFERIDO (o su cliente, al abrir la app) pide verificar su activación.
-- Server-side: exige fila 'pending' + ≥5 registros REALES. 1 sola vez (status).
CREATE OR REPLACE FUNCTION public.zepo_referral_check_activation()
RETURNS JSONB
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  v_me UUID := auth.uid();
  v_r  public.referrals%ROWTYPE;
BEGIN
  IF v_me IS NULL THEN RETURN jsonb_build_object('ok', FALSE, 'error', 'no_auth'); END IF;
  SELECT * INTO v_r FROM public.referrals WHERE referred_id = v_me AND status = 'pending';
  IF NOT FOUND THEN RETURN jsonb_build_object('ok', FALSE, 'error', 'no_pending'); END IF;
  IF (SELECT COUNT(*) FROM public.expenses WHERE user_id = v_me) < 5 THEN
    RETURN jsonb_build_object('ok', FALSE, 'error', 'not_active_yet');
  END IF;

  UPDATE public.referrals SET
    status = 'qualified', qualified_at = NOW(),
    referred_bonus_days = 30, referrer_credit_months = 1
    WHERE id = v_r.id;

  PERFORM public.zepo_grant_trial(v_me, 'pro', 30);
  PERFORM public.zepo_grant_trial(v_r.referrer_id, 'pro', 30);

  RETURN jsonb_build_object('ok', TRUE, 'reward', 'pro_30d_both');
END $$;

REVOKE ALL ON FUNCTION public.zepo_referral_check_activation() FROM public;
GRANT EXECUTE ON FUNCTION public.zepo_referral_check_activation() TO authenticated;
