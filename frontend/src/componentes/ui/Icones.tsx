import logoEscuro from "../../assets/Logo/Logo_Dark.png";
import logoClaro from "../../assets/Logo/Logo_Light.png";

export type NomeIcone =
  | "clientes"
  | "mapa"
  | "lotes"
  | "plano"
  | "fazenda"
  | "sair"
  | "seta";

const CAMINHOS: Record<NomeIcone, string[]> = {
  clientes: [
    "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2",
    "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
    "M22 21v-2a4 4 0 0 0-3-3.87",
    "M16 3.13a4 4 0 0 1 0 7.75",
  ],
  mapa: [
    "M1 6v16l7-4 8 4 7-4V2l-7 4-8-4-7 4z",
    "M8 2v16",
    "M16 6v16",
  ],
  lotes: [
    "M1 3h15v13H1z",
    "M16 8h4l3 3v5h-7V8z",
    "M5.5 21a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
    "M18.5 21a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
  ],
  plano: [
    "M3 3h18v14H3z",
    "M8 21h8",
    "M12 17v4",
    "M7 12l3-3 3 2 4-4",
  ],
  fazenda: [
    "M22 12h-6l-2 3h-4l-2-3H2",
    "M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z",
  ],
  sair: [
    "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4",
    "M16 17l5-5-5-5",
    "M21 12H9",
  ],
  seta: ["M9 18l6-6-6-6"],
};

export function Icone({ nome }: { nome: NomeIcone }) {
  return (
    <svg
      className="icone"
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {CAMINHOS[nome].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}

export function Marca({ sobre = "claro" }: { sobre?: "claro" | "escuro" }) {
  return (
    <img
      className="marca-logo"
      src={sobre === "escuro" ? logoEscuro : logoClaro}
      width={32}
      height={32}
      alt=""
      aria-hidden="true"
    />
  );
}
