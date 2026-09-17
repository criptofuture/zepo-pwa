-- Candado de public.payment_requests (16-sep-2026).
--
-- EL HUECO: pr_update_own (20260519000001_social_system.sql:69) es
--   FOR UPDATE USING (from_user_id = auth.uid() OR to_user_id = auth.uid())
-- sin WITH CHECK propio (Postgres usa el USING tambien para la fila nueva: basta con que
-- quien edita siga siendo una de las dos partes), y la tabla tenia GRANT ALL a
-- authenticated. Con solo su token, emisor y receptor podian cambiar CUALQUIER columna:
-- el receptor bajaba `amount` a 0.01 (y el emisor lo veia como deuda confirmada: cobroFor
-- y el saldo de Contactos leen pr.amount), se daba por `settled`, o cambiaba
-- `from_user_id`; el emisor le pasaba la deuda a otro `to_user_id`; y cualquiera podia
-- ligar `receiver_expense_id` a un gasto AJENO, que
-- despues cancel_split_cobro / retract_split_expense (SECURITY DEFINER) borran sin mirar
-- de quien es. Insertar tambien servia: un cobro podia nacer ya 'accepted'.
--
-- EL ARREGLO, en dos capas:
--  1) Permiso por columna: authenticated solo puede hacer UPDATE de `status` y
--     `receiver_expense_id`, que son las dos unicas que la app cambia con .update()
--     (index.html: _doAcceptPr, declinePaymentRequest, claimPayment,
--     confirmPaymentClaim, rejectPaymentClaim, _insertMirrorExpense). Lo nuevo queda
--     cerrado por defecto.
--  2) Guardia BEFORE INSERT OR UPDATE: aunque alguien vuelva a dar GRANT ALL, solo cambian
--     esas dos columnas, cada lado solo hace SUS cambios de estado, y el gasto espejo
--     tiene que ser del receptor. Las columnas de rechazo (reject_comment, reject_reply,
--     rejection_*: las escriben reject_cobro y compania) quedan tambien fuera del alcance
--     del cliente: si no, el receptor podia fingir que el emisor acepto su rechazo.
--
-- Lo que NO pasa por el guardia: las funciones SECURITY DEFINER (settle_with_friend,
-- cancel_split_cobro, retract_split_expense, request_cobro_review, la de recurrentes),
-- el service_role, y el ON DELETE SET NULL de las llaves foraneas (Postgres lo corre
-- como dueno de la tabla). Todos corren con un rol distinto de authenticated/anon.
--
-- ⚠️ SI LA APP NECESITA ESCRIBIR OTRA COSA: lo recomendado es una RPC SECURITY DEFINER
-- que autorice por auth.uid(), como reject_cobro o cancel_split_cobro. Si de verdad va con
-- .update() directo: sumar la columna al GRANT de abajo Y a la lista de la guardia; un
-- cambio de estado nuevo va en la lista del lado que corresponda.
-- Prueba: tools/qa-e2e-payreq-guard.py (sale 1 sin esta migracion y 0 con ella).

-- Todo o nada: si algo falla a la mitad, no queda aplicado a medias.
BEGIN;

-- ── 1. Permisos ──────────────────────────────────────────────────────────────
-- REVOKE de tabla quita tambien los permisos por columna, por eso va antes del GRANT.
REVOKE ALL ON public.payment_requests FROM anon;
REVOKE UPDATE ON public.payment_requests FROM authenticated;
GRANT UPDATE (status, receiver_expense_id) ON public.payment_requests TO authenticated;

-- ── 2. Guardia ───────────────────────────────────────────────────────────────
-- SECURITY INVOKER a proposito: current_user tiene que ser el rol de quien llama.
CREATE OR REPLACE FUNCTION public.payment_requests_guard()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public
AS $$
DECLARE
  v_uid  uuid := auth.uid();
  v_paso text;
BEGIN
  IF current_user NOT IN ('authenticated', 'anon') THEN
    RETURN NEW;
  END IF;
  IF v_uid IS NULL THEN
    RAISE EXCEPTION 'payment_requests: hace falta sesion' USING ERRCODE = '42501';
  END IF;

  IF TG_OP = 'INSERT' THEN
    IF NEW.status IS DISTINCT FROM 'pending'
       OR NEW.receiver_expense_id IS NOT NULL
       OR COALESCE(NEW.review_requested, false)
       OR COALESCE(to_jsonb(NEW) ->> 'reject_comment', to_jsonb(NEW) ->> 'reject_reply',
                   to_jsonb(NEW) ->> 'rejection_denied_at',
                   to_jsonb(NEW) ->> 'rejection_accepted_at') IS NOT NULL THEN
      RAISE EXCEPTION 'payment_requests: un cobro nuevo nace pendiente, sin espejo y sin revision'
        USING ERRCODE = '42501';
    END IF;
    IF NEW.origin_expense_id IS NOT NULL AND NOT EXISTS (
         SELECT 1 FROM public.expenses e
          WHERE e.id = NEW.origin_expense_id AND e.user_id = NEW.from_user_id) THEN
      RAISE EXCEPTION 'payment_requests: el gasto origen tiene que ser del emisor'
        USING ERRCODE = '42501';
    END IF;
    RETURN NEW;
  END IF;

  -- UPDATE. Por la API solo cambian `status` y `receiver_expense_id` (updated_at lo pone
  -- su propio trigger). Lista cerrada a proposito: el monto, las personas, el detalle y
  -- las columnas de revision/rechazo (review_requested, reject_comment, reject_reply,
  -- rejection_*) solo las escriben las RPC. Una columna nueva queda protegida sola.
  IF (to_jsonb(NEW) - 'status' - 'receiver_expense_id' - 'updated_at')
     IS DISTINCT FROM
     (to_jsonb(OLD) - 'status' - 'receiver_expense_id' - 'updated_at') THEN
    RAISE EXCEPTION 'payment_requests: por la API solo cambian el estado y el gasto espejo'
      USING ERRCODE = '42501';
  END IF;

  -- Cada lado solo hace sus propios cambios de estado.
  IF NEW.status IS DISTINCT FROM OLD.status THEN
    v_paso := COALESCE(OLD.status, '') || '>' || COALESCE(NEW.status, '');
    IF NOT COALESCE(
         (v_uid = OLD.to_user_id   AND v_paso IN ('pending>accepted',   -- aceptar
                                                  'pending>declined',   -- «Ignorar» de v202; v203 lo
                                                                        -- quita: sacarlo cuando v203
                                                                        -- este en produccion
                                                  'accepted>paid'))     -- «ya pague»
      OR (v_uid = OLD.from_user_id AND v_paso IN ('paid>settled',       -- confirmar el pago
                                                  'paid>accepted')),    -- «no recibido»
       false) THEN
      RAISE EXCEPTION 'payment_requests: el cambio % no esta permitido para este usuario', v_paso
        USING ERRCODE = '42501';
    END IF;
  END IF;

  -- El gasto espejo lo liga el receptor, una sola vez, y tiene que ser suyo.
  IF NEW.receiver_expense_id IS DISTINCT FROM OLD.receiver_expense_id THEN
    IF v_uid IS DISTINCT FROM OLD.to_user_id
       OR OLD.receiver_expense_id IS NOT NULL
       OR NEW.receiver_expense_id IS NULL
       OR NEW.status NOT IN ('accepted', 'paid')
       OR NOT EXISTS (SELECT 1 FROM public.expenses e
                       WHERE e.id = NEW.receiver_expense_id AND e.user_id = OLD.to_user_id) THEN
      RAISE EXCEPTION 'payment_requests: el gasto espejo tiene que ser del receptor y ligarse una vez'
        USING ERRCODE = '42501';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS payment_requests_guard ON public.payment_requests;
CREATE TRIGGER payment_requests_guard
  BEFORE INSERT OR UPDATE ON public.payment_requests
  FOR EACH ROW EXECUTE FUNCTION public.payment_requests_guard();

COMMIT;
