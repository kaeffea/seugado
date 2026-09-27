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
  fazenda: Fazenda | null;
  recarregar: () => Promise<void>;
}

const ContextoFazenda = createContext<EstadoFazenda>({
  carregando: true,
  usuario: null,
  fazenda: null,
  recarregar: async () => {},
});

export function FazendaProvider({ children }: { children: ReactNode }) {
  const [carregando, setCarregando] = useState(true);
  const [usuario, setUsuario] = useState<Me | null>(null);
  const [fazenda, setFazenda] = useState<Fazenda | null>(null);

  async function recarregar(): Promise<void> {
    const { data } = await supabase.auth.getSession();
    if (!data.session) {
      setUsuario(null);
      setFazenda(null);
      setCarregando(false);
      return;
    }
    try {
      const me = await api<Me>("/me");
      setUsuario(me);
      setFazenda(me.fazenda);
    } catch {
      setUsuario(null);
      setFazenda(null);
    } finally {
      setCarregando(false);
    }
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
      value={{ carregando, usuario, fazenda, recarregar }}
    >
      {children}
    </ContextoFazenda.Provider>
  );
}

export function useFazenda(): EstadoFazenda {
  return useContext(ContextoFazenda);
}
