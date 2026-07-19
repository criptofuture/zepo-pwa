-- F5 probadita Pro/Elite: cupo mensual de mensajes con Zepi. SERVER-ONLY: solo lo
-- escribe el edge con service_role -- el usuario NO puede leer ni inflar su propio cupo
-- (el numero le llega en la respuesta del edge). Free sigue en 403; Max no cuenta.

CREATE TABLE IF NOT EXISTS public.zepi_usage (
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  month text NOT NULL CHECK (month ~ '^\d{4}-\d{2}$'),
  msgs integer NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, month)
);

ALTER TABLE public.zepi_usage ENABLE ROW LEVEL SECURITY;
-- Server-only: sin policies (nadie pasa RLS desde el browser) y sin grants a anon/authenticated.
REVOKE ALL ON public.zepi_usage FROM anon;
REVOKE ALL ON public.zepi_usage FROM authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.zepi_usage TO service_role;
