import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import { supabase } from "./supabase";
import type { Fazenda, Me } from "./tipos";

export interface EstadoFazenda {
  carregando: boolean;
  usuario: Me | null;
  fazendas: Fazenda[];
  fazenda: Fazenda | null;
  selecionar: (id: string) => void;
  recarregar: () => Promise<void>;
}

const ContextoFazenda = createContext<EstadoFazenda>({
  carregando: true,
  usuario: null,
  fazendas: [],
  fazenda: null,
  selecionar: () => {},
  recarregar: async () => {},
});

const CHAVE_FAZENDA_ID = "seugado.fazenda_id";

function lerFazendaSalva(): string | null {
  try {
    return localStorage.getItem(CHAVE_FAZENDA_ID);
  } catch {
    return null;
  }
}

function salvarFazenda(id: string): void {
  try {
    localStorage.setItem(CHAVE_FAZENDA_ID, id);
  } catch {
    // armazenamento indisponível: a seleção vale só para esta sessão
  }
}

function escolher(fazendas: Fazenda[]): Fazenda | null {
  const salva = lerFazendaSalva();
  return fazendas.find((f) => f.id === salva) ?? fazendas[0] ?? null;
}

export function FazendaProvider({ children }: { children: ReactNode }) {
  const [carregando, setCarregando] = useState(true);
  const [usuario, setUsuario] = useState<Me | null>(null);
  const [fazendas, setFazendas] = useState<Fazenda[]>([]);
  const [fazenda, setFazenda] = useState<Fazenda | null>(null);

  async function recarregar(): Promise<void> {
    const { data } = await supabase.auth.getSession();
    if (!data.session) {
      setUsuario(null);
      setFazendas([]);
      setFazenda(null);
      setCarregando(false);
      return;
    }
    try {
      const me = await api<Me>("/me");
      const lista = await api<Fazenda[]>("/fazendas");
      setUsuario(me);
      setFazendas(lista);
      setFazenda(escolher(lista));
    } catch {
      setUsuario(null);
      setFazendas([]);
      setFazenda(null);
    } finally {
      setCarregando(false);
    }
  }

  function selecionar(id: string): void {
    salvarFazenda(id);
    setFazenda(fazendas.find((f) => f.id === id) ?? null);
  }

  useEffect(() => {
    void recarregar();
    const { data: listener } = supabase.auth.onAuthStateChange(() => {
      void recarregar();
    });
    return () => {
      listener.subscription.unsubscribe();
    };
  }, []);

  return (
    <ContextoFazenda.Provider
      value={{ carregando, usuario, fazendas, fazenda, selecionar, recarregar }}
    >
      {children}
    </ContextoFazenda.Provider>
  );
}

export function useFazenda(): EstadoFazenda {
  return useContext(ContextoFazenda);
}
