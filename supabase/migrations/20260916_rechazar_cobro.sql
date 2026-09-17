-- Rechazar un cobro con comentario, y que el emisor acepte o no el rechazo (v203).
--
-- Reemplaza el par "Ignorar" + "Pedir revision" del receptor:
--   * "Ignorar" (status='declined') escondia el cobro sin avisar al emisor, y en la app del
--     emisor ese split pasaba a contar como deuda CONFIRMADA (_sentCobroByOrigin descarta los
--     declined, y un split sin cobro activo cuenta como confirmado).
--   * "Pedir revision" era un rechazo sin comentario y el emisor solo podia cancelar.
--
-- Estados (sobre la misma fila; status sigue siendo pending/accepted mientras se discute, asi
-- las dos apps siguen contando lo mismo):
--   rechazo abierto   review_requested = true                     -> le toca al EMISOR
--   rechazo negado    review_requested = false, rejection_denied_at -> le toca al RECEPTOR
--   rechazo aceptado  status = 'cancelled', rejection_accepted_at  -> aviso al RECEPTOR
--
-- Las 4 funciones son SECURITY DEFINER (el emisor tiene que tocar el gasto espejo del
-- receptor, que RLS le bloquea) y AUTORIZAN por auth.uid() y por estado.

ALTER TABLE public.payment_requests
  ADD COLUMN IF NOT EXISTS reject_comment        text,
  ADD COLUMN IF NOT EXISTS reject_reply          text,
  ADD COLUMN IF NOT EXISTS rejection_denied_at   timestamptz,
  ADD COLUMN IF NOT EXISTS rejection_accepted_at timestamptz,
  ADD COLUMN IF NOT EXISTS rejection_notice_seen boolean NOT NULL DEFAULT false;

-- Comentario opcional: vacio = NULL, maximo 280 caracteres (el mismo tope que el textarea).
CREATE OR REPLACE FUNCTION public._cobro_comment(p_text text)
RETURNS text
LANGUAGE sql
IMMUTABLE
SET search_path = public
AS $$
  SELECT NULLIF(left(btrim(COALESCE(p_text, '')), 280), '');
$$;

-- RECEPTOR: rechaza un cobro pendiente o ya aceptado.
CREATE OR REPLACE FUNCTION public.reject_cobro(p_cobro_id bigint, p_comment text DEFAULT NULL)
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
     SET review_requested    = true,
         reject_comment      = public._cobro_comment(p_comment),
         reject_reply        = NULL,
         rejection_denied_at = NULL
   WHERE id = p_cobro_id
     AND to_user_id = v_uid
     AND status IN ('pending', 'accepted');
  GET DIAGNOSTICS v_n = ROW_COUNT;
  RETURN v_n > 0;
END;
$$;

-- RECEPTOR: retira su rechazo (cambio de opinion) justo antes de aceptar el cobro. Va por
-- RPC y no por .update() porque la app solo puede escribir status y receiver_expense_id
-- (candado 20260916_payment_requests_guard.sql).
CREATE OR REPLACE FUNCTION public.withdraw_cobro_rejection(p_cobro_id bigint)
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
     SET review_requested    = false,
         rejection_denied_at = NULL
   WHERE id = p_cobro_id
     AND to_user_id = v_uid
     AND status IN ('pending', 'accepted');
  GET DIAGNOSTICS v_n = ROW_COUNT;
  RETURN v_n > 0;
END;
$$;

-- EMISOR: no acepta el rechazo. El cobro le vuelve al receptor con la respuesta.
CREATE OR REPLACE FUNCTION public.deny_cobro_rejection(p_cobro_id bigint, p_comment text DEFAULT NULL)
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
     SET review_requested    = false,
         reject_reply        = public._cobro_comment(p_comment),
         rejection_denied_at = now()
   WHERE id = p_cobro_id
     AND from_user_id = v_uid
     AND review_requested = true
     AND status IN ('pending', 'accepted');
  GET DIAGNOSTICS v_n = ROW_COUNT;
  RETURN v_n > 0;
END;
$$;

-- EMISOR: acepta el rechazo. Anula el cobro, borra el gasto espejo del receptor y le
-- devuelve al emisor SOLO la parte de esa persona: si el gasto estaba dividido con mas
-- gente, las demas siguen igual (cancel_split_cobro revertia el gasto entero).
CREATE OR REPLACE FUNCTION public.accept_cobro_rejection(p_cobro_id bigint, p_comment text DEFAULT NULL)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid     uuid := auth.uid();
  v_pr      public.payment_requests%ROWTYPE;
  v_exp     public.expenses%ROWTYPE;
  v_rest    jsonb;
  v_gone    numeric;
  v_names   text[];
  v_all     text[];
  v_label   text;
  v_share   numeric;
BEGIN
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'not authenticated';
  END IF;

  SELECT * INTO v_pr
    FROM public.payment_requests
   WHERE id = p_cobro_id
     AND from_user_id = v_uid
     AND review_requested = true
     AND status IN ('pending', 'accepted')
   FOR UPDATE;
  IF NOT FOUND THEN
    RETURN false;
  END IF;

  UPDATE public.payment_requests
     SET status                = 'cancelled',
         review_requested      = false,
         reject_reply          = public._cobro_comment(p_comment),
         rejection_accepted_at = now(),
         rejection_notice_seen = false
   WHERE id = p_cobro_id;

  IF v_pr.receiver_expense_id IS NOT NULL THEN
    DELETE FROM public.expenses WHERE id = v_pr.receiver_expense_id AND user_id = v_pr.to_user_id;
  END IF;

  IF v_pr.origin_expense_id IS NULL THEN
    RETURN true;
  END IF;

  SELECT * INTO v_exp
    FROM public.expenses
   WHERE id = v_pr.origin_expense_id
     AND user_id = v_uid
     AND is_split = true
   FOR UPDATE;
  IF NOT FOUND THEN
    RETURN true;
  END IF;

  IF v_exp.split_people IS NOT NULL
     AND jsonb_typeof(v_exp.split_people) = 'array'
     AND EXISTS (SELECT 1 FROM jsonb_array_elements(v_exp.split_people) e
                  WHERE e->>'user_id' = v_pr.to_user_id::text) THEN
    -- Split con desglose: se saca a esta persona por user_id.
    SELECT COALESCE(jsonb_agg(e), '[]'::jsonb)
      INTO v_rest
      FROM jsonb_array_elements(v_exp.split_people) e
     WHERE COALESCE(e->>'user_id', '') <> v_pr.to_user_id::text;
    SELECT COALESCE(sum(NULLIF(e->>'pct', '')::numeric), 0)
      INTO v_gone
      FROM jsonb_array_elements(v_exp.split_people) e
     WHERE e->>'user_id' = v_pr.to_user_id::text;
    SELECT array_agg(btrim(e->>'name'))
      INTO v_names
      FROM jsonb_array_elements(v_rest) e
     WHERE COALESCE(btrim(e->>'name'), '') <> '';
  ELSE
    -- Split viejo sin desglose: nombres separados por coma. Se saca el nombre con que el
    -- emisor ve a esta persona (su apodo privado, si no el nombre del perfil).
    SELECT COALESCE(
             (SELECT alias FROM public.contact_aliases
               WHERE owner_id = v_uid AND contact_id = v_pr.to_user_id LIMIT 1),
             (SELECT display_name FROM public.profiles WHERE user_id = v_pr.to_user_id LIMIT 1))
      INTO v_label;
    SELECT array_agg(n)
      INTO v_all
      FROM (SELECT btrim(x) AS n FROM unnest(string_to_array(COALESCE(v_exp.split_persona, ''), ',')) x) s
     WHERE n <> '';
    SELECT array_agg(n)
      INTO v_names
      FROM unnest(COALESCE(v_all, '{}'::text[])) n
     WHERE lower(n) <> lower(COALESCE(v_label, ''));
    -- Una sola persona en el split: es ella aunque el apodo haya cambiado desde entonces.
    IF COALESCE(array_length(v_all, 1), 0) <= 1 THEN
      v_names := NULL;
    ELSIF COALESCE(array_length(v_names, 1), 0) = array_length(v_all, 1) THEN
      -- Varias personas y ninguna se llama como ella: no se sabe cual sacar. Mejor no tocar
      -- nada (se deshace todo, tambien el 'cancelled') que descuadrar la libreta.
      RAISE EXCEPTION 'split sin desglose: no encuentro a esta persona en "%"', v_exp.split_persona
        USING ERRCODE = 'P0002';
    END IF;
    v_rest := NULL;
    v_gone := (100 - COALESCE(v_exp.split_pct, 50)) / GREATEST(COALESCE(array_length(v_all, 1), 1), 1);
  END IF;

  IF COALESCE(array_length(v_names, 1), 0) = 0 THEN
    -- No queda nadie mas: el gasto vuelve a ser 100% del emisor (igual que cancel_split_cobro).
    UPDATE public.expenses
       SET amount        = COALESCE(split_total, amount),
           is_split      = false,
           split_total   = NULL,
           split_pct     = NULL,
           split_persona = NULL,
           split_people  = NULL,
           split_pending = NULL,
           split_status  = NULL
     WHERE id = v_exp.id;
  ELSE
    -- Quedan otras personas: el emisor absorbe solo esta parte.
    v_share := round(COALESCE(v_pr.amount, 0), 2);
    UPDATE public.expenses
       SET amount        = round(amount + v_share, 2),
           split_pending = GREATEST(round(COALESCE(split_pending, 0) - v_share, 2), 0),
           split_pct     = LEAST(round(COALESCE(split_pct, 50) + v_gone, 2), 100),
           split_people  = CASE WHEN v_rest IS NULL THEN split_people ELSE v_rest END,
           split_persona = array_to_string(v_names, ', ')
     WHERE id = v_exp.id;
  END IF;

  RETURN true;
END;
$$;

-- RECEPTOR: marca como visto el aviso de "aceptaron tu rechazo".
CREATE OR REPLACE FUNCTION public.dismiss_rejection_notice(p_cobro_id bigint)
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
     SET rejection_notice_seen = true
   WHERE id = p_cobro_id
     AND to_user_id = v_uid
     AND status = 'cancelled'
     AND rejection_accepted_at IS NOT NULL;
  GET DIAGNOSTICS v_n = ROW_COUNT;
  RETURN v_n > 0;
END;
$$;

REVOKE ALL    ON FUNCTION public._cobro_comment(text)                   FROM public, anon, authenticated;
REVOKE ALL    ON FUNCTION public.reject_cobro(bigint, text)             FROM public, anon;
REVOKE ALL    ON FUNCTION public.withdraw_cobro_rejection(bigint)       FROM public, anon;
GRANT EXECUTE ON FUNCTION public.withdraw_cobro_rejection(bigint)       TO authenticated;
REVOKE ALL    ON FUNCTION public.deny_cobro_rejection(bigint, text)     FROM public, anon;
REVOKE ALL    ON FUNCTION public.accept_cobro_rejection(bigint, text)   FROM public, anon;
REVOKE ALL    ON FUNCTION public.dismiss_rejection_notice(bigint)       FROM public, anon;
GRANT EXECUTE ON FUNCTION public.reject_cobro(bigint, text)             TO authenticated;
GRANT EXECUTE ON FUNCTION public.deny_cobro_rejection(bigint, text)     TO authenticated;
GRANT EXECUTE ON FUNCTION public.accept_cobro_rejection(bigint, text)   TO authenticated;
GRANT EXECUTE ON FUNCTION public.dismiss_rejection_notice(bigint)       TO authenticated;
