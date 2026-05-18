-- Zepo — Notificaciones: push subscriptions + user settings
-- Ejecutar en: Supabase Dashboard → SQL Editor

-- ── push_subscriptions ──────────────────────────────────────────
-- Guarda el endpoint Web Push de cada usuario (1 por dispositivo)
CREATE TABLE IF NOT EXISTS public.push_subscriptions (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  endpoint     TEXT        NOT NULL,
  p256dh       TEXT        NOT NULL,
  auth_key     TEXT        NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, endpoint)
);

ALTER TABLE public.push_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "push_subs_own" ON public.push_subscriptions
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- ── user_settings ────────────────────────────────────────────────
-- Preferencias de notificación por usuario (sincronizadas con la app)
CREATE TABLE IF NOT EXISTS public.user_settings (
  user_id            UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  notif_daily        BOOLEAN     NOT NULL DEFAULT false,
  notif_weekly       BOOLEAN     NOT NULL DEFAULT false,
  notif_budget       BOOLEAN     NOT NULL DEFAULT true,
  reminder_time      TEXT        NOT NULL DEFAULT '21:00',  -- HH:MM en hora local del usuario
  weekly_day         INTEGER     NOT NULL DEFAULT 1          -- 0=dom…6=sáb
    CHECK (weekly_day BETWEEN 0 AND 6),
  weekly_time        TEXT        NOT NULL DEFAULT '09:00',
  budget_thresholds  INTEGER[]   NOT NULL DEFAULT '{50,75,90}',
  timezone_offset    INTEGER     NOT NULL DEFAULT -5,        -- UTC offset (Ecuador = -5)
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_settings_own" ON public.user_settings
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- Trigger: actualiza updated_at en cada UPDATE
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER user_settings_updated_at
  BEFORE UPDATE ON public.user_settings
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
