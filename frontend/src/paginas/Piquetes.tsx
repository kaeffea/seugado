import { useMemo, useState, type FormEvent, type ReactNode } from "react";

type Confianca = "alta" | "media" | "baixa";
type EstadoPiquete = "atencao" | "ocupado" | "pronto" | "descanso";
type CriterioOrdenacao = "nome" | "altura" | "area" | "dias";

interface PiqueteMock {
  nome: string;
  areaHa: number;
  capim: string;
  alturaAtualCm: number;
  alturaEntradaAlvoCm: number | null;
  alturaSaidaAlvoCm: number | null;
  massaKgMsHa: number;
  confianca: Confianca;
  ocupado: boolean;
  loteOcupante: string | null;
  dias: number;
  ultimaImagem: string;
}

const PIQUETES_INICIAIS: PiqueteMock[] = [
  {
    nome: "Piquete 1",
    areaHa: 62,
    capim: "Mombaça",
    alturaAtualCm: 24,
    alturaEntradaAlvoCm: 30,
    alturaSaidaAlvoCm: 15,
    massaKgMsHa: 3050,
    confianca: "alta",
    ocupado: false,
    loteOcupante: null,
    dias: 67,
    ultimaImagem: "24/09",
  },
  {
    nome: "Piquete 2",
    areaHa: 48,
    capim: "Braquiária",
    alturaAtualCm: 31,
    alturaEntradaAlvoCm: 30,
    alturaSaidaAlvoCm: 15,
    massaKgMsHa: 3390,
    confianca: "alta",
    ocupado: false,
    loteOcupante: null,
    dias: 41,
    ultimaImagem: "24/09",
  },
  {
    nome: "Piquete 3",
    areaHa: 48,
    capim: "Braquiária",
    alturaAtualCm: 12,
    alturaEntradaAlvoCm: 30,
    alturaSaidaAlvoCm: 15,
    massaKgMsHa: 1120,
    confianca: "alta",
    ocupado: true,
    loteOcupante: "Recria",
    dias: 31,
    ultimaImagem: "24/09",
  },
  {
    nome: "Piquete 4",
    areaHa: 51,
    capim: "Mombaça",
    alturaAtualCm: 22,
    alturaEntradaAlvoCm: 30,
    alturaSaidaAlvoCm: 15,
    massaKgMsHa: 4120,
    confianca: "media",
    ocupado: false,
    loteOcupante: null,
    dias: 38,
    ultimaImagem: "18/09",
  },
  {
    nome: "Piquete 5",
    areaHa: 46,
    capim: "Braquiária",
    alturaAtualCm: 18,
    alturaEntradaAlvoCm: 30,
    alturaSaidaAlvoCm: 15,
    massaKgMsHa: 1940,
    confianca: "baixa",
    ocupado: true,
    loteOcupante: "Engorda B",
    dias: 9,
    ultimaImagem: "09/09",
  },
  {
    nome: "Piquete 6",
    areaHa: 44,
    capim: "Braquiária",
    alturaAtualCm: 26,
    alturaEntradaAlvoCm: 30,
    alturaSaidaAlvoCm: 15,
    massaKgMsHa: 2780,
    confianca: "alta",
    ocupado: true,
    loteOcupante: "Cria",
    dias: 14,
    ultimaImagem: "24/09",
  },
  {
    nome: "Piquete 7",
    areaHa: 58,
    capim: "Mombaça",
    alturaAtualCm: 38,
    alturaEntradaAlvoCm: null,
    alturaSaidaAlvoCm: null,
    massaKgMsHa: 5240,
    confianca: "alta",
    ocupado: false,
    loteOcupante: null,
    dias: 52,
    ultimaImagem: "24/09",
  },
  {
    nome: "Piquete 8",
    areaHa: 55,
    capim: "Mombaça",
    alturaAtualCm: 13,
    alturaEntradaAlvoCm: 30,
    alturaSaidaAlvoCm: 15,
    massaKgMsHa: 1480,
    confianca: "alta",
    ocupado: true,
    loteOcupante: "Engorda A",
    dias: 26,
    ultimaImagem: "24/09",
  },
];

const ESTADO_ROTULO: Record<EstadoPiquete, string> = {
  atencao: "Atenção",
  ocupado: "Ocupado",
  pronto: "Pronto",
  descanso: "Descanso",
};

const CONFIANCA_ROTULO: Record<Confianca, string> = {
  alta: "Alta",
  media: "Média",
  baixa: "Baixa",
};

function estadoPiquete(p: PiqueteMock): EstadoPiquete {
  if (p.ocupado) {
    if (p.alturaSaidaAlvoCm !== null && p.alturaAtualCm < p.alturaSaidaAlvoCm) {
      return "atencao";
    }
    return "ocupado";
  }
  if (p.alturaEntradaAlvoCm === null) {
    return "pronto";
  }
  return p.alturaAtualCm >= p.alturaEntradaAlvoCm ? "pronto" : "descanso";
}

const ESTADO_CLASSE_BARRA: Record<EstadoPiquete, string> = {
  atencao: "piquete-barra-atencao",
  pronto: "piquete-barra-ok",
  descanso: "piquete-barra-neutro",
  ocupado: "piquete-barra-ocupado",
};

function percentualAltura(p: PiqueteMock): number {
  const alvo = p.ocupado ? p.alturaSaidaAlvoCm : p.alturaEntradaAlvoCm;
  if (alvo === null || alvo === 0) {
    return Math.min(100, Math.round((p.alturaAtualCm / 40) * 100));
  }
  return Math.min(100, Math.round((p.alturaAtualCm / alvo) * 100));
}

const CHIPS: { chave: "todos" | EstadoPiquete; rotulo: string }[] = [
  { chave: "todos", rotulo: "Todos" },
  { chave: "ocupado", rotulo: "Ocupados" },
  { chave: "descanso", rotulo: "Em descanso" },
  { chave: "pronto", rotulo: "Prontos" },
  { chave: "atencao", rotulo: "Atenção" },
];

function Modal({
  titulo,
  onFechar,
  children,
}: {
  titulo: string;
  onFechar: () => void;
  children: ReactNode;
}) {
  return (
    <div className="modal-fundo" onClick={onFechar}>
      <div
        className="modal-cartao"
        role="dialog"
        aria-modal="true"
        aria-label={titulo}
        onClick={(evento) => evento.stopPropagation()}
      >
        <div className="modal-cabecalho">
          <h2>{titulo}</h2>
          <button type="button" className="modal-fechar" aria-label="Fechar" onClick={onFechar}>
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function ModalEditar({
  piquete,
  capins,
  onSalvar,
  onFechar,
}: {
  piquete: PiqueteMock;
  capins: string[];
  onSalvar: (editado: PiqueteMock) => void;
  onFechar: () => void;
}) {
  const [nome, setNome] = useState(piquete.nome);
  const [areaHa, setAreaHa] = useState(String(piquete.areaHa));
  const [capim, setCapim] = useState(piquete.capim);
  const [alturaAtualCm, setAlturaAtualCm] = useState(String(piquete.alturaAtualCm));
  const [loteOcupante, setLoteOcupante] = useState(piquete.loteOcupante ?? "");

  function handleSubmit(evento: FormEvent<HTMLFormElement>): void {
    evento.preventDefault();
    onSalvar({
      ...piquete,
      nome: nome.trim() === "" ? piquete.nome : nome.trim(),
      areaHa: Number(areaHa) || piquete.areaHa,
      capim,
      alturaAtualCm: Number(alturaAtualCm) || piquete.alturaAtualCm,
      loteOcupante: loteOcupante.trim() === "" ? null : loteOcupante.trim(),
    });
  }

  return (
    <Modal titulo={`Editar ${piquete.nome}`} onFechar={onFechar}>
      <form className="modal-formulario" onSubmit={handleSubmit}>
        <label className="modal-campo">
          <span>Nome</span>
          <input
            className="modal-input"
            value={nome}
            onChange={(evento) => setNome(evento.target.value)}
          />
        </label>
        <label className="modal-campo">
          <span>Área (ha)</span>
          <input
            className="modal-input"
            type="number"
            min="0"
            step="0.1"
            value={areaHa}
            onChange={(evento) => setAreaHa(evento.target.value)}
          />
        </label>
        <label className="modal-campo">
          <span>Capim</span>
          <select
            className="modal-input"
            value={capim}
            onChange={(evento) => setCapim(evento.target.value)}
          >
            {capins.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <label className="modal-campo">
          <span>Altura atual (cm)</span>
          <input
            className="modal-input"
            type="number"
            min="0"
            step="1"
            value={alturaAtualCm}
            onChange={(evento) => setAlturaAtualCm(evento.target.value)}
          />
        </label>
        <label className="modal-campo">
          <span>Lote ocupante</span>
          <input
            className="modal-input"
            value={loteOcupante}
            onChange={(evento) => setLoteOcupante(evento.target.value)}
            placeholder="Nenhum"
          />
        </label>
        <div className="modal-acoes">
          <button type="button" className="modal-botao modal-botao-secundario" onClick={onFechar}>
            Cancelar
          </button>
          <button type="submit" className="modal-botao modal-botao-primario">
            Salvar
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ModalExcluir({
  piquete,
  onConfirmar,
  onFechar,
}: {
  piquete: PiqueteMock;
  onConfirmar: () => void;
  onFechar: () => void;
}) {
  return (
    <Modal titulo="Excluir piquete" onFechar={onFechar}>
      <p className="modal-texto">
        Tem certeza que deseja excluir o <strong>{piquete.nome}</strong>? Essa ação não pode ser
        desfeita.
      </p>
      <div className="modal-acoes">
        <button type="button" className="modal-botao modal-botao-secundario" onClick={onFechar}>
          Cancelar
        </button>
        <button type="button" className="modal-botao modal-botao-perigo" onClick={onConfirmar}>
          Excluir
        </button>
      </div>
    </Modal>
  );
}

export default function Piquetes() {
  const [piquetes, setPiquetes] = useState(PIQUETES_INICIAIS);
  const [busca, setBusca] = useState("");
  const [capimSelecionado, setCapimSelecionado] = useState("todos");
  const [chipAtivo, setChipAtivo] = useState<"todos" | EstadoPiquete>("todos");
  const [ordenacao, setOrdenacao] = useState<CriterioOrdenacao>("nome");
  const [piqueteEditando, setPiqueteEditando] = useState<PiqueteMock | null>(null);
  const [piqueteExcluindo, setPiqueteExcluindo] = useState<PiqueteMock | null>(null);

  const capins = useMemo(
    () => Array.from(new Set(piquetes.map((p) => p.capim))).sort(),
    [piquetes],
  );

  const contagens = useMemo(() => {
    const base: Record<"todos" | EstadoPiquete, number> = {
      todos: piquetes.length,
      atencao: 0,
      ocupado: 0,
      pronto: 0,
      descanso: 0,
    };
    for (const p of piquetes) {
      base[estadoPiquete(p)] += 1;
    }
    return base;
  }, [piquetes]);

  const areaTotalHa = useMemo(
    () => piquetes.reduce((soma, p) => soma + p.areaHa, 0),
    [piquetes],
  );

  const piquetesVisiveis = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    const filtrados = piquetes.filter((p) => {
      if (termo !== "" && !p.nome.toLowerCase().includes(termo)) {
        return false;
      }
      if (capimSelecionado !== "todos" && p.capim !== capimSelecionado) {
        return false;
      }
      if (chipAtivo !== "todos" && estadoPiquete(p) !== chipAtivo) {
        return false;
      }
      return true;
    });
    const ordenados = [...filtrados];
    ordenados.sort((a, b) => {
      switch (ordenacao) {
        case "altura":
          return a.alturaAtualCm - b.alturaAtualCm;
        case "area":
          return a.areaHa - b.areaHa;
        case "dias":
          return a.dias - b.dias;
        default:
          return a.nome.localeCompare(b.nome, "pt-BR", { numeric: true });
      }
    });
    return ordenados;
  }, [piquetes, busca, capimSelecionado, chipAtivo, ordenacao]);

  function salvarEdicao(editado: PiqueteMock): void {
    setPiquetes((atual) => atual.map((p) => (p.nome === piqueteEditando?.nome ? editado : p)));
    setPiqueteEditando(null);
  }

  function confirmarExclusao(): void {
    setPiquetes((atual) => atual.filter((p) => p.nome !== piqueteExcluindo?.nome));
    setPiqueteExcluindo(null);
  }

  return (
    <div className="piquetes-pagina">
      <header className="piquetes-cabecalho-pagina">
        <h1 className="piquetes-titulo-pagina">Piquetes</h1>
        <p className="piquetes-subtitulo-pagina">
          {piquetes.length} piquetes • {areaTotalHa} ha
        </p>
      </header>

      <div className="piquetes-filtros">
        <ul className="piquetes-chips">
          {CHIPS.map((chip) => (
            <li key={chip.chave}>
              <button
                type="button"
                className={
                  chip.chave === chipAtivo
                    ? "filtro-chip filtro-chip-ativo"
                    : "filtro-chip"
                }
                onClick={() => setChipAtivo(chip.chave)}
              >
                {chip.rotulo} · {contagens[chip.chave]}
              </button>
            </li>
          ))}
        </ul>

        <div className="piquetes-filtros-secundarios">
          <input
            type="search"
            placeholder="Buscar piquete"
            className="filtro-busca"
            value={busca}
            onChange={(evento) => setBusca(evento.target.value)}
            aria-label="Buscar piquete"
          />
          <select
            className="filtro-select"
            value={capimSelecionado}
            onChange={(evento) => setCapimSelecionado(evento.target.value)}
            aria-label="Filtrar por capim"
          >
            <option value="todos">Capim: todos</option>
            {capins.map((capim) => (
              <option key={capim} value={capim}>
                Capim: {capim}
              </option>
            ))}
          </select>
          <select
            className="filtro-select"
            value={ordenacao}
            onChange={(evento) => setOrdenacao(evento.target.value as CriterioOrdenacao)}
            aria-label="Ordenar por"
          >
            <option value="nome">Ordenar: nome</option>
            <option value="altura">Ordenar: altura</option>
            <option value="area">Ordenar: área</option>
            <option value="dias">Ordenar: dias</option>
          </select>
        </div>
      </div>

      <div className="piquetes-tabela-cartao">
        <div className="piquetes-tabela-wrap">
          <table className="piquetes-tabela">
            <thead>
              <tr>
                <th>Piquete</th>
                <th>Área</th>
                <th>Capim</th>
                <th>Altura</th>
                <th>Massa</th>
                <th>Confiança</th>
                <th>Status</th>
                <th>Lote ocupante</th>
                <th>Dias</th>
                <th>Imagem</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {piquetesVisiveis.length === 0 && (
                <tr>
                  <td colSpan={11} className="piquetes-tabela-vazia">
                    Nenhum piquete encontrado para esse filtro.
                  </td>
                </tr>
              )}
              {piquetesVisiveis.map((p) => {
                const estado = estadoPiquete(p);
                return (
                  <tr key={p.nome}>
                    <td className="piquetes-tabela-nome">{p.nome}</td>
                    <td>{p.areaHa} ha</td>
                    <td>{p.capim}</td>
                    <td>
                      <div className="piquetes-altura-celula">
                        <span className="piquete-barra-trilho piquetes-barra-mini">
                          <span
                            className={`piquete-barra-preenchimento ${ESTADO_CLASSE_BARRA[estado]}`}
                            style={{ width: `${percentualAltura(p)}%` }}
                          />
                        </span>
                        <span>{p.alturaAtualCm} cm</span>
                      </div>
                    </td>
                    <td>{p.massaKgMsHa.toLocaleString("pt-BR")}</td>
                    <td>
                      <span className={`confianca-texto confianca-${p.confianca}`}>
                        {CONFIANCA_ROTULO[p.confianca]}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge status-badge-${estado}`}>
                        {ESTADO_ROTULO[estado]}
                      </span>
                    </td>
                    <td>{p.loteOcupante ?? "—"}</td>
                    <td>{p.dias} d</td>
                    <td>{p.ultimaImagem}</td>
                    <td>
                      <div className="tabela-acoes">
                        <button
                          type="button"
                          className="tabela-acao-botao"
                          aria-label="Editar piquete"
                          onClick={() => setPiqueteEditando(p)}
                        >
                          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
                            <path
                              d="M4 20l.9-3.6L16.4 5 19 7.6 7.6 19l-3.6.9Z"
                              stroke="currentColor"
                              strokeWidth="1.6"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </button>
                        <button
                          type="button"
                          className="tabela-acao-botao"
                          aria-label="Excluir piquete"
                          onClick={() => setPiqueteExcluindo(p)}
                        >
                          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
                            <path
                              d="M5 7h14M9 7V5h6v2M6 7l1 13h10l1-13"
                              stroke="currentColor"
                              strokeWidth="1.6"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {piqueteEditando && (
        <ModalEditar
          key={piqueteEditando.nome}
          piquete={piqueteEditando}
          capins={capins}
          onSalvar={salvarEdicao}
          onFechar={() => setPiqueteEditando(null)}
        />
      )}
      {piqueteExcluindo && (
        <ModalExcluir
          piquete={piqueteExcluindo}
          onConfirmar={confirmarExclusao}
          onFechar={() => setPiqueteExcluindo(null)}
        />
      )}
    </div>
  );
}
