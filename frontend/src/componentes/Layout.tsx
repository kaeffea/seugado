import { Link, Outlet, useLocation } from "react-router";
import { useFazenda } from "../lib/fazenda";
import { supabase } from "../lib/supabase";
import iconeAjuda from "../assets/Piquetes_icon.png";
import iconeAnimais from "../assets/Animais_icon.png";
import iconeConfiguracoes from "../assets/Fazenda_icon.png";
import iconeDashboard from "../assets/Dashboard_icon.png";
import iconeFazenda from "../assets/Fazenda_icon.png";
import iconeManejos from "../assets/Manejos_icon.png";
import iconeNotificacoes from "../assets/Dashboard_icon.png";
import iconePiquetes from "../assets/Piquetes_icon.png";
import logoMarca from "../assets/logo_darkbg.png";

interface ItemMenu {
  rotulo: string;
  caminho: string;
  icone: string;
}

// Navigation entries. The overlap with the route table in App.tsx is deliberate
// and temporary: no shared constants module until the real pages exist.
// Notificações, Configurações and Ajuda reuse an existing icon: there is no
// dedicated artwork for them yet.
const MENU_PRIMARIO: ItemMenu[] = [
  { rotulo: "Dashboard", caminho: "/dashboard", icone: iconeDashboard },
  { rotulo: "Fazenda", caminho: "/fazenda", icone: iconeFazenda },
  { rotulo: "Piquetes", caminho: "/piquetes", icone: iconePiquetes },
  { rotulo: "Animais", caminho: "/animais", icone: iconeAnimais },
  { rotulo: "Manejos", caminho: "/manejos", icone: iconeManejos },
];

const MENU_SECUNDARIO: ItemMenu[] = [
  { rotulo: "Notificações", caminho: "/notificacoes", icone: iconeNotificacoes },
  { rotulo: "Configurações", caminho: "/configuracoes", icone: iconeConfiguracoes },
  { rotulo: "Ajuda", caminho: "/ajuda", icone: iconeAjuda },
];

export default function Layout() {
  const { usuario, fazendas, fazenda, selecionar } = useFazenda();
  const localizacao = useLocation();

  async function sair(): Promise<void> {
    await supabase.auth.signOut();
  }

  function item(entrada: ItemMenu) {
    const ativo = localizacao.pathname === entrada.caminho;
    return (
      <Link
        key={entrada.caminho}
        to={entrada.caminho}
        className="menu-item"
        aria-current={ativo ? "page" : undefined}
      >
        <img src={entrada.icone} alt="" className="menu-item-icone" />
        <span>{entrada.rotulo}</span>
      </Link>
    );
  }

  return (
    <>
      <aside className="menu-lateral">
        <div className="menu-cabecalho">
          <img src={logoMarca} alt="" className="menu-logo" />
          <span className="menu-marca">SeuGado</span>
        </div>
        <nav className="menu-grupo" aria-label="Menu principal">
          {MENU_PRIMARIO.map(item)}
        </nav>
        <hr className="menu-divisor" />
        <nav className="menu-grupo" aria-label="Menu secundário">
          {MENU_SECUNDARIO.map(item)}
        </nav>
        <div className="menu-rodape">
          <div className="menu-perfil">
            <span className="menu-avatar" aria-hidden="true" />
            <div className="menu-perfil-texto">
              <span className="menu-email">{usuario?.email ?? "sem e-mail"}</span>
              <span className="menu-fazenda-nome">
                {fazenda?.nome ?? "nenhuma fazenda"}
              </span>
            </div>
          </div>
          <label className="menu-rotulo" htmlFor="seletor-fazenda">
            Fazenda ativa
          </label>
          <select
            id="seletor-fazenda"
            className="menu-select"
            value={fazenda?.id ?? ""}
            onChange={(evento) => selecionar(evento.target.value)}
          >
            {fazendas.map((f) => (
              <option key={f.id} value={f.id}>
                {f.nome}
              </option>
            ))}
          </select>
          <button type="button" className="menu-sair" onClick={() => void sair()}>
            Sair
          </button>
        </div>
      </aside>
      <main className="conteudo">
        {fazenda === null && localizacao.pathname === "/ajuda" ? (
          <p>
            Nenhuma fazenda selecionada.{" "}
            <Link to="/clientes">Clientes e fazendas</Link>
          </p>
        ) : (
          <Outlet />
        )}
      </main>
    </>
  );
}
