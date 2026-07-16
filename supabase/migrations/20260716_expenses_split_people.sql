-- Split multi-persona: persistir el % REAL de cada colaborador en el gasto.
--
-- BUG que arregla (reportado en prod, jul-2026): al guardar un split la app solo
-- guardaba split_pct (TU %) y split_persona (nombres CSV). El % de cada colaborador
-- se perdia, y "Cuentas" lo reconstruia en PARTES IGUALES ((100-tuPct)/n) → un
-- ingreso dividido 40/35/25 se mostraba 40/30/30.
--
-- Formato IDENTICO al de recurring_templates.split_people (20260613_recurring_split.sql):
--   [{name, pct, user_id}]  -- solo las OTRAS personas; tu % sigue en split_pct.
-- Asi el cron y el cliente comparten shape sin conversion.
--
-- RLS/GRANT: la columna hereda las policies y grants de public.expenses (tabla que ya
-- tiene RLS habilitado y GRANT a authenticated). No requiere cambios de permisos.
--
-- Sin backfill: los splits historicos se renderizan leyendo el monto real de
-- payment_requests (origin_expense_id), que SI guardo la proporcion correcta.

ALTER TABLE public.expenses ADD COLUMN IF NOT EXISTS split_people jsonb;

-- ---------------------------------------------------------------------------
-- Cron mensual de recurrentes: el gasto generado tambien persiste split_people
-- (antes solo lo tenia la plantilla → el gasto del mes N nacia sin desglose y
-- se editaba/renderizaba igualado). Ademas liga cada cobro a su gasto origen
-- (origin_expense_id), igual que hace saveExpense en el cliente: sin eso, borrar
-- un gasto recurrente dividido no retiraba el cobro de la otra persona.
-- Copia de 20260613_recurring_split.sql con esos 2 cambios.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.zepo_generate_recurring_expenses()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  t          RECORD;
  v_today    date := (now() AT TIME ZONE 'America/Guayaquil')::date;
  v_lastday  int  := EXTRACT(DAY FROM (date_trunc('month', (now() AT TIME ZONE 'America/Guayaquil')::date) + interval '1 month - 1 day'))::int;
  v_eff      int;
  v_mypart   numeric;
  v_pending  numeric;
  person     jsonb;
  v_peramt   numeric;
  v_expid    uuid;
BEGIN
  FOR t IN SELECT * FROM public.recurring_templates WHERE active = true LOOP
    -- Día efectivo: si pide 31 y el mes tiene 30, cae el último día del mes.
    v_eff := LEAST(t.day_of_month, v_lastday);
    IF EXTRACT(DAY FROM v_today)::int = v_eff
       AND (t.last_generated IS NULL OR t.last_generated < date_trunc('month', v_today)::date)
    THEN
      IF COALESCE(t.is_split, false) THEN
        -- Gasto dividido: registra solo MI parte; el resto queda pendiente (cobros abajo).
        v_mypart  := round(t.amount * COALESCE(t.split_pct, 100) / 100.0, 2);
        v_pending := round(t.amount - v_mypart, 2);
        INSERT INTO public.expenses
          (user_id, amount, category, description, payment_method, is_income, date, is_recurring,
           is_split, split_total, split_pct, split_persona, split_people, split_pending, split_status, space_id)
        VALUES
          (t.user_id, v_mypart, t.category, t.description, t.payment_method, t.is_income, v_today, false,
           true, t.amount, t.split_pct, t.split_persona, t.split_people, v_pending, 'pendiente', t.space_id)
        RETURNING id INTO v_expid;
        -- Un cobro por cada persona con user_id (amigo), con SU porcentaje.
        IF t.split_people IS NOT NULL THEN
          FOR person IN SELECT * FROM jsonb_array_elements(t.split_people) LOOP
            IF NULLIF(person->>'user_id', '') IS NOT NULL THEN
              v_peramt := round(t.amount * COALESCE((person->>'pct')::numeric, 0) / 100.0, 2);
              IF v_peramt > 0 THEN
                INSERT INTO public.payment_requests
                  (from_user_id, to_user_id, amount, description, category, expense_date, status, origin_expense_id)
                VALUES
                  (t.user_id, (person->>'user_id')::uuid, v_peramt,
                   COALESCE(NULLIF(t.description, ''), 'Gasto compartido'), t.category, v_today, 'pending', v_expid);
              END IF;
            END IF;
          END LOOP;
        END IF;
      ELSE
        -- Recurrente plano (sin cambios respecto a 20260608_spaces.sql).
        INSERT INTO public.expenses
          (user_id, amount, category, description, payment_method, is_income, date, is_recurring, space_id)
        VALUES
          (t.user_id, t.amount, t.category, t.description, t.payment_method, t.is_income, v_today, false, t.space_id);
      END IF;
      UPDATE public.recurring_templates SET last_generated = v_today WHERE id = t.id;
    END IF;
  END LOOP;
END;
$function$;

-- ---------------------------------------------------------------------------
-- cancel_split_cobro: al revertir el gasto origen a 100% debe limpiar tambien
-- split_people (si no, queda desglose residual de un gasto que ya no es split).
-- Copia de 20260706_cobro_review.sql con esa linea.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.cancel_split_cobro(p_cobro_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
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
           split_people  = NULL,
           split_pending = NULL,
           split_status  = NULL
     WHERE id = v_origin
       AND user_id = v_uid;
  END IF;

  RETURN true;
END;
$function$;
