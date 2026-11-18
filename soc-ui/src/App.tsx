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
    <div className="flex items-center gap-4 border-b border-line bg-ink px-4 py-3 text-[13px] text-mut">
      <span className="text-[19px] font-bold tracking-tight text-txt">PRECINCT<span className="text-acid">/6</span> <span className="font-normal text-mut">triage</span></span>
      <span className="hidden text-[14px] md:inline">26 jul – 01 ago 2024 · 19 productos · 4 orgs</span>
      <span className="ml-auto flex items-center gap-2">
        <span
          className="inline-block h-1.5 w-1.5 rounded-full"
          style={{ background: data?.loaded ? "#d7ff3e" : "#e9a13b" }}
        />
        <span className="font-mono text-[11px]">{data ? `${data.model} · ${data.loaded ? "listo" : "stub sin pkl"}` : "conectando a :8000…"}</span>
      </span>
    </div>
  );
}

function Shell() {
  const link = ({ isActive }: { isActive: boolean }) =>
    `px-1 py-2 text-[14px] ${isActive ? "text-txt underline decoration-acid decoration-2 underline-offset-8" : "text-mut hover:text-txt"}`;
  return (
    <div className="min-h-screen bg-ink text-txt">
      <StatusBar />
      <nav className="flex items-center gap-5 border-b border-line px-4">
        <NavLink to="/" className={link}>Cola</NavLink>
        <NavLink to="/panorama" className={link}>Panorama</NavLink>
        <NavLink to="/incidente" className={link}>Incidente</NavLink>
        <NavLink to="/grafo" className={link}>Grafo</NavLink>
        <NavLink to="/cobertura" className={link}>Cobertura</NavLink>
        <NavLink to="/lab" className={link}>Lab</NavLink>
      </nav>
      <main className="mx-auto max-w-[1480px] px-4 py-5">
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
