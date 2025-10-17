-- V5b: UPSERT for get_or_create_monster to avoid unique violations on (kind,spec)
BEGIN;

CREATE OR REPLACE FUNCTION get_or_create_monster(monster_kind TEXT, monster_spec TEXT DEFAULT NULL)
RETURNS INTEGER AS $$
DECLARE
  v_monster_id INTEGER;
BEGIN
  SELECT m.monster_id INTO v_monster_id
  FROM monster_catalog m
  WHERE m.kind = monster_kind 
    AND COALESCE(m.spec, '') = COALESCE(monster_spec, '');

  IF v_monster_id IS NULL THEN
    INSERT INTO monster_catalog (kind, spec, slug)
    VALUES (
      monster_kind,
      monster_spec,
      LOWER(monster_kind || CASE WHEN monster_spec IS NOT NULL THEN '|' || monster_spec ELSE '' END)
    )
    ON CONFLICT ON CONSTRAINT monster_catalog_uq_kind_spec
    DO UPDATE SET slug = EXCLUDED.slug
    RETURNING monster_id INTO v_monster_id;
  END IF;

  RETURN v_monster_id;
END;
$$ LANGUAGE plpgsql;

COMMIT;












