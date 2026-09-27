export type Confianca = "alta" | "media" | "baixa";
export type MetodoPastejo = "continuo" | "rotacionado";
export type Categoria = "bezerro" | "bezerra" | "novilho" | "novilha" | "vaca" | "boi" | "touro";
export type SituacaoPiquete = "ocupado" | "descansando";

export interface Cliente { id: string; nome: string; telefone: string | null; observacoes: string | null; }

export interface Fazenda {
  id: string; cliente_id: string | null; cliente_nome: string | null;
  nome: string; timezone: string;
  funcionarios_disponiveis: number; animais_por_funcionario_dia: number;
  dias_preferenciais_manejo: number[];            // 0 = segunda … 6 = domingo
  envio_plano_dia: number;                        // 0 = segunda … 6 = domingo
  envio_plano_hora: number;                       // 0 … 23, hora local da fazenda
}
export interface Me { usuario_id: string; email: string | null; }

export interface Cultivar {
  id: string; slug: string; nome: string;
  regimes_disponiveis: MetodoPastejo[]; calibrada: boolean; faltantes_calibracao: string[];
}
export interface GeoJsonPolygon { type: "Polygon"; coordinates: number[][][]; }
export interface Piquete {
  id: string; nome: string; geometria: GeoJsonPolygon; area_ha: number;
  cultivar_id: string; cultivar_nome: string; metodo_pastejo: MetodoPastejo;
  situacao: SituacaoPiquete; lote_atual_id: string | null; lote_atual_nome: string | null;
  ultima_altura_cm: number | null; ultima_altura_data: string | null;
}
export interface ParametroPendente {
  cultivar_id: string; cultivar_nome: string; metodo_pastejo: MetodoPastejo; faltantes: string[];
}
export interface ComposicaoItem {
  categoria: Categoria; n_animais: number; peso_medio_kg: number | null;
  origem_peso?: "produtor" | "ua_tabela";
}
export interface Lote {
  id: string; nome: string; indissoluvel: boolean; composicao: ComposicaoItem[];
  piquete_atual_id: string | null; piquete_atual_nome: string | null; desde: string | null;
  peso_vivo_total_kg: number; n_animais_total: number;
}
export interface Movimentacao {
  id: string; data: string; lote_id: string; lote_nome: string;
  piquete_origem_id: string | null; piquete_origem_nome: string | null;
  piquete_destino_id: string; piquete_destino_nome: string;
  altura_destino_cm: number; altura_entrada_alvo_cm: number;
  altura_origem_cm: number | null; altura_saida_alvo_cm: number | null;
  dias_previstos: number; motivo: string; confianca: Confianca; motivo_confianca: string;
}
export interface Alerta {
  tipo: string; data: string; texto: string; confianca: Confianca; motivo_confianca: string;
  piquete_id: string | null; lote_id: string | null;
}
export interface PedidoValidacao { piquete_id: string; piquete_nome: string; motivo: string; }
export interface ResumoPiquete {
  piquete_id: string; nome: string; situacao: SituacaoPiquete; lote_atual_nome: string | null;
  altura_hoje_cm: number | null; altura_entrada_alvo_cm: number | null;
  altura_saida_alvo_cm: number | null; confianca: Confianca; motivo_confianca: string;
  faltantes: string[];
}
export interface PlanoManejo {
  id: string; fazenda_id: string; data_geracao: string; data_inicio: string; horizonte_dias: number;
  movimentacoes: Movimentacao[]; alertas: Alerta[]; pedidos_validacao: PedidoValidacao[];
  piquetes: ResumoPiquete[];
}
