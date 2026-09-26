-- SPEC-008: farm settings, user link, cultivar catalog, derived tables,
-- weekly plan, telegram state and row-level security. Runs after 0001.
BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE fazenda
    ADD COLUMN nome TEXT NOT NULL DEFAULT '',
    ADD COLUMN timezone TEXT NOT NULL DEFAULT 'America/Fortaleza',
    ADD COLUMN funcionarios_disponiveis INTEGER NOT NULL DEFAULT 1
        CHECK (funcionarios_disponiveis >= 1),
    ADD COLUMN manejos_por_funcionario_dia INTEGER NOT NULL DEFAULT 1
        CHECK (manejos_por_funcionario_dia >= 1),
    ADD COLUMN dias_preferenciais_manejo SMALLINT[] NOT NULL DEFAULT '{0}'
        CHECK (cardinality(dias_preferenciais_manejo) >= 1
               AND dias_preferenciais_manejo <@ '{0,1,2,3,4,5,6}'::smallint[]),
    ADD COLUMN telegram_chat_id BIGINT,
    ADD COLUMN codigo_vinculo_telegram TEXT NOT NULL
        DEFAULT substr(replace(gen_random_uuid()::text, '-', ''), 1, 16),
    ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN criado_em TIMESTAMPTZ NOT NULL DEFAULT now();
CREATE UNIQUE INDEX fazenda_codigo_vinculo_idx ON fazenda (codigo_vinculo_telegram);

CREATE TABLE fazenda_usuario (
    usuario_id UUID PRIMARY KEY,               -- Supabase Auth user id
    fazenda_id UUID NOT NULL REFERENCES fazenda(id),
    criado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cultivar (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug       TEXT NOT NULL UNIQUE,
    nome       TEXT NOT NULL,
    parametros JSONB NOT NULL
);

INSERT INTO cultivar (slug, nome, parametros) VALUES
('marandu', 'Marandu', '{
  "especie": "Brachiaria brizantha", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 30, "altura_saida_cm": 15,
     "altura_maxima_cm": null, "altura_minima_cm": null, "eficiencia_pastejo": 0.72,
     "confianca": "media", "fonte": "Andrade (2008), Embrapa Acre, via Soares et al. (2021)"},
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 35, "altura_minima_cm": 20,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": 110, "rue_max_g_por_mj": 2.31, "temperatura_base_c": 15.0,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": "alta"}'),
('mombaca', 'Mombaça', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 85, "altura_saida_cm": 45,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "media", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"},
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 75, "altura_minima_cm": 50,
     "confianca": "media", "fonte": "Kill-Silveira (2020), Rev. Vet. Zootec. 27"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": "alta"}'),
('tanzania', 'Tanzânia', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 70, "altura_saida_cm": 35,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "media", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"},
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 60, "altura_minima_cm": 40,
     "confianca": "media", "fonte": "Kill-Silveira (2020), Rev. Vet. Zootec. 27"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": 15.0,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('zuri', 'Zuri', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 80, "altura_saida_cm": 40,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('massai', 'Massai', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 55, "altura_saida_cm": 30,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('tamani', 'Tamani', '{
  "especie": "Panicum maximum", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "rotacionado", "altura_entrada_cm": 50, "altura_saida_cm": 25,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('xaraes', 'Xaraés', '{
  "especie": "Brachiaria brizantha", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 40, "altura_minima_cm": 20,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('piata', 'Piatã', '{
  "especie": "Brachiaria brizantha", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 40, "altura_minima_cm": 20,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"},
    {"metodo": "rotacionado", "altura_entrada_cm": 32.9, "altura_saida_cm": null,
     "altura_maxima_cm": null, "altura_minima_cm": null,
     "confianca": "baixa", "fonte": "Crestani et al., Embrapa (ILPF, pleno sol)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": 2.31, "temperatura_base_c": null,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}'),
('decumbens', 'Brachiaria decumbens', '{
  "especie": "Brachiaria decumbens", "via_fotossintetica": "C4",
  "por_regime": [
    {"metodo": "continuo", "altura_entrada_cm": null, "altura_saida_cm": null,
     "altura_maxima_cm": 30, "altura_minima_cm": 15,
     "confianca": "alta", "fonte": "Embrapa Gado de Corte, CT-135, Costa & Queiroz (ed. rev. 2017)"}
  ],
  "densidade_kg_ha_por_cm": null, "rue_max_g_por_mj": null, "temperatura_base_c": 16.7,
  "descanso_min_dias": 21, "descanso_max_dias": 45, "qualidade_base": null}');

INSERT INTO tipo_evento (tipo) VALUES ('altura_medida');

DROP TABLE estado_piquete;
DROP TABLE estado_lote;
DROP TABLE leitura;

CREATE TABLE estado_piquete (
    fazenda_id     UUID NOT NULL REFERENCES fazenda(id),
    piquete_id     UUID NOT NULL,
    nome           TEXT NOT NULL,
    area_ha        DOUBLE PRECISION NOT NULL,
    cultivar_id    UUID NOT NULL,
    metodo_pastejo TEXT NOT NULL,
    ativo          BOOLEAN NOT NULL,
    geometria      geometry(Polygon, 4326) NOT NULL,
    situacao       TEXT NOT NULL,
    lote_atual_id  UUID,
    desde          DATE NOT NULL,
    dias_descanso  INTEGER NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, piquete_id)
);
CREATE TABLE estado_lote (
    fazenda_id       UUID NOT NULL REFERENCES fazenda(id),
    lote_id          UUID NOT NULL,
    nome             TEXT NOT NULL,
    indissoluvel     BOOLEAN NOT NULL,
    composicao       JSONB NOT NULL,   -- [{categoria, n_animais, peso_medio_kg, origem_peso}]
    piquete_atual_id UUID,
    desde            DATE,
    peso_vivo_total_kg DOUBLE PRECISION NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, lote_id)
);
CREATE TABLE leitura (
    id              UUID NOT NULL,
    fazenda_id      UUID NOT NULL REFERENCES fazenda(id),
    piquete_id      UUID NOT NULL,
    data            DATE NOT NULL,
    ndvi            DOUBLE PRECISION NOT NULL,
    refletancia_red DOUBLE PRECISION NOT NULL,
    refletancia_nir DOUBLE PRECISION NOT NULL,
    origem          TEXT NOT NULL,
    pct_nuvem       DOUBLE PRECISION NOT NULL,
    pixels_validos  INTEGER NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, piquete_id)
);
CREATE TABLE altura_atual (
    fazenda_id  UUID NOT NULL REFERENCES fazenda(id),
    piquete_id  UUID NOT NULL,
    data        DATE NOT NULL,
    altura_cm   DOUBLE PRECISION NOT NULL,
    meio        TEXT NOT NULL,
    derivado_ate_sequencia BIGINT NOT NULL,
    derivado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (fazenda_id, piquete_id)
);

CREATE TABLE plano (
    id             UUID PRIMARY KEY,
    fazenda_id     UUID NOT NULL REFERENCES fazenda(id),
    gerado_em      TIMESTAMPTZ NOT NULL,
    data_inicio    DATE NOT NULL,
    horizonte_dias INTEGER NOT NULL,
    payload        JSONB NOT NULL
);
CREATE INDEX plano_fazenda_gerado_idx ON plano (fazenda_id, gerado_em DESC);

CREATE TABLE telegram_conversa (
    chat_id       BIGINT PRIMARY KEY,
    estado        TEXT NOT NULL,
    dados         JSONB NOT NULL DEFAULT '{}'::jsonb,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE tipo_evento ENABLE ROW LEVEL SECURITY;
ALTER TABLE origem_evento ENABLE ROW LEVEL SECURITY;
ALTER TABLE fazenda ENABLE ROW LEVEL SECURITY;
ALTER TABLE evento ENABLE ROW LEVEL SECURITY;
ALTER TABLE fazenda_usuario ENABLE ROW LEVEL SECURITY;
ALTER TABLE cultivar ENABLE ROW LEVEL SECURITY;
ALTER TABLE estado_piquete ENABLE ROW LEVEL SECURITY;
ALTER TABLE estado_lote ENABLE ROW LEVEL SECURITY;
ALTER TABLE leitura ENABLE ROW LEVEL SECURITY;
ALTER TABLE altura_atual ENABLE ROW LEVEL SECURITY;
ALTER TABLE plano ENABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_conversa ENABLE ROW LEVEL SECURITY;

COMMIT;
