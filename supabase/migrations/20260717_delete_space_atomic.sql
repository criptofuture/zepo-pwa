-- D14: borrar un espacio movia gastos -> presupuestos -> recurrentes -> DELETE en una cadena de
-- 4 await SIN transaccion. Si la red se caia a mitad, quedaba un estado partido (gastos movidos
-- pero el espacio aun existe, o al reves). Esta RPC hace las 4 operaciones en UNA transaccion:
-- si algo falla, se revierte todo. SECURITY DEFINER porque mueve/borra filas del usuario saltando
-- RLS, pero autoriza explicitamente: ambos espacios deben ser de auth.uid() y no se borra el default.
--
-- Nota sobre budgets: su UNIQUE es (user_id, category, month, year) SIN space_id -> dos espacios
-- NO pueden tener el mismo presupuesto (categoria/mes) a la vez, asi que mover space_id nunca
-- viola la constraint. No hace falta manejar colision.

CREATE OR REPLACE FUNCTION public.zepo_delete_space(p_space_id uuid, p_target_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path = public
AS $function$
DECLARE
  v_uid uuid := auth.uid();
BEGIN
  IF v_uid IS NULL THEN RAISE EXCEPTION 'no auth'; END IF;
  IF p_space_id = p_target_id THEN RAISE EXCEPTION 'origen y destino son el mismo espacio'; END IF;
  IF NOT EXISTS (SELECT 1 FROM public.spaces WHERE id = p_space_id AND user_id = v_uid) THEN
    RAISE EXCEPTION 'el espacio a borrar no es tuyo';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.spaces WHERE id = p_target_id AND user_id = v_uid) THEN
    RAISE EXCEPTION 'el espacio destino no es tuyo';
  END IF;
  IF EXISTS (SELECT 1 FROM public.spaces WHERE id = p_space_id AND is_default) THEN
    RAISE EXCEPTION 'no se puede borrar el espacio por defecto';
  END IF;

  UPDATE public.expenses           SET space_id = p_target_id WHERE space_id = p_space_id AND user_id = v_uid;
  UPDATE public.budgets            SET space_id = p_target_id WHERE space_id = p_space_id AND user_id = v_uid;
  UPDATE public.recurring_templates SET space_id = p_target_id WHERE space_id = p_space_id AND user_id = v_uid;
  DELETE FROM public.spaces WHERE id = p_space_id AND user_id = v_uid;
END;
$function$;

REVOKE ALL ON FUNCTION public.zepo_delete_space(uuid, uuid) FROM anon;
GRANT EXECUTE ON FUNCTION public.zepo_delete_space(uuid, uuid) TO authenticated;
