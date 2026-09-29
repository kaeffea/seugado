import { useEffect, useState } from "react";
import FormularioFazenda, { type DadosFazenda } from "../componentes/ui/FormularioFazenda";
import { mensagemDeErro } from "../componentes/ui/erros";
import { api, ErroApi } from "../lib/api";
import { useFazenda } from "../lib/fazenda";
import type { Fazenda } from "../lib/tipos";
import "./Configuracoes.css";

interface StatusTelegram {
  vinculado: boolean;
  link: string;
}

type EstadoTelegram =
  | { tipo: "carregando" }
  | { tipo: "indisponivel" }
  | { tipo: "erro"; mensagem: string }
  | { tipo: "ok"; status: StatusTelegram };

function estadoDeErro(falha: unknown): EstadoTelegram {
  // 404: a rota ainda não existe nesta versão da API
  if (falha instanceof ErroApi && falha.status === 404) {
    return { tipo: "indisponivel" };
  }
  return { tipo: "erro", mensagem: mensagemDeErro(falha) };
}

function CartaoTelegram({ fazendaId }: { fazendaId: string }) {
  const [estado, setEstado] = useState<EstadoTelegram>({ tipo: "carregando" });
  const [copiado, setCopiado] = useState(false);

  async function consultar(): Promise<void> {
    try {
      const status = await api<StatusTelegram>(`/fazendas/${fazendaId}/telegram`);
      setEstado({ tipo: "ok", status });
    } catch (falha) {
      setEstado(estadoDeErro(falha));
    }
  }

  // o cartão é remontado (key) a cada troca de fazenda, então o estado já começa limpo
  useEffect(() => {
    api<StatusTelegram>(`/fazendas/${fazendaId}/telegram`)
      .then((status) => setEstado({ tipo: "ok", status }))
      .catch((falha: unknown) => setEstado(estadoDeErro(falha)));
  }, [fazendaId]);

  async function copiar(link: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(link);
      setCopiado(true);
    } catch {
      setCopiado(false);
    }
  }

  return (
    <section className="cartao configuracoes-telegram">
      <h2 className="cartao-titulo">Telegram</h2>
      {estado.tipo === "carregando" ? <p className="cartao-subtitulo">Carregando…</p> : null}
      {estado.tipo === "indisponivel" ? (
        <p className="aviso-alerta">Vínculo do Telegram indisponível</p>
      ) : null}
      {estado.tipo === "erro" ? (
        <p className="aviso-erro" role="alert">
          {estado.mensagem}
        </p>
      ) : null}
      {estado.tipo === "ok" && estado.status.vinculado ? (
        <p className="aviso-info">Telegram conectado ✓</p>
      ) : null}
      {estado.tipo === "ok" && !estado.status.vinculado ? (
        <>
          <p>
            Mande este link para o produtor abrir no celular e tocar em <strong>Começar</strong>
          </p>
          <code className="configuracoes-link">{estado.status.link}</code>
          <div className="formulario-acoes">
            <button
              type="button"
              className="botao botao-primario"
              onClick={() => void copiar(estado.status.link)}
            >
              {copiado ? "Copiado ✓" : "Copiar"}
            </button>
            <button
              type="button"
              className="botao botao-secundario"
              onClick={() => void consultar()}
            >
              Atualizar status
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}

export default function Configuracoes() {
  const { fazenda, recarregar } = useFazenda();

  if (fazenda === null) {
    return null;
  }

  async function salvar(dados: DadosFazenda): Promise<void> {
    if (fazenda === null) {
      return;
    }
    await api<Fazenda>(`/fazendas/${fazenda.id}`, {
      method: "PUT",
      body: JSON.stringify(dados),
    });
    await recarregar();
  }

  return (
    <div className="pagina">
      <div className="pagina-cabecalho">
        <div>
          <h1 className="pagina-titulo">Fazenda</h1>
          <p className="cartao-subtitulo">{`Cliente: ${fazenda.cliente_nome ?? "sem cliente"}`}</p>
        </div>
      </div>

      <section className="cartao">
        <FormularioFazenda
          key={fazenda.id}
          clienteId={fazenda.cliente_id}
          inicial={fazenda}
          rotuloEnviar="Salvar"
          mensagemSucesso="Alterações salvas ✓"
          aoEnviar={salvar}
        />
      </section>

      <CartaoTelegram key={fazenda.id} fazendaId={fazenda.id} />
    </div>
  );
}
