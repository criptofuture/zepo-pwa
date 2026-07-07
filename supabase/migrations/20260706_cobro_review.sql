-- Revision y cancelacion de cobros (split).
-- Flujo: el RECEPTOR de un cobro puede PEDIR REVISION (review_requested=true) aunque
-- ya lo haya aceptado. El EMISOR ve la marca y puede CANCELAR el cobro: se anula, se
-- borra el gasto espejo del receptor y el gasto origen vuelve a 100% del emisor.
--
-- Ambas funciones son SECURITY DEFINER (bypassan RLS) pero AUTORIZAN explicitamente
-- por auth.uid(): request solo el receptor (to_user_id), cancel solo el emisor (from_user_id).

ALTER TABLE public.payment_requests
  ADD COLUMN IF NOT EXISTS review_requested boolean NOT NULL DEFAULT false;

-- El RECEPTOR pide revision de un cobro dirigido a el (pendiente o aceptado).
CREATE OR REPLACE FUNCTION public.request_cobro_review(p_cobro_id bigint)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid uuid := auth.uid();
  v_n   integer;
BEGIN
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'not authenticated';
  END IF;
  UPDATE public.payment_requests
     SET review_requested = true
   WHERE id = p_cobro_id
     AND to_user_id = v_uid
     AND status IN ('pending', 'accepted');
  GET DIAGNOSTICS v_n = ROW_COUNT;
  RETURN v_n > 0;
END;
$$;

-- El EMISOR cancela el cobro (tras revision): anula, borra espejo, revierte gasto a 100%.
CREATE OR REPLACE FUNCTION public.cancel_split_cobro(p_cobro_id bigint)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid    uuid := auth.uid();
  v_origin uuid;
  v_mirror uuid;
BEGIN
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'not authenticated';
  END IF;

  SELECT origin_expense_id, receiver_expense_id
    INTO v_origin, v_mirror
    FROM public.payment_requests
   WHERE id = p_cobro_id
     AND from_user_id = v_uid               -- solo el emisor cancela lo suyo
     AND status IN ('pending', 'accepted'); -- nunca tocar saldados/pagados/cancelados
  IF NOT FOUND THEN
    RETURN false;
  END IF;

  UPDATE public.payment_requests
     SET status = 'cancelled', review_requested = false
   WHERE id = p_cobro_id;

  -- borra el gasto espejo del receptor (bypassa RLS via definer)
  IF v_mirror IS NOT NULL THEN
    DELETE FROM public.expenses WHERE id = v_mirror;
  END IF;

  -- revierte el gasto origen del emisor a 100% (deja de estar dividido)
  IF v_origin IS NOT NULL THEN
    UPDATE public.expenses
       SET amount        = COALESCE(split_total, amount),
           is_split      = false,
           split_total   = NULL,
           split_pct     = NULL,
           split_persona = NULL,
           split_pending = NULL,
           split_status  = NULL
     WHERE id = v_origin
       AND user_id = v_uid;
  END IF;

  RETURN true;
END;
$$;

REVOKE ALL    ON FUNCTION public.request_cobro_review(bigint) FROM public, anon;
REVOKE ALL    ON FUNCTION public.cancel_split_cobro(bigint)   FROM public, anon;
GRANT EXECUTE ON FUNCTION public.request_cobro_review(bigint) TO authenticated;
GRANT EXECUTE ON FUNCTION public.cancel_split_cobro(bigint)   TO authenticated;
