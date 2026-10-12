BEGIN;

CREATE TABLE modulo (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    nome       TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fazenda_id, nome)
);

CREATE TABLE praca (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    nome       TEXT NOT NULL CHECK (length(trim(nome)) > 0),
    ponto      geometry(Point, 4326) NOT NULL,
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (fazenda_id, nome)
);

-- piquete_id and lote_id have no foreign key on purpose: paddocks and cattle groups live in
-- the event log, and their derived rows are rebuilt by DELETE + INSERT.
CREATE TABLE piquete_estrutura (
    piquete_id UUID PRIMARY KEY,
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    modulo_id  UUID REFERENCES modulo(id) ON DELETE RESTRICT,
    praca_id   UUID REFERENCES praca(id) ON DELETE RESTRICT,
    CHECK (modulo_id IS NOT NULL OR praca_id IS NOT NULL)
);
CREATE INDEX piquete_estrutura_fazenda_idx ON piquete_estrutura (fazenda_id);

CREATE TABLE lote_modulo (
    lote_id    UUID PRIMARY KEY,
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    modulo_id  UUID NOT NULL REFERENCES modulo(id) ON DELETE RESTRICT
);
CREATE INDEX lote_modulo_fazenda_idx ON lote_modulo (fazenda_id);

ALTER TABLE modulo ENABLE ROW LEVEL SECURITY;
ALTER TABLE praca ENABLE ROW LEVEL SECURITY;
ALTER TABLE piquete_estrutura ENABLE ROW LEVEL SECURITY;
ALTER TABLE lote_modulo ENABLE ROW LEVEL SECURITY;

COMMIT;
