import { Link, Outlet, useLocation } from "react-router";
import { useFazenda } from "../lib/fazenda";
import { supabase } from "../lib/supabase";

export default function Layout() {
  const { fazendas, fazenda, selecionar } = useFazenda();
  const localizacao = useLocation();

  async function sair(): Promise<void> {
    await supabase.auth.signOut();
  }

  return (
    <>
      <header>
        <span>SeuGado · Admin</span>
        <select
          value={fazenda?.id ?? ""}
          onChange={(evento) => selecionar(evento.target.value)}
        >
          {fazendas.map((f) => (
            <option key={f.id} value={f.id}>
              {`${f.cliente_nome ?? "sem cliente"} — ${f.nome}`}
            </option>
          ))}
        </select>
        <nav>
          <Link to="/clientes">Clientes e fazendas</Link>
          <Link to="/mapa">Mapa</Link>
          <Link to="/lotes">Lotes</Link>
          <Link to="/plano">Plano da semana</Link>
          <Link to="/configuracoes">Fazenda</Link>
        </nav>
        <button type="button" onClick={() => void sair()}>
          Sair
        </button>
      </header>
      <main>
        {fazenda === null && localizacao.pathname !== "/clientes" ? (
          <p>
            Nenhuma fazenda selecionada. Cadastre uma em{" "}
            <Link to="/clientes">Clientes e fazendas</Link>.
          </p>
        ) : (
          <Outlet />
        )}
      </main>
    </>
  );
}
