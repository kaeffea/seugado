import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import FormularioFazenda, { type DadosFazenda } from "../componentes/ui/FormularioFazenda";
import { mensagemDeErro } from "../componentes/ui/erros";
import { api } from "../lib/api";
import { useFazenda } from "../lib/fazenda";
import type { Cliente, Fazenda } from "../lib/tipos";
import "./Clientes.css";

function FormularioCliente({
  aoCriar,
  aoCancelar,
}: {
  aoCriar: () => Promise<void>;
  aoCancelar: () => void;
}) {
  const [nome, setNome] = useState("");
  const [telefone, setTelefone] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function enviar(evento: FormEvent<HTMLFormElement>): Promise<void> {
    evento.preventDefault();
    if (enviando) {
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      await api<Cliente>("/clientes", {
        method: "POST",
        body: JSON.stringify({
          nome: nome.trim(),
          telefone: telefone.trim() === "" ? null : telefone.trim(),
          observacoes: observacoes.trim() === "" ? null : observacoes.trim(),
        }),
      });
      await aoCriar();
    } catch (falha) {
      setErro(mensagemDeErro(falha));
      setEnviando(false);
    }
  }

  return (
    <form className="cartao formulario" onSubmit={(evento) => void enviar(evento)}>
      <h2 className="cartao-titulo">Novo cliente</h2>
      <label className="campo">
        Nome
        <input
          className="campo-entrada"
          type="text"
          value={nome}
          onChange={(evento) => setNome(evento.target.value)}
          required
          disabled={enviando}
        />
      </label>
      <label className="campo">
        Telefone
        <input
          className="campo-entrada"
          type="tel"
          value={telefone}
          onChange={(evento) => setTelefone(evento.target.value)}
          disabled={enviando}
        />
      </label>
      <label className="campo">
        Observações
        <textarea
          className="campo-entrada"
          rows={3}
          value={observacoes}
          onChange={(evento) => setObservacoes(evento.target.value)}
          disabled={enviando}
        />
      </label>
      {erro !== null ? (
        <p className="aviso-erro" role="alert">
          {erro}
        </p>
      ) : null}
      <div className="formulario-acoes">
        <button className="botao botao-primario" type="submit" disabled={enviando}>
          {enviando ? "Salvando…" : "Criar cliente"}
        </button>
        <button
          className="botao botao-secundario"
          type="button"
          onClick={aoCancelar}
          disabled={enviando}
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

function ListaFazendas({
  fazendas,
  selecionada,
  aoAbrir,
}: {
  fazendas: Fazenda[];
  selecionada: string | null;
  aoAbrir: (id: string) => void;
}) {
  if (fazendas.length === 0) {
    return <p className="cartao-subtitulo">Nenhuma fazenda cadastrada.</p>;
  }
  return (
    <ul className="clientes-fazendas">
      {fazendas.map((f) => (
        <li key={f.id}>
          <button
            type="button"
            className={
              f.id === selecionada ? "clientes-fazenda clientes-fazenda-ativa" : "clientes-fazenda"
            }
            onClick={() => aoAbrir(f.id)}
          >
            <span className="clientes-fazenda-nome">{f.nome}</span>
            <span className="clientes-fazenda-detalhe">
              {`${f.funcionarios_disponiveis} ${
                f.funcionarios_disponiveis === 1 ? "pessoa" : "pessoas"
              } no manejo`}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

export default function Clientes() {
  const { fazendas, fazenda, selecionar, recarregar } = useFazenda();
  const navigate = useNavigate();
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [novoCliente, setNovoCliente] = useState(false);
  const [novaFazendaDe, setNovaFazendaDe] = useState<string | null>(null);

  // incrementar recarrega a lista de clientes
  const [recarga, setRecarga] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api<Cliente[]>("/clientes")
      .then((lista) => {
        if (!cancelado) {
          setClientes(lista);
          setErro(null);
        }
      })
      .catch((falha: unknown) => {
        if (!cancelado) {
          setErro(mensagemDeErro(falha));
        }
      })
      .finally(() => {
        if (!cancelado) {
          setCarregando(false);
        }
      });
    return () => {
      cancelado = true;
    };
  }, [recarga]);

  function abrirFazenda(id: string): void {
    selecionar(id);
    navigate("/mapa");
  }

  async function criarFazenda(dados: DadosFazenda): Promise<void> {
    await api<Fazenda>("/fazendas", { method: "POST", body: JSON.stringify(dados) });
    await recarregar();
    setNovaFazendaDe(null);
  }

  async function aoCriarCliente(): Promise<void> {
    setRecarga((n) => n + 1);
    setNovoCliente(false);
  }

  const semCliente = fazendas.filter((f) => f.cliente_id === null);

  return (
    <div className="pagina">
      <div className="pagina-cabecalho">
        <div>
          <h1 className="pagina-titulo">Clientes e fazendas</h1>
          <p className="cartao-subtitulo">Cadastre o produtor, a fazenda e a rotina de manejo.</p>
        </div>
        {novoCliente ? null : (
          <button
            type="button"
            className="botao botao-primario"
            onClick={() => setNovoCliente(true)}
          >
            Novo cliente
          </button>
        )}
      </div>

      {novoCliente ? (
        <FormularioCliente aoCriar={aoCriarCliente} aoCancelar={() => setNovoCliente(false)} />
      ) : null}

      {erro !== null ? (
        <p className="aviso-erro" role="alert">
          {erro}
        </p>
      ) : null}

      {carregando ? <p className="cartao-subtitulo">Carregando…</p> : null}
      {!carregando && erro === null && clientes.length === 0 && semCliente.length === 0 ? (
        <p className="cartao cartao-subtitulo">
          Nenhum cliente cadastrado ainda. Toque em “Novo cliente” para começar.
        </p>
      ) : null}

      {clientes.map((c) => (
        <section key={c.id} className="cartao clientes-cartao">
          <div className="clientes-cabecalho">
            <div>
              <h2 className="cartao-titulo">{c.nome}</h2>
              {c.telefone ? <p className="cartao-subtitulo">{c.telefone}</p> : null}
              {c.observacoes ? <p className="cartao-subtitulo">{c.observacoes}</p> : null}
            </div>
            {novaFazendaDe === c.id ? null : (
              <button
                type="button"
                className="botao botao-secundario"
                onClick={() => setNovaFazendaDe(c.id)}
              >
                Nova fazenda
              </button>
            )}
          </div>
          <ListaFazendas
            fazendas={fazendas.filter((f) => f.cliente_id === c.id)}
            selecionada={fazenda?.id ?? null}
            aoAbrir={abrirFazenda}
          />
          {novaFazendaDe === c.id ? (
            <div className="clientes-nova-fazenda">
              <h3 className="cartao-titulo">Nova fazenda</h3>
              <FormularioFazenda
                clienteId={c.id}
                rotuloEnviar="Criar fazenda"
                aoEnviar={criarFazenda}
                aoCancelar={() => setNovaFazendaDe(null)}
              />
            </div>
          ) : null}
        </section>
      ))}

      {semCliente.length > 0 ? (
        <section className="cartao clientes-cartao">
          <h2 className="cartao-titulo">Sem cliente</h2>
          <ListaFazendas
            fazendas={semCliente}
            selecionada={fazenda?.id ?? null}
            aoAbrir={abrirFazenda}
          />
        </section>
      ) : null}
    </div>
  );
}
