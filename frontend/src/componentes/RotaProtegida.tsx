import { Outlet } from "react-router";
import { useFazenda } from "../lib/fazenda";

export default function RotaProtegida() {
  const { carregando } = useFazenda();
  if (carregando) {
    return <>Carregando…</>;
  }
  // Login redirect temporarily disabled by the user to preview screens
  // without Supabase access. Restore before shipping this component.
  // if (usuario === null) {
  //   return <Navigate to="/login" replace />;
  // }
  return <Outlet />;
}
