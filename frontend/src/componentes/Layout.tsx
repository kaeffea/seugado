import { Link, Outlet, useLocation } from "react-router";
import { useFazenda } from "../lib/fazenda";
import { supabase } from "../lib/supabase";
import { Icone, Marca, type NomeIcone } from "./ui/Icones";
import "./Layout.css";

const LINKS: { para: string; texto: string; icone: NomeIcone }[] = [
  { para: "/clientes", texto: "Clientes e fazendas", icone: "clientes" },
  { para: "/mapa", texto: "Mapa", icone: "mapa" },
  { para: "/lotes", texto: "Lotes", icone: "lotes" },
  { para: "/plano", texto: "Plano da semana", icone: "plano" },
  { para: "/configuracoes", texto: "Fazenda", icone: "fazenda" },
];

export default function Layout() {
  const { usuario, fazendas, fazenda, selecionar } = useFazenda();
  const localizacao = useLocation();

  async function sair(): Promise<void> {
    await supabase.auth.signOut();
  }

  const identificacao = usuario?.email ?? "";

  return (
    <div className="layout">
      <aside className="menu">
        <div className="menu-marca">
          <Marca />
          <span>SeuGado · Admin</span>
        </div>
        <nav className="menu-links">
          {LINKS.map((item) => {
            const ativo = localizacao.pathname === item.para;
            return (
              <Link
                key={item.para}
                to={item.para}
                className={ativo ? "menu-link ativo" : "menu-link"}
              >
                <Icone nome={item.icone} />
                <span>{item.texto}</span>
              </Link>
            );
          })}
        </nav>
        <div className="menu-rodape">
          <select
            className="menu-seletor"
            value={fazenda?.id ?? ""}
            onChange={(evento) => selecionar(evento.target.value)}
          >
            {fazendas.map((f) => (
              <option key={f.id} value={f.id}>
                {`${f.cliente_nome ?? "sem cliente"} — ${f.nome}`}
              </option>
            ))}
          </select>
          <div className="menu-usuario">
            <span className="menu-avatar" aria-hidden="true">
              {identificacao.charAt(0).toUpperCase()}
            </span>
            <span className="menu-usuario-texto">
              <span className="menu-usuario-nome">{identificacao}</span>
              <span className="menu-usuario-fazenda">{fazenda?.nome ?? ""}</span>
            </span>
            <button
              type="button"
              className="menu-sair"
              onClick={() => void sair()}
              aria-label="Sair"
            >
              <Icone nome="sair" />
              <span>Sair</span>
            </button>
          </div>
        </div>
      </aside>
      <main className={localizacao.pathname === "/mapa" ? "conteudo conteudo-cheio" : "conteudo"}>
        {fazenda === null && localizacao.pathname !== "/clientes" ? (
          <p>
            Nenhuma fazenda selecionada. Cadastre uma em{" "}
            <Link to="/clientes">Clientes e fazendas</Link>.
          </p>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
}
