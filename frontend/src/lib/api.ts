import { supabase } from "./supabase";

export class ErroApi extends Error {
  status: number;
  corpo: string;

  constructor(status: number, corpo: string) {
    super(corpo);
    this.status = status;
    this.corpo = corpo;
    this.name = "ErroApi";
  }
}

export async function api<T>(
  caminho: string,
  opcoes: RequestInit = {},
): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const cabecalhos = new Headers(opcoes.headers);
  cabecalhos.set("Content-Type", "application/json");
  if (token) {
    cabecalhos.set("Authorization", `Bearer ${token}`);
  }
  const resposta = await fetch(import.meta.env.VITE_API_URL + caminho, {
    ...opcoes,
    headers: cabecalhos,
  });
  if (!resposta.ok) {
    const texto = await resposta.text();
    throw new ErroApi(resposta.status, texto);
  }
  if (resposta.status === 204) {
    return undefined as T;
  }
  return (await resposta.json()) as T;
}
