import { Navigate, Outlet, useLocation } from "react-router";
import { useFazenda } from "../lib/fazenda";

export default function RotaProtegida() {
  const { carregando, usuario, fazenda } = useFazenda();
  const localizacao = useLocation();
  if (carregando) {
    return <>Carregando…</>;
  }
  if (usuario === null) {
    return <Navigate to="/login" replace />;
  }
  if (fazenda === null && localizacao.pathname !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }
  return <Outlet />;
}
