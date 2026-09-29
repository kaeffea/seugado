import type { ComposicaoItem, Lote, Movimentacao, Piquete, PlanoManejo } from "../lib/tipos";

// Datas de calendário da API não são instantes UTC: preserve o dia em qualquer fuso.
export function dataCurta(data: string): string {
  return new Date(`${data}T12:00:00Z`).toLocaleDateString("pt-BR", { timeZone: "UTC", day: "2-digit", month: "2-digit" });
}

export function dataComDia(data: string): string {
  return new Date(`${data}T12:00:00Z`).toLocaleDateString("pt-BR", { timeZone: "UTC", weekday: "short", day: "2-digit", month: "2-digit" }).replace(".,", "").replace(".", "");
}

export function hojeNaFazenda(timeZone: string, agora = new Date()): string {
  const partes = new Intl.DateTimeFormat("en-US", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(agora);
  const valor = (tipo: string) => partes.find(p => p.type === tipo)!.value;
  return `${valor("year")}-${valor("month")}-${valor("day")}`;
}

export function fimDoPlano(plano: Pick<PlanoManejo, "data_inicio" | "horizonte_dias">): string {
  const data = new Date(`${plano.data_inicio}T12:00:00Z`);
  data.setUTCDate(data.getUTCDate() + plano.horizonte_dias - 1);
  return data.toISOString().slice(0, 10);
}

export function piquetesDisponiveis(piquetes: Piquete[], lote: Lote | null): Piquete[] {
  return piquetes.filter(p => p.lote_atual_id === null || p.id === lote?.piquete_atual_id);
}

export function pesoParaEdicao(item: ComposicaoItem): string {
  return item.origem_peso === "ua_tabela" || item.peso_medio_kg === null ? "" : String(item.peso_medio_kg);
}

export function movimentosPorDia(movimentacoes: Movimentacao[]): [string, Movimentacao[]][] {
  const dias = new Map<string, Movimentacao[]>();
  for (const movimento of movimentacoes) {
    const lista = dias.get(movimento.data) ?? [];
    lista.push(movimento);
    dias.set(movimento.data, lista);
  }
  return [...dias].sort(([a], [b]) => a.localeCompare(b));
}
