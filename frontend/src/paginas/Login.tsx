import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { Marca } from "../componentes/ui/Icones";
import { useFazenda } from "../lib/fazenda";
import { supabase } from "../lib/supabase";
import "./Login.css";

export default function Login() {
  const { carregando, usuario } = useFazenda();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  if (!carregando && usuario !== null) {
    return <Navigate to="/mapa" replace />;
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
        setErro("E-mail ou senha incorretos");
        return;
      }
      navigate("/mapa");
    } catch {
      setErro("E-mail ou senha incorretos");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="login-tela">
      <form className="cartao login-cartao formulario" onSubmit={(evento) => void entrar(evento)}>
        <div className="login-marca">
          <Marca />
          <h1>SeuGado</h1>
        </div>
        <p className="cartao-subtitulo">Painel da equipe</p>
        <label className="campo" htmlFor="login-email">
          E-mail
          <input
            id="login-email"
            className="campo-entrada"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(evento) => setEmail(evento.target.value)}
            required
            disabled={enviando}
          />
        </label>
        <label className="campo" htmlFor="login-senha">
          Senha
          <input
            id="login-senha"
            className="campo-entrada"
            type="password"
            autoComplete="current-password"
            value={senha}
            onChange={(evento) => setSenha(evento.target.value)}
            required
            disabled={enviando}
          />
        </label>
        <button className="botao botao-primario" type="submit" disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>
        {erro !== null ? (
          <p className="aviso-erro" role="alert">
            {erro}
          </p>
        ) : null}
      </form>
    </div>
  );
}
