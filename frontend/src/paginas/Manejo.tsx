import { useMemo, useState, type FormEvent, type ReactNode } from "react";

type TipoManejo = "movimentacao" | "baixa" | "ajuste_manual" | "entrada_animais";
type Canal = "telegram" | "app" | "automatico";

interface ManejoPendente {
  id: string;
  loteNome: string;
  piqueteOrigemNome: string;
  piqueteDestinoNome: string;
  motivo: string;
  sugeridoEm: string;
}

interface RegistroHistorico {
  id: string;
  data: string;
  tipo: TipoManejo;
  loteNome: string | null;
  origemNome: string | null;
  destinoNome: string | null;
  por: string;
  canal: Canal;
  observacao: string;
}

const HOJE_ISO = "2026-09-28";

function formatarData(iso: string): string {
  const [, mes, dia] = iso.split("-");
  return `${dia}/${mes}`;
}

function somarDias(iso: string, dias: number): string {
  const data = new Date(`${iso}T00:00:00`);
  data.setDate(data.getDate() + dias);
  return data.toISOString().slice(0, 10);
}

const PIQUETES_DISPONIVEIS = [
  "Piquete 1",
  "Piquete 2",
  "Piquete 3",
  "Piquete 4",
  "Piquete 5",
  "Piquete 6",
  "Piquete 7",
  "Piquete 8",
];

const PENDENTES_INICIAIS: ManejoPendente[] = [
  {
    id: "p1",
    loteNome: "Recria",
    piqueteOrigemNome: "Piquete 3",
    piqueteDestinoNome: "Piquete 7",
    motivo: "Sugerido em 25/09 · Piquete 3 está em 12 cm, abaixo da altura de saída de 15 cm",
    sugeridoEm: "25/09",
  },
];

const HISTORICO_INICIAL: RegistroHistorico[] = [
  {
    id: "h1",
    data: "2026-09-26",
    tipo: "movimentacao",
    loteNome: "Engorda A",
    origemNome: "Piquete 8",
    destinoNome: "Piquete 2",
    por: "Zé Carlos",
    canal: "telegram",
    observacao: "Confirmado às 14:20",
  },
  {
    id: "h3",
    data: "2026-09-22",
    tipo: "baixa",
    loteNome: "Engorda A",
    origemNome: null,
    destinoNome: null,
    por: "Leandro M.",
    canal: "app",
    observacao: "Venda de 18 bois",
  },
  {
    id: "h4",
    data: "2026-09-19",
    tipo: "movimentacao",
    loteNome: "Cria",
    origemNome: "Piquete 4",
    destinoNome: "Piquete 6",
    por: "Zé Carlos",
    canal: "telegram",
    observacao: "",
  },
  {
    id: "h5",
    data: "2026-09-17",
    tipo: "ajuste_manual",
    loteNome: "Recria",
    origemNome: "Piquete 3",
    destinoNome: null,
    por: "Leandro M.",
    canal: "app",
    observacao: "Correção de contagem",
  },
  {
    id: "h6",
    data: "2026-09-14",
    tipo: "entrada_animais",
    loteNome: "Reposição",
    origemNome: null,
    destinoNome: "Piquete 6",
    por: "Leandro M.",
    canal: "app",
    observacao: "18 novilhas Angus",
  },
  {
    id: "h7",
    data: "2026-09-12",
    tipo: "movimentacao",
    loteNome: "Engorda B",
    origemNome: "Piquete 1",
    destinoNome: "Piquete 5",
    por: "Sistema",
    canal: "automatico",
    observacao: "Sem resposta em 48 h",
  },
  {
    id: "h9",
    data: "2026-09-05",
    tipo: "movimentacao",
    loteNome: "Recria",
    origemNome: "Piquete 7",
    destinoNome: "Piquete 3",
    por: "Zé Carlos",
    canal: "telegram",
    observacao: "",
  },
];

const TIPO_ROTULO: Record<TipoManejo, string> = {
  movimentacao: "Movimentação",
  baixa: "Baixa",
  ajuste_manual: "Ajuste manual",
  entrada_animais: "Entrada de animais",
};

const TIPO_CLASSE: Record<TipoManejo, string> = {
  movimentacao: "tipo-badge-ok",
  baixa: "tipo-badge-erro",
  ajuste_manual: "tipo-badge-atencao",
  entrada_animais: "tipo-badge-ocupado",
};

const CANAL_ROTULO: Record<Canal, string> = {
  telegram: "Telegram",
  app: "App",
  automatico: "Automático",
};

function origemDestino(r: { origemNome: string | null; destinoNome: string | null }): string {
  if (r.origemNome !== null && r.destinoNome !== null) {
    return `${r.origemNome} → ${r.destinoNome}`;
  }
  if (r.destinoNome !== null) {
    return `→ ${r.destinoNome}`;
  }
  return "—";
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

function ModalAlterarDestino({
  pendente,
  onSalvar,
  onFechar,
}: {
  pendente: ManejoPendente;
  onSalvar: (novoDestino: string) => void;
  onFechar: () => void;
}) {
  const [destino, setDestino] = useState(pendente.piqueteDestinoNome);
  const opcoes = PIQUETES_DISPONIVEIS.filter((nome) => nome !== pendente.piqueteOrigemNome);

  function handleSubmit(evento: FormEvent<HTMLFormElement>): void {
    evento.preventDefault();
    onSalvar(destino);
  }

  return (
    <Modal titulo={`Alterar destino — ${pendente.loteNome}`} onFechar={onFechar}>
      <form className="modal-formulario" onSubmit={handleSubmit}>
        <p className="modal-texto">
          Origem: <strong>{pendente.piqueteOrigemNome}</strong>
        </p>
        <label className="modal-campo">
          <span>Novo destino</span>
          <select
            className="modal-input"
            value={destino}
            onChange={(evento) => setDestino(evento.target.value)}
          >
            {opcoes.map((nome) => (
              <option key={nome} value={nome}>
                {nome}
              </option>
            ))}
          </select>
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

function ModalEditarRegistro({
  registro,
  onSalvar,
  onFechar,
}: {
  registro: RegistroHistorico;
  onSalvar: (editado: RegistroHistorico) => void;
  onFechar: () => void;
}) {
  const [tipo, setTipo] = useState<TipoManejo>(registro.tipo);
  const [canal, setCanal] = useState<Canal>(registro.canal);
  const [observacao, setObservacao] = useState(registro.observacao);

  function handleSubmit(evento: FormEvent<HTMLFormElement>): void {
    evento.preventDefault();
    onSalvar({ ...registro, tipo, canal, observacao: observacao.trim() });
  }

  return (
    <Modal titulo="Editar registro" onFechar={onFechar}>
      <form className="modal-formulario" onSubmit={handleSubmit}>
        <label className="modal-campo">
          <span>Tipo</span>
          <select
            className="modal-input"
            value={tipo}
            onChange={(evento) => setTipo(evento.target.value as TipoManejo)}
          >
            {Object.entries(TIPO_ROTULO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </label>
        <label className="modal-campo">
          <span>Canal</span>
          <select
            className="modal-input"
            value={canal}
            onChange={(evento) => setCanal(evento.target.value as Canal)}
          >
            {Object.entries(CANAL_ROTULO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </label>
        <label className="modal-campo">
          <span>Observação</span>
          <input
            className="modal-input"
            value={observacao}
            onChange={(evento) => setObservacao(evento.target.value)}
            placeholder="Nenhuma"
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

function ModalExcluirRegistro({
  registro,
  onConfirmar,
  onFechar,
}: {
  registro: RegistroHistorico;
  onConfirmar: () => void;
  onFechar: () => void;
}) {
  return (
    <Modal titulo="Excluir registro" onFechar={onFechar}>
      <p className="modal-texto">
        Tem certeza que deseja excluir o registro de <strong>{TIPO_ROTULO[registro.tipo]}</strong>{" "}
        de {formatarData(registro.data)}? Essa ação não pode ser desfeita.
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

function ModalRegistrar({
  onSalvar,
  onFechar,
}: {
  onSalvar: (item: Omit<RegistroHistorico, "id">) => void;
  onFechar: () => void;
}) {
  const [data, setData] = useState(HOJE_ISO);
  const [tipo, setTipo] = useState<TipoManejo>("movimentacao");
  const [loteNome, setLoteNome] = useState("");
  const [origemNome, setOrigemNome] = useState("");
  const [destinoNome, setDestinoNome] = useState("");
  const [canal, setCanal] = useState<Canal>("app");
  const [observacao, setObservacao] = useState("");

  function handleSubmit(evento: FormEvent<HTMLFormElement>): void {
    evento.preventDefault();
    onSalvar({
      data,
      tipo,
      loteNome: loteNome.trim() === "" ? null : loteNome.trim(),
      origemNome: origemNome === "" ? null : origemNome,
      destinoNome: destinoNome === "" ? null : destinoNome,
      por: "Você",
      canal,
      observacao: observacao.trim(),
    });
  }

  return (
    <Modal titulo="Registrar manejo" onFechar={onFechar}>
      <form className="modal-formulario" onSubmit={handleSubmit}>
        <label className="modal-campo">
          <span>Data</span>
          <input
            className="modal-input"
            type="date"
            value={data}
            onChange={(evento) => setData(evento.target.value)}
          />
        </label>
        <label className="modal-campo">
          <span>Tipo</span>
          <select
            className="modal-input"
            value={tipo}
            onChange={(evento) => setTipo(evento.target.value as TipoManejo)}
          >
            {Object.entries(TIPO_ROTULO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </label>
        <label className="modal-campo">
          <span>Lote</span>
          <input
            className="modal-input"
            value={loteNome}
            onChange={(evento) => setLoteNome(evento.target.value)}
            placeholder="Nenhum"
          />
        </label>
        <label className="modal-campo">
          <span>Origem</span>
          <select
            className="modal-input"
            value={origemNome}
            onChange={(evento) => setOrigemNome(evento.target.value)}
          >
            <option value="">Nenhuma</option>
            {PIQUETES_DISPONIVEIS.map((nome) => (
              <option key={nome} value={nome}>
                {nome}
              </option>
            ))}
          </select>
        </label>
        <label className="modal-campo">
          <span>Destino</span>
          <select
            className="modal-input"
            value={destinoNome}
            onChange={(evento) => setDestinoNome(evento.target.value)}
          >
            <option value="">Nenhum</option>
            {PIQUETES_DISPONIVEIS.map((nome) => (
              <option key={nome} value={nome}>
                {nome}
              </option>
            ))}
          </select>
        </label>
        <label className="modal-campo">
          <span>Canal</span>
          <select
            className="modal-input"
            value={canal}
            onChange={(evento) => setCanal(evento.target.value as Canal)}
          >
            {Object.entries(CANAL_ROTULO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </label>
        <label className="modal-campo">
          <span>Observação</span>
          <input
            className="modal-input"
            value={observacao}
            onChange={(evento) => setObservacao(evento.target.value)}
            placeholder="Nenhuma"
          />
        </label>
        <div className="modal-acoes">
          <button type="button" className="modal-botao modal-botao-secundario" onClick={onFechar}>
            Cancelar
          </button>
          <button type="submit" className="modal-botao modal-botao-primario">
            Registrar
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default function Manejos() {
  const [pendentes, setPendentes] = useState(PENDENTES_INICIAIS);
  const [historico, setHistorico] = useState(HISTORICO_INICIAL);
  const [tipoFiltro, setTipoFiltro] = useState<"todos" | TipoManejo>("todos");
  const [loteFiltro, setLoteFiltro] = useState("todos");
  const [canalFiltro, setCanalFiltro] = useState<"todos" | Canal>("todos");
  const [dataInicio, setDataInicio] = useState(somarDias(HOJE_ISO, -6));
  const [dataFim, setDataFim] = useState(HOJE_ISO);
  const [pendenteAlterando, setPendenteAlterando] = useState<ManejoPendente | null>(null);
  const [registroEditando, setRegistroEditando] = useState<RegistroHistorico | null>(null);
  const [registroExcluindo, setRegistroExcluindo] = useState<RegistroHistorico | null>(null);
  const [registrando, setRegistrando] = useState(false);

  const lotes = useMemo(
    () =>
      Array.from(
        new Set(historico.map((r) => r.loteNome).filter((l): l is string => l !== null)),
      ).sort(),
    [historico],
  );

  const historicoVisivel = useMemo(
    () =>
      historico.filter((r) => {
        if (r.data < dataInicio || r.data > dataFim) {
          return false;
        }
        if (tipoFiltro !== "todos" && r.tipo !== tipoFiltro) {
          return false;
        }
        if (loteFiltro !== "todos" && r.loteNome !== loteFiltro) {
          return false;
        }
        if (canalFiltro !== "todos" && r.canal !== canalFiltro) {
          return false;
        }
        return true;
      }),
    [historico, dataInicio, dataFim, tipoFiltro, loteFiltro, canalFiltro],
  );

  function registrar(item: Omit<RegistroHistorico, "id">): void {
    setHistorico((atual) => [{ ...item, id: `h${Date.now()}` }, ...atual]);
  }

  function confirmarPendente(pendente: ManejoPendente): void {
    setPendentes((atual) => atual.filter((p) => p.id !== pendente.id));
    registrar({
      data: HOJE_ISO,
      tipo: "movimentacao",
      loteNome: pendente.loteNome,
      origemNome: pendente.piqueteOrigemNome,
      destinoNome: pendente.piqueteDestinoNome,
      por: "Você",
      canal: "app",
      observacao: "Confirmado manualmente",
    });
  }

  function recusarPendente(pendente: ManejoPendente): void {
    setPendentes((atual) => atual.filter((p) => p.id !== pendente.id));
    registrar({
      data: HOJE_ISO,
      tipo: "ajuste_manual",
      loteNome: pendente.loteNome,
      origemNome: null,
      destinoNome: null,
      por: "Você",
      canal: "app",
      observacao: `Sugestão recusada (${pendente.piqueteOrigemNome} → ${pendente.piqueteDestinoNome})`,
    });
  }

  function salvarDestino(novoDestino: string): void {
    if (pendenteAlterando === null) {
      return;
    }
    setPendentes((atual) =>
      atual.map((p) =>
        p.id === pendenteAlterando.id ? { ...p, piqueteDestinoNome: novoDestino } : p,
      ),
    );
    setPendenteAlterando(null);
  }

  function salvarEdicaoRegistro(editado: RegistroHistorico): void {
    setHistorico((atual) => atual.map((r) => (r.id === editado.id ? editado : r)));
    setRegistroEditando(null);
  }

  function confirmarExclusaoRegistro(): void {
    if (registroExcluindo === null) {
      return;
    }
    setHistorico((atual) => atual.filter((r) => r.id !== registroExcluindo.id));
    setRegistroExcluindo(null);
  }

  function registrarNovo(item: Omit<RegistroHistorico, "id">): void {
    registrar(item);
    setRegistrando(false);
  }

  return (
    <div className="manejos-pagina">
      <header className="manejos-cabecalho-pagina">
        <div>
          <h1 className="manejos-titulo-pagina">Manejos</h1>
          <p className="manejos-subtitulo-pagina">
            {pendentes.length} pendente{pendentes.length === 1 ? "" : "s"} •{" "}
            {historicoVisivel.length} registros no período
          </p>
        </div>
        <button
          type="button"
          className="modal-botao modal-botao-primario"
          onClick={() => setRegistrando(true)}
        >
          + Registrar manejo
        </button>
      </header>

      {pendentes.length > 0 && (
        <div className="manejos-pendentes-lista">
          {pendentes.map((p) => (
            <div key={p.id} className="pendente-cartao">
              <span className="pendente-icone" aria-hidden="true">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
                  <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
                  <path
                    d="M12 7v5l3.5 2"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                  />
                </svg>
              </span>
              <div className="pendente-texto">
                <p className="pendente-titulo-linha">
                  <strong>Lote {p.loteNome}</strong> {p.piqueteOrigemNome} → {p.piqueteDestinoNome}
                </p>
                <p className="pendente-motivo">{p.motivo}</p>
              </div>
              <div className="pendente-acoes">
                <button
                  type="button"
                  className="modal-botao modal-botao-secundario"
                  onClick={() => setPendenteAlterando(p)}
                >
                  Alterar destino
                </button>
                <button
                  type="button"
                  className="modal-botao modal-botao-secundario"
                  onClick={() => recusarPendente(p)}
                >
                  Recusar
                </button>
                <button
                  type="button"
                  className="modal-botao modal-botao-primario"
                  onClick={() => confirmarPendente(p)}
                >
                  Confirmar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="manejos-filtros">
        <select
          className="filtro-select"
          value={tipoFiltro}
          onChange={(evento) => setTipoFiltro(evento.target.value as "todos" | TipoManejo)}
          aria-label="Filtrar por tipo"
        >
          <option value="todos">Tipo: todos</option>
          {Object.entries(TIPO_ROTULO).map(([valor, rotulo]) => (
            <option key={valor} value={valor}>
              Tipo: {rotulo}
            </option>
          ))}
        </select>
        <select
          className="filtro-select"
          value={loteFiltro}
          onChange={(evento) => setLoteFiltro(evento.target.value)}
          aria-label="Filtrar por lote"
        >
          <option value="todos">Lote: todos</option>
          {lotes.map((lote) => (
            <option key={lote} value={lote}>
              Lote: {lote}
            </option>
          ))}
        </select>
        <select
          className="filtro-select"
          value={canalFiltro}
          onChange={(evento) => setCanalFiltro(evento.target.value as "todos" | Canal)}
          aria-label="Filtrar por canal"
        >
          <option value="todos">Canal: todos</option>
          {Object.entries(CANAL_ROTULO).map(([valor, rotulo]) => (
            <option key={valor} value={valor}>
              Canal: {rotulo}
            </option>
          ))}
        </select>
        <div className="manejos-periodo">
          <input
            className="filtro-select"
            type="date"
            value={dataInicio}
            onChange={(evento) => setDataInicio(evento.target.value)}
            aria-label="Data inicial"
          />
          <span>–</span>
          <input
            className="filtro-select"
            type="date"
            value={dataFim}
            onChange={(evento) => setDataFim(evento.target.value)}
            aria-label="Data final"
          />
        </div>
      </div>

      <div className="piquetes-tabela-cartao">
        <div className="piquetes-tabela-wrap">
          <table className="piquetes-tabela">
            <thead>
              <tr>
                <th>Data</th>
                <th>Tipo</th>
                <th>Lote</th>
                <th>Origem → Destino</th>
                <th>Por</th>
                <th>Canal</th>
                <th>Observação</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {historicoVisivel.length === 0 && (
                <tr>
                  <td colSpan={8} className="piquetes-tabela-vazia">
                    Nenhum registro encontrado para esse filtro.
                  </td>
                </tr>
              )}
              {historicoVisivel.map((r) => (
                <tr key={r.id}>
                  <td>{formatarData(r.data)}</td>
                  <td>
                    <span className={`tipo-badge ${TIPO_CLASSE[r.tipo]}`}>
                      {TIPO_ROTULO[r.tipo]}
                    </span>
                  </td>
                  <td>{r.loteNome ?? "—"}</td>
                  <td>{origemDestino(r)}</td>
                  <td>{r.por}</td>
                  <td>
                    <span className="canal-badge">{CANAL_ROTULO[r.canal]}</span>
                  </td>
                  <td>{r.observacao === "" ? "—" : r.observacao}</td>
                  <td>
                    <div className="tabela-acoes">
                      <button
                        type="button"
                        className="tabela-acao-botao"
                        aria-label="Editar registro"
                        onClick={() => setRegistroEditando(r)}
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
                        aria-label="Excluir registro"
                        onClick={() => setRegistroExcluindo(r)}
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

      {pendenteAlterando && (
        <ModalAlterarDestino
          pendente={pendenteAlterando}
          onSalvar={salvarDestino}
          onFechar={() => setPendenteAlterando(null)}
        />
      )}
      {registroEditando && (
        <ModalEditarRegistro
          key={registroEditando.id}
          registro={registroEditando}
          onSalvar={salvarEdicaoRegistro}
          onFechar={() => setRegistroEditando(null)}
        />
      )}
      {registroExcluindo && (
        <ModalExcluirRegistro
          registro={registroExcluindo}
          onConfirmar={confirmarExclusaoRegistro}
          onFechar={() => setRegistroExcluindo(null)}
        />
      )}
      {registrando && (
        <ModalRegistrar onSalvar={registrarNovo} onFechar={() => setRegistrando(false)} />
      )}
    </div>
  );
}
