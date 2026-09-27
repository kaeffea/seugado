import { Navigate, Outlet } from "react-router";
import { useFazenda } from "../lib/fazenda";

export default function RotaProtegida() {
  const { carregando, usuario } = useFazenda();
  if (carregando) {
    return <>Carregando…</>;
  }
  if (usuario === null) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
}
