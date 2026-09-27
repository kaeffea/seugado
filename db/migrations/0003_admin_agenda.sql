BEGIN;

CREATE TABLE cliente (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome        TEXT NOT NULL,
    telefone    TEXT,
    observacoes TEXT,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE cliente ENABLE ROW LEVEL SECURITY;

ALTER TABLE fazenda ADD COLUMN cliente_id UUID REFERENCES cliente(id);
ALTER TABLE fazenda RENAME COLUMN manejos_por_funcionario_dia TO animais_por_funcionario_dia;
ALTER TABLE fazenda
    ADD COLUMN envio_plano_dia SMALLINT NOT NULL DEFAULT 0
        CHECK (envio_plano_dia BETWEEN 0 AND 6),
    ADD COLUMN envio_plano_hora SMALLINT NOT NULL DEFAULT 6
        CHECK (envio_plano_hora BETWEEN 0 AND 23),
    ADD COLUMN ultimo_envio_semanal DATE,
    ADD COLUMN ultima_rotina_diaria DATE;
CREATE UNIQUE INDEX fazenda_telegram_chat_idx
    ON fazenda (telegram_chat_id) WHERE telegram_chat_id IS NOT NULL;

ALTER TABLE plano ADD COLUMN status TEXT NOT NULL DEFAULT 'vigente'
    CHECK (status IN ('vigente', 'candidato', 'substituido', 'descartado'));
CREATE INDEX plano_fazenda_status_idx ON plano (fazenda_id, status, gerado_em DESC);

COMMIT;
