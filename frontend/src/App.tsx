import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import Layout from "./componentes/Layout";
import RotaProtegida from "./componentes/RotaProtegida";
import { FazendaProvider } from "./lib/fazenda";
import Clientes from "./paginas/Clientes";
import EmConstrucao from "./paginas/EmConstrucao";
import Login from "./paginas/Login";
import Mapa from "./paginas/Mapa";

export default function App() {
  return (
    <BrowserRouter>
      <FazendaProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<RotaProtegida />}>
            <Route element={<Layout />}>
              <Route path="/dashboard" element={<EmConstrucao titulo="Dashboard" />} />
              <Route path="/fazenda" element={<EmConstrucao titulo="Fazenda" />} />
              <Route path="/piquetes" element={<EmConstrucao titulo="Piquetes" />} />
              <Route path="/animais" element={<EmConstrucao titulo="Animais" />} />
              <Route path="/manejos" element={<EmConstrucao titulo="Manejos" />} />
              <Route
                path="/notificacoes"
                element={<EmConstrucao titulo="Notificações" />}
              />
              <Route
                path="/configuracoes"
                element={<EmConstrucao titulo="Configurações" />}
              />
              <Route path="/ajuda" element={<EmConstrucao titulo="Ajuda" />} />
              <Route path="/mapa" element={<Mapa />} />
              <Route path="/clientes" element={<Clientes />} />
            </Route>
          </Route>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </FazendaProvider>
    </BrowserRouter>
  );
}
