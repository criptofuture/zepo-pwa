-- Retirar un gasto dividido: al borrar el gasto origen, cancela el/los cobro(s)
-- ligado(s) y borra el gasto espejo en la cuenta de la otra persona.
--
-- Por que una funcion SECURITY DEFINER: RLS impide que el remitente toque una fila
-- de expenses de otro usuario. Esta funcion corre como owner (bypassa RLS) pero
-- AUTORIZA explicitamente: solo el remitente del cobro (from_user_id = auth.uid())
-- puede retirar, y solo cobros aun no saldados (status pending/accepted).

CREATE OR REPLACE FUNCTION public.retract_split_expense(p_expense_id uuid)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_uid   uuid := auth.uid();
  v_count integer := 0;
  r       record;
BEGIN
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'not authenticated';
  END IF;

  FOR r IN
    SELECT id, receiver_expense_id
    FROM public.payment_requests
    WHERE origin_expense_id = p_expense_id
      AND from_user_id = v_uid            -- solo el remitente puede retirar lo suyo
      AND status IN ('pending', 'accepted') -- nunca tocar saldados/pagados/rechazados
  LOOP
    -- borra el gasto espejo del receptor (bypassa RLS via definer)
    IF r.receiver_expense_id IS NOT NULL THEN
      DELETE FROM public.expenses WHERE id = r.receiver_expense_id;
    END IF;
    UPDATE public.payment_requests SET status = 'cancelled' WHERE id = r.id;
    v_count := v_count + 1;
  END LOOP;

  RETURN v_count;
END;
$$;

REVOKE ALL   ON FUNCTION public.retract_split_expense(uuid) FROM public, anon;
GRANT EXECUTE ON FUNCTION public.retract_split_expense(uuid) TO authenticated;
