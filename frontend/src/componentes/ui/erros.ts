import { ErroApi } from "../../lib/api";

interface ItemDetalhe {
  msg?: unknown;
}

// Traduz o corpo de erro do FastAPI ({"detail": "..."} ou lista de validação) em texto.
export function mensagemDeErro(erro: unknown): string {
  if (erro instanceof ErroApi) {
    try {
      const corpo = JSON.parse(erro.corpo) as { detail?: unknown };
      if (typeof corpo.detail === "string") {
        return corpo.detail;
      }
      if (Array.isArray(corpo.detail)) {
        const mensagens = (corpo.detail as ItemDetalhe[])
          .map((item) => (typeof item.msg === "string" ? item.msg : ""))
          .filter((texto) => texto !== "");
        if (mensagens.length > 0) {
          return mensagens.join("; ");
        }
      }
    } catch {
      // corpo que não é JSON: cai no texto bruto abaixo
    }
    return erro.corpo || `Erro ${erro.status}`;
  }
  return erro instanceof Error ? erro.message : "Erro inesperado";
}
