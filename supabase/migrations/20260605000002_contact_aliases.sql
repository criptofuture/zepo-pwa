-- contact_aliases: apodo PRIVADO que cada usuario le pone a un contacto suyo.
-- Solo lo ve y edita el dueno (owner_id). Precedencia al mostrar: alias > profiles.display_name > fallback.

CREATE TABLE IF NOT EXISTS public.contact_aliases (
  id          BIGSERIAL PRIMARY KEY,
  owner_id    UUID NOT NULL,
  contact_id  UUID NOT NULL,
  alias       TEXT NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (owner_id, contact_id)
);

ALTER TABLE public.contact_aliases ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS contact_aliases_own ON public.contact_aliases;
CREATE POLICY contact_aliases_own ON public.contact_aliases
  FOR ALL TO authenticated
  USING (owner_id = auth.uid())
  WITH CHECK (owner_id = auth.uid());

GRANT SELECT, INSERT, UPDATE, DELETE ON public.contact_aliases TO authenticated;
GRANT USAGE ON SEQUENCE public.contact_aliases_id_seq TO authenticated;
-- service_role explicito (no recibe grants automaticos en tablas nuevas).
GRANT SELECT, INSERT, UPDATE, DELETE ON public.contact_aliases TO service_role;
GRANT USAGE ON SEQUENCE public.contact_aliases_id_seq TO service_role;
REVOKE ALL ON public.contact_aliases FROM anon;
