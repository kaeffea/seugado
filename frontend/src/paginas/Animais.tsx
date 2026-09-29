import { useMemo, useState, type FormEvent, type ReactNode } from "react";

type Categoria = "bezerro" | "bezerra" | "novilho" | "novilha" | "vaca" | "boi" | "touro";
type CriterioOrdenacao = "nome" | "cabecas" | "ua" | "dias";

interface LoteMock {
  id: string;
  nome: string;
  raca: string;
  piqueteAtualNome: string;
  dias: number;
  quantidadeTotal: number;
  pesoMedioKg: number;
}

interface PiqueteParaLote {
  nome: string;
  alturaCm: number;
}

const PIQUETES_PARA_LOTE: PiqueteParaLote[] = [
  { nome: "Piquete 1", alturaCm: 18 },
  { nome: "Piquete 2", alturaCm: 31 },
  { nome: "Piquete 3", alturaCm: 12 },
  { nome: "Piquete 4", alturaCm: 22 },
  { nome: "Piquete 5", alturaCm: 26 },
  { nome: "Piquete 6", alturaCm: 34 },
  { nome: "Piquete 7", alturaCm: 88 },
  { nome: "Piquete 8", alturaCm: 13 },
];

const RACAS_DISPONIVEIS = ["Nelore", "Angus", "Brahman", "Cruzado"];

let contadorId = 0;
function gerarId(prefixo: string): string {
  contadorId += 1;
  return `${prefixo}${contadorId}`;
}

const CATEGORIA_ROTULO: Record<Categoria, string> = {
  bezerro: "Bezerro",
  bezerra: "Bezerra",
  novilho: "Novilho",
  novilha: "Novilha",
  vaca: "Vaca",
  boi: "Boi",
  touro: "Touro",
};

const LOTES_INICIAIS: LoteMock[] = [
  {
    id: "l1",
    nome: "Engorda A",
    raca: "Nelore",
    piqueteAtualNome: "Piquete 8",
    dias: 26,
    quantidadeTotal: 112,
    pesoMedioKg: 448,
  },
  {
    id: "l2",
    nome: "Engorda B",
    raca: "Nelore",
    piqueteAtualNome: "Piquete 5",
    dias: 9,
    quantidadeTotal: 90,
    pesoMedioKg: 418,
  },
  {
    id: "l3",
    nome: "Recria",
    raca: "Cruzado",
    piqueteAtualNome: "Piquete 3",
    dias: 31,
    quantidadeTotal: 110,
    pesoMedioKg: 219,
  },
  {
    id: "l4",
    nome: "Cria",
    raca: "Nelore",
    piqueteAtualNome: "Piquete 6",
    dias: 14,
    quantidadeTotal: 138,
    pesoMedioKg: 266,
  },
  {
    id: "l5",
    nome: "Reposição",
    raca: "Angus",
    piqueteAtualNome: "Piquete 1",
    dias: 14,
    quantidadeTotal: 18,
    pesoMedioKg: 280,
  },
  {
    id: "l6",
    nome: "Touros",
    raca: "Nelore",
    piqueteAtualNome: "Piquete 7",
    dias: 26,
    quantidadeTotal: 8,
    pesoMedioKg: 780,
  },
];

function uaTotal(lote: { quantidadeTotal: number; pesoMedioKg: number }): number {
  return (lote.quantidadeTotal * lote.pesoMedioKg) / 450;
}

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
        className="modal-cartao modal-cartao-largo"
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

interface ValoresLote {
  nome: string;
  raca: string;
  piqueteAtualNome: string;
  quantidadeTotal: number;
  pesoMedioKg: number;
}

const COMPOSICAO_EXEMPLO: { categoria: Categoria }[] = [{ categoria: "novilho" }];

function FormularioLote({
  titulo,
  subtitulo,
  textoSalvar,
  valoresIniciais,
  onSalvar,
  onFechar,
}: {
  titulo: string;
  subtitulo: string;
  textoSalvar: string;
  valoresIniciais: ValoresLote;
  onSalvar: (valores: ValoresLote) => void;
  onFechar: () => void;
}) {
  const [nome, setNome] = useState(valoresIniciais.nome);
  const [raca, setRaca] = useState(valoresIniciais.raca);
  const [piqueteAtualNome, setPiqueteAtualNome] = useState(valoresIniciais.piqueteAtualNome);
  const [quantidadeTotal, setQuantidadeTotal] = useState(String(valoresIniciais.quantidadeTotal));
  const [pesoMedioKg, setPesoMedioKg] = useState(String(valoresIniciais.pesoMedioKg));

  const totalUa = useMemo(
    () => (Number(quantidadeTotal) * Number(pesoMedioKg)) / 450,
    [quantidadeTotal, pesoMedioKg],
  );

  function handleSubmit(evento: FormEvent<HTMLFormElement>): void {
    evento.preventDefault();
    onSalvar({
      nome: nome.trim() === "" ? valoresIniciais.nome : nome.trim(),
      raca,
      piqueteAtualNome,
      quantidadeTotal: Number(quantidadeTotal) || 0,
      pesoMedioKg: Number(pesoMedioKg) || 0,
    });
  }

  return (
    <Modal titulo={titulo} onFechar={onFechar}>
      <form className="modal-formulario" onSubmit={handleSubmit}>
        <p className="modal-texto">{subtitulo}</p>
        <div className="lote-form-grade">
          <label className="modal-campo">
            <span>Nome do lote</span>
            <input
              className="modal-input"
              value={nome}
              onChange={(evento) => setNome(evento.target.value)}
            />
          </label>
          <label className="modal-campo">
            <span>Piquete atual</span>
            <select
              className="modal-input"
              value={piqueteAtualNome}
              onChange={(evento) => setPiqueteAtualNome(evento.target.value)}
            >
              {PIQUETES_PARA_LOTE.map((p) => (
                <option key={p.nome} value={p.nome}>
                  {p.nome} · {p.alturaCm}cm
                </option>
              ))}
            </select>
          </label>
          <label className="modal-campo">
            <span>Raça</span>
            <select
              className="modal-input"
              value={raca}
              onChange={(evento) => setRaca(evento.target.value)}
            >
              {RACAS_DISPONIVEIS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="lote-form-grade lote-form-grade-2">
          <label className="modal-campo">
            <span>Quantidade total</span>
            <input
              className="modal-input"
              type="number"
              min="0"
              value={quantidadeTotal}
              onChange={(evento) => setQuantidadeTotal(evento.target.value)}
            />
          </label>
          <label className="modal-campo">
            <span>Peso médio (kg)</span>
            <input
              className="modal-input"
              type="number"
              min="0"
              value={pesoMedioKg}
              onChange={(evento) => setPesoMedioKg(evento.target.value)}
            />
          </label>
        </div>

        <div className="composicao-secao">
          <div className="composicao-titulo">
            <span>Composição por categoria</span>
            <span className="badge-em-desenvolvimento">Em desenvolvimento</span>
          </div>
          <div className="composicao-bloqueada">
            <div className="composicao-cabecalho">
              <span>Categoria</span>
              <span>Quantidade</span>
              <span>Peso médio (kg)</span>
              <span />
            </div>
            {COMPOSICAO_EXEMPLO.map((linha) => (
              <div key={linha.categoria} className="composicao-linha">
                <select className="modal-input" value={linha.categoria} disabled>
                  {Object.entries(CATEGORIA_ROTULO).map(([valor, rotulo]) => (
                    <option key={valor} value={valor}>
                      {rotulo}
                    </option>
                  ))}
                </select>
                <input className="modal-input" type="number" value="" placeholder="—" disabled />
                <input className="modal-input" type="number" value="" placeholder="—" disabled />
                <button type="button" className="composicao-remover" disabled aria-hidden="true">
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
            ))}
            <button type="button" className="composicao-adicionar" disabled>
              + Adicionar categoria
            </button>
          </div>
        </div>

        <div className="composicao-totais">
          <div>
            <span className="composicao-total-rotulo">Total em UA</span>
            <span className="composicao-total-valor">
              {totalUa.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}
            </span>
          </div>
          <p className="composicao-total-nota">
            Calculado ao vivo.
            <br />1 UA = 450 kg de peso vivo.
          </p>
        </div>

        <div className="modal-acoes">
          <button type="button" className="modal-botao modal-botao-secundario" onClick={onFechar}>
            Cancelar
          </button>
          <button type="submit" className="modal-botao modal-botao-primario">
            {textoSalvar}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ModalMoverLote({
  lote,
  onSalvar,
  onFechar,
}: {
  lote: LoteMock;
  onSalvar: (novoPiquete: string) => void;
  onFechar: () => void;
}) {
  const [piquete, setPiquete] = useState(lote.piqueteAtualNome);

  function handleSubmit(evento: FormEvent<HTMLFormElement>): void {
    evento.preventDefault();
    onSalvar(piquete);
  }

  return (
    <Modal titulo={`Mover ${lote.nome}`} onFechar={onFechar}>
      <form className="modal-formulario" onSubmit={handleSubmit}>
        <p className="modal-texto">
          Piquete atual: <strong>{lote.piqueteAtualNome}</strong>
        </p>
        <label className="modal-campo">
          <span>Novo piquete</span>
          <select
            className="modal-input"
            value={piquete}
            onChange={(evento) => setPiquete(evento.target.value)}
          >
            {PIQUETES_PARA_LOTE.filter((p) => p.nome !== lote.piqueteAtualNome).map((p) => (
              <option key={p.nome} value={p.nome}>
                {p.nome} · {p.alturaCm}cm
              </option>
            ))}
          </select>
        </label>
        <div className="modal-acoes">
          <button type="button" className="modal-botao modal-botao-secundario" onClick={onFechar}>
            Cancelar
          </button>
          <button type="submit" className="modal-botao modal-botao-primario">
            Mover
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ModalExcluirLote({
  lote,
  onConfirmar,
  onFechar,
}: {
  lote: LoteMock;
  onConfirmar: () => void;
  onFechar: () => void;
}) {
  return (
    <Modal titulo="Excluir lote" onFechar={onFechar}>
      <p className="modal-texto">
        Tem certeza que deseja excluir o lote <strong>{lote.nome}</strong>? Essa ação não pode
        ser desfeita.
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

export default function Animais() {
  const [lotes, setLotes] = useState(LOTES_INICIAIS);
  const [busca, setBusca] = useState("");
  const [piqueteFiltro, setPiqueteFiltro] = useState("todos");
  const [racaFiltro, setRacaFiltro] = useState("todos");
  const [ordenacao, setOrdenacao] = useState<CriterioOrdenacao>("nome");
  const [adicionando, setAdicionando] = useState(false);
  const [loteEditando, setLoteEditando] = useState<LoteMock | null>(null);
  const [loteMovendo, setLoteMovendo] = useState<LoteMock | null>(null);
  const [loteExcluindo, setLoteExcluindo] = useState<LoteMock | null>(null);

  const racas = useMemo(() => Array.from(new Set(lotes.map((l) => l.raca))).sort(), [lotes]);

  const totais = useMemo(
    () => ({
      lotes: lotes.length,
      cabecas: lotes.reduce((soma, l) => soma + l.quantidadeTotal, 0),
      ua: lotes.reduce((soma, l) => soma + uaTotal(l), 0),
    }),
    [lotes],
  );

  const lotesVisiveis = useMemo(() => {
    const termo = busca.trim().toLowerCase();
    const filtrados = lotes.filter((l) => {
      if (termo !== "" && !l.nome.toLowerCase().includes(termo)) {
        return false;
      }
      if (piqueteFiltro !== "todos" && l.piqueteAtualNome !== piqueteFiltro) {
        return false;
      }
      if (racaFiltro !== "todos" && l.raca !== racaFiltro) {
        return false;
      }
      return true;
    });
    const ordenados = [...filtrados];
    ordenados.sort((a, b) => {
      switch (ordenacao) {
        case "cabecas":
          return b.quantidadeTotal - a.quantidadeTotal;
        case "ua":
          return uaTotal(b) - uaTotal(a);
        case "dias":
          return a.dias - b.dias;
        default:
          return a.nome.localeCompare(b.nome, "pt-BR", { numeric: true });
      }
    });
    return ordenados;
  }, [lotes, busca, piqueteFiltro, racaFiltro, ordenacao]);

  function adicionarLote(valores: ValoresLote): void {
    setLotes((atual) => [{ id: gerarId("l"), dias: 0, ...valores }, ...atual]);
    setAdicionando(false);
  }

  function salvarEdicao(valores: ValoresLote): void {
    if (loteEditando === null) {
      return;
    }
    setLotes((atual) =>
      atual.map((l) => (l.id === loteEditando.id ? { ...l, ...valores } : l)),
    );
    setLoteEditando(null);
  }

  function salvarMovimentacao(novoPiquete: string): void {
    if (loteMovendo === null) {
      return;
    }
    setLotes((atual) =>
      atual.map((l) =>
        l.id === loteMovendo.id ? { ...l, piqueteAtualNome: novoPiquete, dias: 0 } : l,
      ),
    );
    setLoteMovendo(null);
  }

  function confirmarExclusao(): void {
    if (loteExcluindo === null) {
      return;
    }
    setLotes((atual) => atual.filter((l) => l.id !== loteExcluindo.id));
    setLoteExcluindo(null);
  }

  return (
    <div className="animais-pagina">
      <header className="animais-cabecalho-pagina">
        <div>
          <h1 className="animais-titulo-pagina">Animais</h1>
          <p className="animais-subtitulo-pagina">
            {totais.lotes} lotes • {totais.cabecas} cabeças •{" "}
            {totais.ua.toLocaleString("pt-BR", { maximumFractionDigits: 0 })} UA
          </p>
        </div>
        <div className="animais-cabecalho-acoes">
          <input
            type="search"
            placeholder="Buscar lote"
            className="filtro-busca"
            value={busca}
            onChange={(evento) => setBusca(evento.target.value)}
            aria-label="Buscar lote"
          />
          <button
            type="button"
            className="modal-botao modal-botao-primario"
            onClick={() => setAdicionando(true)}
          >
            + Adicionar lote
          </button>
        </div>
      </header>

      <div className="animais-filtros">
        <select
          className="filtro-select"
          value={piqueteFiltro}
          onChange={(evento) => setPiqueteFiltro(evento.target.value)}
          aria-label="Filtrar por piquete"
        >
          <option value="todos">Piquete: todos</option>
          {PIQUETES_PARA_LOTE.map((p) => (
            <option key={p.nome} value={p.nome}>
              Piquete: {p.nome}
            </option>
          ))}
        </select>
        <select
          className="filtro-select"
          value={racaFiltro}
          onChange={(evento) => setRacaFiltro(evento.target.value)}
          aria-label="Filtrar por raça"
        >
          <option value="todos">Raça: todas</option>
          {racas.map((r) => (
            <option key={r} value={r}>
              Raça: {r}
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
          <option value="cabecas">Ordenar: cabeças</option>
          <option value="ua">Ordenar: UA</option>
          <option value="dias">Ordenar: dias</option>
        </select>
      </div>

      <div className="piquetes-tabela-cartao">
        <div className="piquetes-tabela-wrap">
          <table className="piquetes-tabela">
            <thead>
              <tr>
                <th>Lote</th>
                <th>Piquete atual</th>
                <th>Cabeças</th>
                <th>Peso médio</th>
                <th>UA</th>
                <th>Dias</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {lotesVisiveis.length === 0 && (
                <tr>
                  <td colSpan={7} className="piquetes-tabela-vazia">
                    Nenhum lote encontrado para esse filtro.
                  </td>
                </tr>
              )}
              {lotesVisiveis.map((l) => (
                <tr key={l.id}>
                  <td>
                    <div className="lote-nome-celula">
                      <span className="piquetes-tabela-nome">{l.nome}</span>
                      <span className="lote-raca">{l.raca}</span>
                    </div>
                  </td>
                  <td>
                    <span className="lote-piquete-atual">{l.piqueteAtualNome}</span>
                  </td>
                  <td>{l.quantidadeTotal}</td>
                  <td>{l.pesoMedioKg} kg</td>
                  <td>{uaTotal(l).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}</td>
                  <td>{l.dias} dias</td>
                  <td>
                    <div className="tabela-acoes">
                      <button
                        type="button"
                        className="tabela-acao-botao"
                        aria-label="Editar lote"
                        onClick={() => setLoteEditando(l)}
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
                        aria-label="Mover lote"
                        onClick={() => setLoteMovendo(l)}
                      >
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
                          <path
                            d="M4 12h16m0 0-5-5m5 5-5 5"
                            stroke="currentColor"
                            strokeWidth="1.6"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </button>
                      <button
                        type="button"
                        className="tabela-acao-botao"
                        aria-label="Excluir lote"
                        onClick={() => setLoteExcluindo(l)}
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
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {adicionando && (
        <FormularioLote
          titulo="Adicionar lote"
          subtitulo="O lote é a unidade do sistema. Não há cadastro por animal."
          textoSalvar="Salvar lote"
          valoresIniciais={{
            nome: "",
            raca: RACAS_DISPONIVEIS[0],
            piqueteAtualNome: PIQUETES_PARA_LOTE[0].nome,
            quantidadeTotal: 0,
            pesoMedioKg: 0,
          }}
          onSalvar={adicionarLote}
          onFechar={() => setAdicionando(false)}
        />
      )}
      {loteEditando && (
        <FormularioLote
          key={loteEditando.id}
          titulo={`Editar ${loteEditando.nome}`}
          subtitulo="O lote é a unidade do sistema. Não há cadastro por animal."
          textoSalvar="Salvar alterações"
          valoresIniciais={{
            nome: loteEditando.nome,
            raca: loteEditando.raca,
            piqueteAtualNome: loteEditando.piqueteAtualNome,
            quantidadeTotal: loteEditando.quantidadeTotal,
            pesoMedioKg: loteEditando.pesoMedioKg,
          }}
          onSalvar={salvarEdicao}
          onFechar={() => setLoteEditando(null)}
        />
      )}
      {loteMovendo && (
        <ModalMoverLote
          lote={loteMovendo}
          onSalvar={salvarMovimentacao}
          onFechar={() => setLoteMovendo(null)}
        />
      )}
      {loteExcluindo && (
        <ModalExcluirLote
          lote={loteExcluindo}
          onConfirmar={confirmarExclusao}
          onFechar={() => setLoteExcluindo(null)}
        />
      )}
    </div>
  );
}
