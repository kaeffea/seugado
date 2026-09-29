import { useState, type FormEvent } from "react";
import type { Fazenda } from "../../lib/tipos";
import { mensagemDeErro } from "./erros";
import "./FormularioFazenda.css";

export type DadosFazenda = Omit<Fazenda, "id" | "cliente_nome">;

const DIAS_CURTOS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
const DIAS_LONGOS = [
  "Segunda-feira",
  "Terça-feira",
  "Quarta-feira",
  "Quinta-feira",
  "Sexta-feira",
  "Sábado",
  "Domingo",
];
const HORAS = Array.from({ length: 24 }, (_, hora) => hora);

// Segunda e quinta marcadas por padrão (L3).
const DIAS_MANEJO_PADRAO = [0, 3];
const FUSO_PADRAO = "America/Fortaleza";
const ENVIO_DIA_PADRAO = 6;
const ENVIO_HORA_PADRAO = 18;

interface Props {
  clienteId: string | null;
  inicial?: Fazenda;
  rotuloEnviar: string;
  mensagemSucesso?: string;
  aoEnviar: (dados: DadosFazenda) => Promise<void>;
  aoCancelar?: () => void;
}

export default function FormularioFazenda({
  clienteId,
  inicial,
  rotuloEnviar,
  mensagemSucesso,
  aoEnviar,
  aoCancelar,
}: Props) {
  const [nome, setNome] = useState(inicial?.nome ?? "");
  const [funcionarios, setFuncionarios] = useState(
    inicial ? String(inicial.funcionarios_disponiveis) : "",
  );
  const [animais, setAnimais] = useState(
    inicial ? String(inicial.animais_por_funcionario_dia) : "",
  );
  const [dias, setDias] = useState<number[]>(
    inicial?.dias_preferenciais_manejo ?? DIAS_MANEJO_PADRAO,
  );
  const [envioDia, setEnvioDia] = useState(inicial?.envio_plano_dia ?? ENVIO_DIA_PADRAO);
  const [envioHora, setEnvioHora] = useState(inicial?.envio_plano_hora ?? ENVIO_HORA_PADRAO);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [salvo, setSalvo] = useState(false);

  function alternarDia(dia: number): void {
    setSalvo(false);
    setDias((atuais) =>
      atuais.includes(dia) ? atuais.filter((d) => d !== dia) : [...atuais, dia],
    );
  }

  async function enviar(evento: FormEvent<HTMLFormElement>): Promise<void> {
    evento.preventDefault();
    if (enviando) {
      return;
    }
    setErro(null);
    setSalvo(false);
    const nFuncionarios = Number.parseInt(funcionarios, 10);
    const nAnimais = Number.parseInt(animais, 10);
    if (!(nFuncionarios >= 1) || !(nAnimais >= 1)) {
      setErro("Informe pelo menos 1 pessoa e 1 animal por pessoa.");
      return;
    }
    if (dias.length === 0) {
      setErro("Marque pelo menos um dia da semana para mexer no gado.");
      return;
    }
    setEnviando(true);
    try {
      await aoEnviar({
        cliente_id: clienteId,
        nome: nome.trim(),
        timezone: inicial?.timezone ?? FUSO_PADRAO,
        funcionarios_disponiveis: nFuncionarios,
        animais_por_funcionario_dia: nAnimais,
        dias_preferenciais_manejo: [...dias].sort((a, b) => a - b),
        envio_plano_dia: envioDia,
        envio_plano_hora: envioHora,
      });
      setSalvo(true);
    } catch (falha) {
      setErro(mensagemDeErro(falha));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className="formulario" onSubmit={(evento) => void enviar(evento)}>
      <label className="campo">
        Nome da fazenda
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
        Quantas pessoas fazem o manejo do gado?
        <input
          className="campo-entrada"
          type="number"
          min={1}
          step={1}
          value={funcionarios}
          onChange={(evento) => setFuncionarios(evento.target.value)}
          required
          disabled={enviando}
        />
      </label>
      <label className="campo">
        Quantos animais cada pessoa consegue mover sozinha num dia?
        <input
          className="campo-entrada"
          type="number"
          min={1}
          step={1}
          value={animais}
          onChange={(evento) => setAnimais(evento.target.value)}
          required
          disabled={enviando}
        />
      </label>
      <fieldset className="campo formulario-dias">
        <legend>Em quais dias da semana se pode mexer no gado?</legend>
        <div className="formulario-dias-lista">
          {DIAS_CURTOS.map((rotulo, dia) => (
            <label key={rotulo} className="formulario-dia">
              <input
                type="checkbox"
                checked={dias.includes(dia)}
                onChange={() => alternarDia(dia)}
                disabled={enviando}
              />
              {rotulo}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="campo formulario-dias">
        <legend>Quando o produtor quer receber o plano?</legend>
        <div className="formulario-envio">
          <select
            className="campo-entrada"
            aria-label="Dia da semana do envio"
            value={envioDia}
            onChange={(evento) => setEnvioDia(Number(evento.target.value))}
            disabled={enviando}
          >
            {DIAS_LONGOS.map((rotulo, dia) => (
              <option key={rotulo} value={dia}>
                {rotulo}
              </option>
            ))}
          </select>
          <select
            className="campo-entrada"
            aria-label="Hora do envio"
            value={envioHora}
            onChange={(evento) => setEnvioHora(Number(evento.target.value))}
            disabled={enviando}
          >
            {HORAS.map((hora) => (
              <option key={hora} value={hora}>
                {`${hora}h`}
              </option>
            ))}
          </select>
        </div>
      </fieldset>
      {erro !== null ? (
        <p className="aviso-erro" role="alert">
          {erro}
        </p>
      ) : null}
      {salvo && mensagemSucesso ? <p className="aviso-info">{mensagemSucesso}</p> : null}
      <div className="formulario-acoes">
        <button className="botao botao-primario" type="submit" disabled={enviando}>
          {enviando ? "Salvando…" : rotuloEnviar}
        </button>
        {aoCancelar ? (
          <button
            className="botao botao-secundario"
            type="button"
            onClick={aoCancelar}
            disabled={enviando}
          >
            Cancelar
          </button>
        ) : null}
      </div>
    </form>
  );
}
