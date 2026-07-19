-- F4 Zepi memoria de largo plazo: 1 fila por usuario. El edge zepo-companion la lee y
-- escribe CON EL JWT DEL USUARIO (rol authenticated + RLS = solo su fila); el cliente
-- solo la borra (boton "Borrar memoria de Zepi" en Ajustes).

CREATE TABLE IF NOT EXISTS public.zepi_memory (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  facts jsonb NOT NULL DEFAULT '{}'::jsonb,
  summary text NOT NULL DEFAULT '' CHECK (char_length(summary) <= 4000),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.zepi_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY zepi_memory_own ON public.zepi_memory
  FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.zepi_memory TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.zepi_memory TO service_role;
REVOKE ALL ON public.zepi_memory FROM anon;
