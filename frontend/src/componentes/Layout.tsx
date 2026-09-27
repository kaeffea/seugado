import { Link, Outlet } from "react-router";
import { supabase } from "../lib/supabase";

export default function Layout() {
  async function sair(): Promise<void> {
    await supabase.auth.signOut();
  }

  return (
    <>
      <header>
        <span>SeuGado</span>
        <nav>
          <Link to="/mapa">Mapa</Link>
          <Link to="/lotes">Lotes</Link>
          <Link to="/plano">Plano da semana</Link>
          <Link to="/configuracoes">Configurações</Link>
        </nav>
        <button type="button" onClick={() => void sair()}>
          Sair
        </button>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );
}
