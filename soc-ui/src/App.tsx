import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import Coverage from "./pages/Coverage";
import Graph from "./pages/Graph";
import Incident from "./pages/Incident";
import Lab from "./pages/Lab";
import Panorama from "./pages/Panorama";
import Queue from "./pages/Queue";
import { api } from "./lib/api";

const qc = new QueryClient();

function StatusBar() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 15000 });
  return (
    <div className="mono flex items-center gap-3 border-b border-line bg-panel px-4 py-2 text-[12px] text-mut">
      <span className="font-bold text-txt">PRECINCT6 SOC</span>
      <span className="hidden xl:inline">ventana 26 jul – 01 ago 2024 · 19 productos · 4 orgs en vivo</span>
      <span className="ml-auto flex items-center gap-2">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ background: data?.loaded ? "#3aa88f" : "#d99a2b" }}
        />
        {data ? `${data.model} · ${data.loaded ? "modelo cargado" : "stub sin pkl"}` : "conectando a :8000…"}
      </span>
    </div>
  );
}

function Shell() {
  const link = ({ isActive }: { isActive: boolean }) =>
    `rounded-md border px-3 py-1.5 text-sm ${isActive ? "border-line bg-panel text-txt" : "border-transparent text-mut hover:text-txt"}`;
  return (
    <div className="min-h-screen bg-ink text-txt">
      <StatusBar />
      <nav className="flex items-center gap-2 border-b border-line px-4 py-2">
        <NavLink to="/" className={link}>Cola</NavLink>
        <NavLink to="/panorama" className={link}>Panorama</NavLink>
        <NavLink to="/incidente" className={link}>Incidente</NavLink>
        <NavLink to="/grafo" className={link}>Grafo</NavLink>
        <NavLink to="/cobertura" className={link}>Cobertura MITRE</NavLink>
        <NavLink to="/lab" className={link}>Laboratorio</NavLink>
        <a className="mono ml-auto text-xs text-mut" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
          API docs
        </a>
      </nav>
      <main className="mx-auto max-w-[1400px] px-4 py-4">
        <Routes>
          <Route path="/" element={<Queue />} />
          <Route path="/panorama" element={<Panorama />} />
          <Route path="/incidente/:id?" element={<Incident />} />
          <Route path="/grafo" element={<Graph />} />
          <Route path="/cobertura" element={<Coverage />} />
          <Route path="/lab" element={<Lab />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Shell />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
