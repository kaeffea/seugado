import { useState } from "react";
import iconeAtualizacao from "../assets/Icon Atualização do satelite.png";

type EstadoDecisao = "pendente" | "confirmada" | "recusada";
type EstadoVisualPiquete = "atencao" | "ok" | "neutro";

interface MovimentacaoMock {
  id: string;
  loteNome: string;
  piqueteOrigemNome: string;
  piqueteDestinoNome: string;
  motivo: string;
  status: EstadoDecisao;
}

interface PiqueteEstadoMock {
  nome: string;
  ocupado: boolean;
  alturaHojeCm: number | null;
  alturaEntradaAlvoCm: number | null;
  alturaSaidaAlvoCm: number | null;
}

interface AlertaMock {
  piqueteNome: string;
  texto: string;
}

const FAZENDA_MOCK = { nome: "Fazenda Belo Horizonte" };

const PLANO_MOCK = { geradoEm: "25/09", proximaEmDias: 4 };

const ATUALIZACAO_MOCK = { data: "24/09", haDias: 3 };

const KPIS_MOCK = {
  piquetesTotal: 8,
  piquetesOcupados: 4,
  piquetesDescanso: 4,
  areaTotalHa: 412,
  areaMediaHa: 51,
  cabecas: 418,
  uaTotal: 331,
  lotesTotal: 6,
  taxaLotacao: "0,80",
};

const MOVIMENTACOES_INICIAIS: MovimentacaoMock[] = [
  {
    id: "m1",
    loteNome: "Lote Recria",
    piqueteOrigemNome: "Piquete 3",
    piqueteDestinoNome: "Piquete 7",
    motivo: "Piquete 3 está em 12 cm, abaixo da altura de saída de 15 cm",
    status: "pendente",
  },
  {
    id: "m2",
    loteNome: "Lote Engorda A",
    piqueteOrigemNome: "Piquete 8",
    piqueteDestinoNome: "Piquete 2",
    motivo: "Piquete 2 chegou a 31 cm, dentro do ponto de entrada",
    status: "pendente",
  },
];

const PIQUETES_ESTADO_MOCK: PiqueteEstadoMock[] = [
  { nome: "Piquete 3", ocupado: true, alturaHojeCm: 12, alturaEntradaAlvoCm: 30, alturaSaidaAlvoCm: 15 },
  { nome: "Piquete 8", ocupado: true, alturaHojeCm: null, alturaEntradaAlvoCm: 30, alturaSaidaAlvoCm: 15 },
  { nome: "Piquete 1", ocupado: false, alturaHojeCm: 18, alturaEntradaAlvoCm: 30, alturaSaidaAlvoCm: 15 },
  { nome: "Piquete 5", ocupado: true, alturaHojeCm: 26, alturaEntradaAlvoCm: 30, alturaSaidaAlvoCm: 15 },
  { nome: "Piquete 4", ocupado: false, alturaHojeCm: 21, alturaEntradaAlvoCm: 30, alturaSaidaAlvoCm: 15 },
  { nome: "Piquete 6", ocupado: false, alturaHojeCm: 34, alturaEntradaAlvoCm: 30, alturaSaidaAlvoCm: 15 },
  { nome: "Piquete 2", ocupado: true, alturaHojeCm: 31, alturaEntradaAlvoCm: 30, alturaSaidaAlvoCm: 15 },
  { nome: "Piquete 7", ocupado: false, alturaHojeCm: 38, alturaEntradaAlvoCm: null, alturaSaidaAlvoCm: null },
];

const ALERTAS_MOCK: AlertaMock[] = [
  { piqueteNome: "Piquete 3", texto: "Abaixo da altura de saída há 4 dias" },
  { piqueteNome: "Piquete 8", texto: "Abaixo da altura de saída" },
  { piqueteNome: "Piquete 5", texto: "67 dias em descanso, passou do ponto" },
];

function estadoVisual(p: PiqueteEstadoMock): EstadoVisualPiquete {
  if (p.alturaHojeCm === null) {
    return "neutro";
  }
  if (p.ocupado) {
    if (p.alturaSaidaAlvoCm === null) {
      return "neutro";
    }
    return p.alturaHojeCm < p.alturaSaidaAlvoCm ? "atencao" : "ok";
  }
  if (p.alturaEntradaAlvoCm === null) {
    return "neutro";
  }
  return p.alturaHojeCm >= p.alturaEntradaAlvoCm ? "ok" : "neutro";
}

function rotuloLateral(p: PiqueteEstadoMock): string {
  if (p.alturaHojeCm === null) {
    return "sem leitura";
  }
  const alvo = p.ocupado ? p.alturaSaidaAlvoCm : p.alturaEntradaAlvoCm;
  if (alvo === null) {
    return "sem alvo (contínuo)";
  }
  const rotuloAlvo = p.ocupado ? "saída" : "entrada";
  return `${p.alturaHojeCm}/${alvo}cm ${rotuloAlvo}`;
}

function percentualBarra(p: PiqueteEstadoMock): number {
  if (p.alturaHojeCm === null) {
    return 0;
  }
  const alvo = p.ocupado ? p.alturaSaidaAlvoCm : p.alturaEntradaAlvoCm;
  if (alvo === null || alvo === 0) {
    return 0;
  }
  return Math.min(100, Math.round((p.alturaHojeCm / alvo) * 100));
}

export default function Dashboard() {
  const [movimentacoes, setMovimentacoes] = useState(MOVIMENTACOES_INICIAIS);

  function decidir(id: string, status: EstadoDecisao): void {
    setMovimentacoes((atual) => atual.map((m) => (m.id === id ? { ...m, status } : m)));
  }

  return (
    <div className="dashboard">
      <header className="dashboard-cabecalho">
        <div>
          <h1 className="dashboard-titulo">
            {FAZENDA_MOCK.nome} • {KPIS_MOCK.areaTotalHa} ha
          </h1>
        </div>
        <div className="dashboard-cabecalho-acoes">
          <span className="dashboard-badge-atualizacao">
            <img src={iconeAtualizacao} alt="" className="dashboard-badge-icone" />
            Atualização de {ATUALIZACAO_MOCK.data} • há {ATUALIZACAO_MOCK.haDias} dias
          </span>
          <button type="button" className="dashboard-botao-notificacao" aria-label="Notificações">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" aria-hidden="true">
              <path
                d="M12 3a5 5 0 0 0-5 5v3.2c0 .5-.2 1-.5 1.4L5 15h14l-1.5-2.4a2.3 2.3 0 0 1-.5-1.4V8a5 5 0 0 0-5-5Z"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
              <path
                d="M9.5 18a2.5 2.5 0 0 0 5 0"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>
      </header>

      <section className="dashboard-recomendacao" aria-labelledby="recomendacao-titulo">
        <div className="recomendacao-cabecalho">
          <h2 id="recomendacao-titulo">Recomendação da semana</h2>
          <p>
            Gerada em {PLANO_MOCK.geradoEm} • próxima em {PLANO_MOCK.proximaEmDias} dias
          </p>
        </div>
        <ul className="recomendacao-lista">
          {movimentacoes.map((m) => (
            <li key={m.id} className="recomendacao-linha">
              <div className="recomendacao-texto">
                <p className="recomendacao-titulo-linha">
                  <strong>{m.loteNome}</strong> {m.piqueteOrigemNome} → {m.piqueteDestinoNome}
                </p>
                <p className="recomendacao-motivo">{m.motivo}</p>
              </div>
              <div className="recomendacao-acoes">
                <span className={`recomendacao-status recomendacao-status-${m.status}`}>
                  {m.status === "pendente" && "Pendente"}
                  {m.status === "confirmada" && "Confirmada"}
                  {m.status === "recusada" && "Recusada"}
                </span>
                {m.status === "pendente" && (
                  <>
                    <button
                      type="button"
                      className="recomendacao-botao recomendacao-botao-confirmar"
                      onClick={() => decidir(m.id, "confirmada")}
                    >
                      Confirmar
                    </button>
                    <button
                      type="button"
                      className="recomendacao-botao recomendacao-botao-recusar"
                      onClick={() => decidir(m.id, "recusada")}
                    >
                      Recusar
                    </button>
                  </>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="dashboard-kpis" aria-label="Indicadores da fazenda">
        <div className="kpi-card">
          <span className="kpi-rotulo">Piquetes</span>
          <span className="kpi-valor">{KPIS_MOCK.piquetesTotal}</span>
          <span className="kpi-detalhe">
            {KPIS_MOCK.piquetesOcupados} ocupados • {KPIS_MOCK.piquetesDescanso} em descanso
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-rotulo">Área Total</span>
          <span className="kpi-valor">{KPIS_MOCK.areaTotalHa} ha</span>
          <span className="kpi-detalhe">média de {KPIS_MOCK.areaMediaHa} ha por piquete</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-rotulo">Cabeças</span>
          <span className="kpi-valor">{KPIS_MOCK.cabecas}</span>
          <span className="kpi-detalhe">
            {KPIS_MOCK.uaTotal} UA em {KPIS_MOCK.lotesTotal} lotes
          </span>
        </div>
        <div className="kpi-card">
          <span className="kpi-rotulo">Taxa de Lotação</span>
          <span className="kpi-valor">{KPIS_MOCK.taxaLotacao} UA/ha</span>
          <span className="kpi-detalhe">sobre a área em uso</span>
        </div>
      </section>

      <div className="dashboard-grade">
        <section className="dashboard-piquetes" aria-labelledby="piquetes-titulo">
          <div className="piquetes-cabecalho">
            <h2 id="piquetes-titulo">Estado dos Piquetes</h2>
            <ul className="piquetes-legenda">
              <li>
                <span className="legenda-marcador legenda-atencao" /> abaixo da saída
              </li>
              <li>
                <span className="legenda-marcador legenda-neutro" /> em descanso
              </li>
              <li>
                <span className="legenda-marcador legenda-ok" /> pronto
              </li>
            </ul>
          </div>
          <ul className="piquetes-lista">
            {PIQUETES_ESTADO_MOCK.map((p) => (
              <li key={p.nome} className="piquete-linha">
                <span className="piquete-nome">{p.nome}</span>
                <span className="piquete-barra-trilho">
                  <span
                    className={`piquete-barra-preenchimento piquete-barra-${estadoVisual(p)}`}
                    style={{ width: `${percentualBarra(p)}%` }}
                  />
                </span>
                <span className="piquete-rotulo-lateral">{rotuloLateral(p)}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="dashboard-atencao" aria-labelledby="atencao-titulo">
          <h2 id="atencao-titulo">Precisa de atenção</h2>
          <ul className="atencao-lista">
            {ALERTAS_MOCK.map((a, indice) => (
              <li key={`${a.piqueteNome}-${indice}`} className="atencao-cartao">
                <strong>{a.piqueteNome}</strong>
                <span>{a.texto}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
