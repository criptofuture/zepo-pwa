-- profiles: nombre publico + color de avatar, legible ENTRE usuarios autenticados.
-- Por que existe: user_settings tiene RLS "solo tu fila" (user_id = auth.uid()), asi que
-- la app NUNCA podia leer el display_name de otra persona -> los contactos se veian como
-- los primeros 8 chars del UUID ("fb4abcae"). profiles separa lo PUBLICO (nombre + color)
-- de lo privado (preferencias en user_settings), exponiendo solo eso.

CREATE TABLE IF NOT EXISTS public.profiles (
  user_id      UUID PRIMARY KEY,
  display_name TEXT,
  avatar_color TEXT NOT NULL DEFAULT '#507D5A',
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Lectura: cualquier usuario autenticado ve nombre+color de otros (necesario para amigos/cobros).
DROP POLICY IF EXISTS profiles_read_all ON public.profiles;
CREATE POLICY profiles_read_all ON public.profiles
  FOR SELECT TO authenticated
  USING (true);

-- Escritura: solo tu propia fila.
DROP POLICY IF EXISTS profiles_insert_own ON public.profiles;
CREATE POLICY profiles_insert_own ON public.profiles
  FOR INSERT TO authenticated
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS profiles_update_own ON public.profiles;
CREATE POLICY profiles_update_own ON public.profiles
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- GRANTs explicitos (listo para default-deny). anon NO consume profiles.
GRANT SELECT, INSERT, UPDATE ON public.profiles TO authenticated;
-- service_role NO recibe grants automaticos en tablas nuevas (gotcha Zepo) -> explicito.
GRANT SELECT, INSERT, UPDATE, DELETE ON public.profiles TO service_role;
REVOKE ALL ON public.profiles FROM anon;

-- Backfill: nombre desde user_settings.display_name o, si vacio, desde users.name
-- (users.name SIEMPRE trae al menos full_name de Google o el prefijo del email -> nunca UUID).
INSERT INTO public.profiles (user_id, display_name, avatar_color)
SELECT u.id,
       COALESCE(NULLIF(us.display_name, ''), NULLIF(u.name, '')),
       COALESCE(us.avatar_color, '#507D5A')
FROM public.users u
LEFT JOIN public.user_settings us ON us.user_id = u.id
ON CONFLICT (user_id) DO NOTHING;
