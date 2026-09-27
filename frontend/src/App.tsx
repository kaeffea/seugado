import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import Layout from "./componentes/Layout";
import RotaProtegida from "./componentes/RotaProtegida";
import { FazendaProvider } from "./lib/fazenda";
import Clientes from "./paginas/Clientes";
import Configuracoes from "./paginas/Configuracoes";
import Login from "./paginas/Login";
import Lotes from "./paginas/Lotes";
import Mapa from "./paginas/Mapa";
import Plano from "./paginas/Plano";

export default function App() {
  return (
    <BrowserRouter>
      <FazendaProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<RotaProtegida />}>
            <Route element={<Layout />}>
              <Route path="/clientes" element={<Clientes />} />
              <Route path="/mapa" element={<Mapa />} />
              <Route path="/lotes" element={<Lotes />} />
              <Route path="/plano" element={<Plano />} />
              <Route path="/configuracoes" element={<Configuracoes />} />
            </Route>
          </Route>
          <Route path="/" element={<Navigate to="/mapa" replace />} />
          <Route path="*" element={<Navigate to="/mapa" replace />} />
        </Routes>
      </FazendaProvider>
    </BrowserRouter>
  );
}
