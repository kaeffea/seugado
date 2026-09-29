import { useEffect, useState, type FormEvent } from "react";
import { api, ErroApi } from "../lib/api";
import { useFazenda } from "../lib/fazenda";
import type { Confianca, Fazenda, PedidoValidacao, PlanoManejo } from "../lib/tipos";
import { mensagemDeErro } from "../componentes/ui/erros";
import { dataComDia, fimDoPlano, hojeNaFazenda, movimentosPorDia } from "./dadosManejo";
import "./Plano.css";

const CONFIANCA: Record<Confianca, string> = { alta: "alta", media: "média", baixa: "baixa" };
const ICONES_ALERTA: Record<string, string> = {
  sem_piquete_apto: "⊘", capacidade_excedida: "⇈", aguardando_parametro: "⚙",
  estimativa_indisponivel: "?", continuo_acima_maxima: "↑", continuo_abaixo_minima: "↓",
  lote_sem_piquete: "⌖", sem_dia_de_manejo: "▦", passando_do_ponto: "◷",
};

function Medicao({ pedido, fazenda, bloqueado, aoOcupar }: {
  pedido: PedidoValidacao; fazenda: Fazenda; bloqueado: boolean; aoOcupar: (ocupado: boolean) => void;
}) {
  const [altura, setAltura] = useState("");
  const [data, setData] = useState(() => hojeNaFazenda(fazenda.timezone));
  const [enviando, setEnviando] = useState(false);
  const [salvo, setSalvo] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function registrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (bloqueado || enviando || salvo) return;
    setEnviando(true);
    aoOcupar(true);
    setErro(null);
    try {
      await api<void>(`/fazendas/${fazenda.id}/piquetes/${pedido.piquete_id}/alturas`, {
        method: "POST", body: JSON.stringify({ altura_cm: Number(altura), data }),
      });
      setSalvo(true);
    } catch (falha) { setErro(mensagemDeErro(falha)); }
    finally { setEnviando(false); aoOcupar(false); }
  }

  return (
    <form className="cartao plano-medicao" onSubmit={registrar}>
      <h3 className="cartao-titulo">{pedido.piquete_nome}</h3>
      <p>{pedido.motivo}</p>
      {salvo ? <p className="aviso-info" role="status">Medição registrada. Gere um novo plano para considerar esta medida.</p> : (
        <div className="plano-medicao-campos">
          <label className="campo">Altura (cm)
            <input className="campo-entrada" type="number" min={0.1} max={400} step="any" required value={altura} onChange={e => setAltura(e.target.value)} disabled={bloqueado || enviando} />
          </label>
          <label className="campo">Data da medição
            <input className="campo-entrada" type="date" required max={hojeNaFazenda(fazenda.timezone)} value={data} onChange={e => setData(e.target.value)} disabled={bloqueado || enviando} />
          </label>
          <button className="botao botao-primario" disabled={bloqueado || enviando} type="submit">{enviando ? "Salvando…" : "Registrar medição"}</button>
        </div>
      )}
      {erro ? <p className="aviso-erro" role="alert">{erro}</p> : null}
    </form>
  );
}

function PlanoDaFazenda({ fazenda }: { fazenda: Fazenda }) {
  const [plano, setPlano] = useState<PlanoManejo | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [semPlano, setSemPlano] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [gerando, setGerando] = useState(false);
  const [enviar, setEnviar] = useState(true);
  const [medindo, setMedindo] = useState(false);
  const [recarga, setRecarga] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api<PlanoManejo>(`/fazendas/${fazenda.id}/plano/atual`)
      .then(dados => { if (!cancelado) { setPlano(dados); setSemPlano(false); setErro(null); } })
      .catch(falha => {
        if (cancelado) return;
        if (falha instanceof ErroApi && falha.status === 404) { setPlano(null); setSemPlano(true); setErro(null); }
        else setErro(mensagemDeErro(falha));
      })
      .finally(() => { if (!cancelado) setCarregando(false); });
    return () => { cancelado = true; };
  }, [fazenda.id, recarga]);

  async function gerar() {
    if (gerando || carregando || medindo) return;
    setGerando(true);
    setErro(null);
    try {
      const novo = await api<PlanoManejo>(`/fazendas/${fazenda.id}/ciclo`, {
        method: "POST", body: JSON.stringify({ ingerir_satelite: true, enviar }),
      });
      setPlano(novo);
      setSemPlano(false);
    } catch (falha) { setErro(mensagemDeErro(falha)); }
    finally { setGerando(false); }
  }

  const grupos = plano ? movimentosPorDia(plano.movimentacoes) : [];
  const demonstracao = plano?.movimentacoes.some(m => m.motivo.startsWith("Plano de demonstração"));
  const geracao = plano ? new Date(plano.data_geracao) : null;

  return (
    <div className="pagina plano-pagina">
      <div className="pagina-cabecalho">
        <div>
          <h1 className="pagina-titulo">Plano da semana</h1>
          <p className="cartao-subtitulo">{fazenda.nome}</p>
        </div>
        <div className="plano-gerar">
          <button className="botao botao-primario" disabled={carregando || gerando || medindo} onClick={() => void gerar()}>
            {gerando ? <><span className="plano-spinner" aria-hidden="true" /> Buscando satélite e clima…</> : semPlano ? "Gerar o primeiro plano" : "Gerar e enviar plano agora"}
          </button>
          <label className="plano-checkbox"><input type="checkbox" checked={enviar} disabled={gerando || medindo} onChange={e => setEnviar(e.target.checked)} /> enviar ao produtor</label>
        </div>
      </div>
      {demonstracao ? <div className="aviso-alerta plano-demonstracao" role="note">Plano de demonstração — o otimizador definitivo ainda está em desenvolvimento.</div> : null}
      {plano && geracao ? <p className="plano-periodo">Plano de {dataComDia(plano.data_inicio)} a {dataComDia(fimDoPlano(plano))} · gerado em {geracao.toLocaleDateString("pt-BR", { timeZone: fazenda.timezone, day: "2-digit", month: "2-digit" })} às {geracao.toLocaleTimeString("pt-BR", { timeZone: fazenda.timezone, hour: "2-digit", minute: "2-digit" })}</p> : null}
      {gerando ? <p className="aviso-info" role="status">Buscando satélite e clima… Isso pode levar de 1 a 2 minutos.</p> : null}
      {erro ? <div className="aviso-erro" role="alert">{erro} <button className="botao botao-secundario" disabled={gerando || carregando || medindo} onClick={() => { setCarregando(true); setRecarga(n => n + 1); }}>Atualizar plano</button></div> : null}
      {carregando ? <p role="status">Carregando plano…</p> : null}
      {!carregando && semPlano ? <section className="cartao plano-vazio"><h2 className="cartao-titulo">Ainda não há plano para esta fazenda</h2><p className="cartao-subtitulo">Use “Gerar o primeiro plano” para buscar os dados e preparar os manejos.</p></section> : null}
      {plano ? <>
        <section className="plano-secao" aria-label="Movimentações por dia" aria-busy={gerando}>
          <h2 className="cartao-titulo">Manejos previstos</h2>
          {grupos.length === 0 ? <p className="cartao cartao-subtitulo">Nenhuma movimentação prevista neste plano.</p> : grupos.map(([data, movimentos]) => (
            <section className="plano-dia" key={data}>
              <h3 className="plano-dia-titulo">{dataComDia(data)}</h3>
              {movimentos.map(m => (
                <article className="cartao plano-movimento" key={m.id}>
                  <div className="plano-movimento-topo">
                    <h4 className="cartao-titulo">Mover {m.lote_nome}: {m.piquete_origem_nome ?? "Sem piquete de origem"} <span className="plano-seta">→</span> {m.piquete_destino_nome}</h4>
                    <span className={`selo selo-${m.confianca}`}>Confiança {CONFIANCA[m.confianca]}</span>
                  </div>
                  <p>{m.motivo}</p>
                  <p className="plano-previsao">Previsão: {m.dias_previstos} dias no piquete</p>
                  <p className="cartao-subtitulo">{m.motivo_confianca}</p>
                </article>
              ))}
            </section>
          ))}
        </section>
        <section className="plano-secao" aria-label="Alertas">
          <h2 className="cartao-titulo">Alertas</h2>
          {plano.alertas.length === 0 ? <p className="cartao-subtitulo">Nenhum alerta neste plano.</p> : (
            <ul className="plano-alertas">{plano.alertas.map((alerta, i) => (
              <li className="aviso-alerta plano-alerta" key={`${alerta.data}-${alerta.tipo}-${i}`}>
                <span className="plano-alerta-icone" aria-hidden="true">{ICONES_ALERTA[alerta.tipo] ?? "⚠"}</span>
                <div><strong>{dataComDia(alerta.data)}</strong><p>{alerta.texto}</p><small>{alerta.motivo_confianca}</small></div>
              </li>
            ))}</ul>
          )}
        </section>
        <section className="plano-secao" aria-label="Medições pedidas">
          <h2 className="cartao-titulo">Medições pedidas</h2>
          {plano.pedidos_validacao.length === 0 ? <p className="cartao-subtitulo">Nenhuma medição pedida neste plano.</p> : plano.pedidos_validacao.map(pedido => (
            <Medicao key={`${plano.id}-${pedido.piquete_id}`} pedido={pedido} fazenda={fazenda} bloqueado={gerando || medindo || carregando} aoOcupar={setMedindo} />
          ))}
        </section>
      </> : null}
    </div>
  );
}

export default function Plano() {
  const { fazenda } = useFazenda();
  return fazenda ? <PlanoDaFazenda key={fazenda.id} fazenda={fazenda} /> : null;
}
