-- 1. Domain lookup tables (referenced by evento, never edited by app code at runtime)
CREATE TABLE tipo_evento (tipo TEXT PRIMARY KEY);
INSERT INTO tipo_evento (tipo) VALUES
    ('piquete_criado'), ('piquete_alterado'),
    ('lote_criado'), ('lote_alterado'), ('lote_dissolvido'),
    ('manejo_recomendado'), ('manejo_confirmado'), ('manejo_recusado'), ('manejo_divergente'),
    ('leitura_satelite'), ('foto_validacao'), ('parametro_alterado');

CREATE TABLE origem_evento (origem TEXT PRIMARY KEY);
INSERT INTO origem_evento (origem) VALUES
    ('produtor'), ('sistema'), ('satelite'), ('sar_inferido');

-- 2. fazenda (minimal — full shape is a different spec; only what evento's FK needs)
CREATE TABLE IF NOT EXISTS fazenda (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid()
);

-- 3. evento (append-only)
CREATE TABLE evento (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fazenda_id         UUID NOT NULL REFERENCES fazenda(id),
    sequencia          BIGINT GENERATED ALWAYS AS IDENTITY,
    tipo               TEXT NOT NULL REFERENCES tipo_evento(tipo),
    origem             TEXT NOT NULL REFERENCES origem_evento(origem),
    ocorrido_em        TIMESTAMPTZ NOT NULL,
    registrado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ator               TEXT,
    corrige_evento_id  UUID REFERENCES evento(id),
    chave_idempotencia TEXT,
    versao_payload     SMALLINT NOT NULL DEFAULT 1,
    payload            JSONB NOT NULL,
    entidade_id        UUID GENERATED ALWAYS AS ((payload->>'entidade_id')::uuid) STORED,
    UNIQUE (fazenda_id, chave_idempotencia)
);

CREATE INDEX ON evento (fazenda_id, ocorrido_em, sequencia);
CREATE INDEX ON evento (fazenda_id, entidade_id);
CREATE INDEX ON evento (fazenda_id, tipo, ocorrido_em);

REVOKE UPDATE, DELETE ON evento FROM PUBLIC;

CREATE OR REPLACE FUNCTION impedir_alteracao_evento()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'A tabela evento e estritamente append-only. Operacoes de UPDATE ou DELETE sao proibidas.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_impedir_alteracao_evento
BEFORE UPDATE OR DELETE ON evento
FOR EACH ROW
EXECUTE FUNCTION impedir_alteracao_evento();

-- 4. Derived tables (all carry derivado_ate_sequencia BIGINT NOT NULL and
--    derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(); no other table writes to these):
CREATE TABLE estado_piquete (
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    piquete_id UUID NOT NULL,
    situacao TEXT NOT NULL,
    lote_atual_id UUID,
    desde DATE NOT NULL,
    dias_descanso INTEGER NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, piquete_id)
);

CREATE TABLE estado_lote (
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    lote_id UUID NOT NULL,
    piquete_atual_id UUID,
    desde DATE,
    peso_vivo_total_kg DOUBLE PRECISION NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, lote_id)
);

CREATE TABLE leitura (
    id UUID NOT NULL,
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    piquete_id UUID NOT NULL,
    data DATE NOT NULL,
    ndvi DOUBLE PRECISION NOT NULL,
    origem TEXT NOT NULL,
    pct_nuvem DOUBLE PRECISION NOT NULL,
    pixels_validos INTEGER NOT NULL,
    massa_kg_ms_ha DOUBLE PRECISION NOT NULL,
    taxa_acumulo DOUBLE PRECISION NOT NULL,
    confianca TEXT NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, piquete_id)     -- one row per piquete: latest reading only
);
