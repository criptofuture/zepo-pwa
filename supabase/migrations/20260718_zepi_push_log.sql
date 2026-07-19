-- F7 Zepi proactivo: registro de 1 push maximo por usuario por dia. SERVER-ONLY
-- (solo el edge zepi-push-insight con service_role lo toca). Tambien evita re-quemar
-- llamadas al modelo el mismo dia aunque el cron corra dos veces.

CREATE TABLE IF NOT EXISTS public.zepi_push_log (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  day date NOT NULL,
  sent boolean NOT NULL DEFAULT false,
  title text NOT NULL DEFAULT '',
  PRIMARY KEY (user_id, day)
);

ALTER TABLE public.zepi_push_log ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.zepi_push_log FROM anon;
REVOKE ALL ON public.zepi_push_log FROM authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.zepi_push_log TO service_role;
