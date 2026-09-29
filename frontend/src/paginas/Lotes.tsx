import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { api } from "../lib/api";
import { useFazenda } from "../lib/fazenda";
import type { Categoria, ComposicaoItem, Fazenda, Lote, Piquete } from "../lib/tipos";
import { mensagemDeErro } from "../componentes/ui/erros";
import { dataCurta, hojeNaFazenda, piquetesDisponiveis, pesoParaEdicao } from "./dadosManejo";
import "./Lotes.css";

const CATEGORIAS: Categoria[] = ["bezerro", "bezerra", "novilho", "novilha", "vaca", "boi", "touro"];
type LinhaComposicao = Pick<ComposicaoItem, "categoria"> & { quantidade: string; peso: string };

function FormularioLote({ fazenda, piquetes, lote, aoSalvar, aoCancelar }: {
  fazenda: Fazenda; piquetes: Piquete[]; lote: Lote | null;
  aoSalvar: () => void; aoCancelar: () => void;
}) {
  const [nome, setNome] = useState(lote?.nome ?? "");
  const [composicao, setComposicao] = useState<LinhaComposicao[]>(() => lote
    ? lote.composicao.map(item => ({ categoria: item.categoria, quantidade: String(item.n_animais), peso: pesoParaEdicao(item) }))
    : [{ categoria: "bezerro", quantidade: "", peso: "" }]);
  const [piqueteId, setPiqueteId] = useState(lote?.piquete_atual_id ?? "");
  const [desde, setDesde] = useState(lote?.desde ?? hojeNaFazenda(fazenda.timezone));
  const [indissoluvel, setIndissoluvel] = useState(lote?.indissoluvel ?? false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const disponiveis = piquetesDisponiveis(piquetes, lote);

  function alterarLinha(indice: number, dados: Partial<LinhaComposicao>) {
    setComposicao(atual => atual.map((item, i) => i === indice ? { ...item, ...dados } : item));
  }

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (enviando) return;
    setErro(null);
    if (!nome.trim()) { setErro("Informe o nome do lote."); return; }
    setEnviando(true);
    const itens: ComposicaoItem[] = composicao.map(item => ({
      categoria: item.categoria, n_animais: Number(item.quantidade),
      peso_medio_kg: item.peso.trim() === "" ? null : Number(item.peso),
    }));
    try {
      await api<Lote>(`/fazendas/${fazenda.id}/lotes${lote ? `/${lote.id}` : ""}`, {
        method: lote ? "PUT" : "POST",
        body: JSON.stringify({ nome: nome.trim(), indissoluvel, composicao: itens, piquete_atual_id: piqueteId, desde: desde || null }),
      });
      aoSalvar();
    } catch (falha) { setErro(mensagemDeErro(falha)); }
    finally { setEnviando(false); }
  }

  return (
    <form className="cartao formulario lotes-formulario" onSubmit={salvar}>
      <div>
        <h2 className="cartao-titulo">{lote ? "Editar lote" : "Novo lote"}</h2>
        <p className="cartao-subtitulo">O lote é a unidade de manejo. Não há cadastro por animal.</p>
      </div>
      <fieldset disabled={enviando} className="lotes-campos formulario">
        <label className="campo">Nome
          <input className="campo-entrada" value={nome} onChange={e => setNome(e.target.value)} required autoFocus />
        </label>
        <fieldset className="lotes-campos">
          <legend className="lotes-legenda">Composição</legend>
          <p className="campo-dica" id="lotes-dica-peso">Sem peso? Deixe em branco: estimamos pela tabela de Unidade Animal</p>
          <div className="lotes-composicao">
            {composicao.map((item, indice) => (
              <div className="lotes-linha" key={indice}>
                <label className="campo">Categoria
                  <select className="campo-entrada" value={item.categoria} onChange={e => alterarLinha(indice, { categoria: e.target.value as Categoria })}>
                    {CATEGORIAS.filter(c => c === item.categoria || !composicao.some(linha => linha.categoria === c)).map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </label>
                <label className="campo">Quantidade
                  <input className="campo-entrada" type="number" min={1} step={1} required value={item.quantidade} onChange={e => alterarLinha(indice, { quantidade: e.target.value })} />
                </label>
                <label className="campo">Peso médio (kg), opcional
                  <input className="campo-entrada" type="number" min={20} max={1500} step="any" aria-describedby="lotes-dica-peso" value={item.peso} onChange={e => alterarLinha(indice, { peso: e.target.value })} />
                </label>
                <button type="button" className="botao botao-secundario" disabled={composicao.length === 1} aria-label={`Remover categoria ${item.categoria}`} onClick={() => setComposicao(atual => atual.filter((_, i) => i !== indice))}>Remover</button>
              </div>
            ))}
          </div>
          <button type="button" className="botao botao-secundario lotes-adicionar" disabled={composicao.length === CATEGORIAS.length} onClick={() => {
            const categoria = CATEGORIAS.find(c => !composicao.some(item => item.categoria === c));
            if (categoria) setComposicao(atual => [...atual, { categoria, quantidade: "", peso: "" }]);
          }}>+ categoria</button>
        </fieldset>
        <div className="lotes-localizacao">
          <label className="campo">Onde o lote está agora
            <select className="campo-entrada" value={piqueteId} required onChange={e => setPiqueteId(e.target.value)}>
              <option value="">Selecione um piquete</option>
              {disponiveis.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}
            </select>
          </label>
          <label className="campo">Desde
            <input className="campo-entrada" type="date" value={desde} max={hojeNaFazenda(fazenda.timezone)} onChange={e => setDesde(e.target.value)} />
          </label>
        </div>
        {disponiveis.length === 0 ? <p className="aviso-alerta">Não há piquetes livres para este lote.</p> : null}
        <label className="lotes-checkbox">
          <input type="checkbox" checked={indissoluvel} onChange={e => setIndissoluvel(e.target.checked)} />
          <span>Lote indissolúvel<small className="campo-dica">Não pode ser juntado a outro lote, como vacas com bezerros ao pé.</small></span>
        </label>
      </fieldset>
      {erro ? <p className="aviso-erro" role="alert">{erro}</p> : null}
      <div className="lotes-acoes">
        <button className="botao botao-primario" type="submit" disabled={enviando || disponiveis.length === 0}>{enviando ? "Salvando…" : "Salvar lote"}</button>
        <button className="botao botao-secundario" type="button" disabled={enviando} onClick={aoCancelar}>Cancelar</button>
      </div>
    </form>
  );
}

function LotesDaFazenda({ fazenda }: { fazenda: Fazenda }) {
  const [lotes, setLotes] = useState<Lote[]>([]);
  const [piquetes, setPiquetes] = useState<Piquete[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [recarga, setRecarga] = useState(0);
  const [editor, setEditor] = useState<Lote | "novo" | null>(null);
  const [confirmacao, setConfirmacao] = useState<string | null>(null);
  const [dissolvendo, setDissolvendo] = useState(false);

  useEffect(() => {
    let cancelado = false;
    Promise.all([api<Lote[]>(`/fazendas/${fazenda.id}/lotes`), api<Piquete[]>(`/fazendas/${fazenda.id}/piquetes`)])
      .then(([lista, pastos]) => { if (!cancelado) { setLotes(lista); setPiquetes(pastos); setErro(null); } })
      .catch(falha => { if (!cancelado) setErro(mensagemDeErro(falha)); })
      .finally(() => { if (!cancelado) setCarregando(false); });
    return () => { cancelado = true; };
  }, [fazenda.id, recarga]);

  function recarregar() { setCarregando(true); setRecarga(n => n + 1); }

  async function dissolver(id: string) {
    if (dissolvendo) return;
    setDissolvendo(true);
    setErro(null);
    try {
      await api<void>(`/fazendas/${fazenda.id}/lotes/${id}`, { method: "DELETE" });
      setConfirmacao(null);
      recarregar();
    } catch (falha) { setErro(mensagemDeErro(falha)); }
    finally { setDissolvendo(false); }
  }

  return (
    <div className="pagina lotes-pagina">
      <div className="pagina-cabecalho">
        <div><h1 className="pagina-titulo">Lotes</h1><p className="cartao-subtitulo">{fazenda.nome} · composição e localização do gado</p></div>
        {editor === null ? <button className="botao botao-primario" disabled={carregando || erro !== null || piquetes.length === 0 || dissolvendo} onClick={() => { setEditor("novo"); setConfirmacao(null); }}>+ Novo lote</button> : null}
      </div>
      {erro ? <div className="aviso-erro" role="alert">{erro} <button className="botao botao-secundario" disabled={carregando || dissolvendo} onClick={recarregar}>Tentar novamente</button></div> : null}
      {carregando ? <p role="status">Carregando lotes e piquetes…</p> : null}
      {!carregando && !erro && piquetes.length === 0 ? <p className="aviso-info">Cadastre os piquetes no Mapa antes dos lotes. <Link to="/mapa">Abrir Mapa</Link></p> : null}
      {editor !== null ? <FormularioLote key={editor === "novo" ? "novo" : editor.id} fazenda={fazenda} piquetes={piquetes} lote={editor === "novo" ? null : editor} aoCancelar={() => setEditor(null)} aoSalvar={() => { setEditor(null); recarregar(); }} /> : null}
      {!carregando && !erro && lotes.length === 0 && piquetes.length > 0 ? <p className="cartao cartao-subtitulo">Nenhum lote cadastrado. Crie um lote para informar sua composição e onde ele está.</p> : null}
      <div className="lotes-lista" aria-busy={carregando}>
        {lotes.map(lote => (
          <article className="cartao lotes-cartao" key={lote.id}>
            <div>
              <h2 className="cartao-titulo">{lote.nome}</h2>
              <p className="lotes-resumo">{lote.n_animais_total.toLocaleString("pt-BR")} animais · {lote.piquete_atual_nome ?? "Sem piquete"}{lote.desde ? ` desde ${dataCurta(lote.desde)}` : ""} · {(lote.peso_vivo_total_kg / 1000).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} t de peso vivo</p>
              <p className="cartao-subtitulo">{lote.composicao.map(item => `${item.n_animais} × ${item.categoria}`).join(" · ")}</p>
              {lote.indissoluvel ? <span className="selo selo-media">Indissolúvel</span> : null}
            </div>
            <div className="lotes-acoes">
              {confirmacao === lote.id ? <>
                <p>Dissolver o lote “{lote.nome}”?</p>
                <button className="botao lotes-perigo" disabled={dissolvendo || carregando} onClick={() => void dissolver(lote.id)}>{dissolvendo ? "Dissolvendo…" : "Confirmar dissolução"}</button>
                <button className="botao botao-secundario" disabled={dissolvendo} onClick={() => setConfirmacao(null)}>Cancelar</button>
              </> : <>
                <button className="botao botao-secundario" disabled={carregando || dissolvendo || editor !== null} onClick={() => { setEditor(lote); setConfirmacao(null); }}>Editar</button>
                <button className="botao botao-secundario lotes-dissolver" disabled={carregando || dissolvendo || editor !== null} onClick={() => setConfirmacao(lote.id)}>Dissolver</button>
              </>}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export default function Lotes() {
  const { fazenda } = useFazenda();
  return fazenda ? <LotesDaFazenda key={fazenda.id} fazenda={fazenda} /> : null;
}
