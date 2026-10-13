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

// 1 UA = 450 kg de peso vivo (ADR-014): o mesmo divisor da lotação por módulo no backend.
export const KG_POR_UA = 450;

// peso_vivo_total_kg já soma quantidade × peso médio, com o peso da tabela quando falta o informado.
export function uaDoLote(lote: Pick<Lote, "peso_vivo_total_kg">): number {
  return lote.peso_vivo_total_kg / KG_POR_UA;
}

export interface Lotacao { cabecas: number; ua: number; areaHa: number; uaPorHa: number | null; }

// Lotação global (ADR-026 §4): UA de todos os lotes ÷ área dos piquetes ativos.
export function lotacaoGlobal(
  lotes: Pick<Lote, "n_animais_total" | "peso_vivo_total_kg">[],
  piquetes: Pick<Piquete, "area_ha">[],
): Lotacao {
  const cabecas = lotes.reduce((soma, lote) => soma + lote.n_animais_total, 0);
  const ua = lotes.reduce((soma, lote) => soma + uaDoLote(lote), 0);
  const areaHa = piquetes.reduce((soma, piquete) => soma + piquete.area_ha, 0);
  return { cabecas, ua, areaHa, uaPorHa: areaHa > 0 ? ua / areaHa : null };
}

export function decimal(valor: number, casas: number): string {
  return valor.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
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
