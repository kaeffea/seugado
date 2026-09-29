import { useState, type FormEvent } from "react";
import { Navigate } from "react-router";
import { useFazenda } from "../lib/fazenda";
import { supabase } from "../lib/supabase";

export default function Login() {
  const { carregando, usuario } = useFazenda();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  if (!carregando && usuario !== null) {
    return <Navigate to="/dashboard" replace />;
  }

  async function entrar(evento: FormEvent<HTMLFormElement>): Promise<void> {
    evento.preventDefault();
    if (enviando) {
      return;
    }
    setEnviando(true);
    setErro(null);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password: senha });
      if (error) {
        setErro("E-mail ou senha inválidos.");
      }
    } catch {
      setErro("Não foi possível conectar. Tente novamente.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="login-tela">
      <form className="login-cartao" onSubmit={(evento) => void entrar(evento)}>
        <h1 className="login-marca">SeuGado</h1>
        <label className="login-rotulo" htmlFor="login-email">
          E-mail
        </label>
        <input
          id="login-email"
          className="login-campo"
          type="email"
          value={email}
          onChange={(evento) => setEmail(evento.target.value)}
          required
          disabled={enviando}
        />
        <label className="login-rotulo" htmlFor="login-senha">
          Senha
        </label>
        <input
          id="login-senha"
          className="login-campo"
          type="password"
          value={senha}
          onChange={(evento) => setSenha(evento.target.value)}
          required
          disabled={enviando}
        />
        <button className="login-botao" type="submit" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>
        {erro !== null ? (
          <p className="login-erro" role="alert">
            {erro}
          </p>
        ) : null}
      </form>
    </div>
  );
}
