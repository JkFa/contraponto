import { useEffect, useState } from "react";
import { HashRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import { BRAND } from "./brand";
import { IconMoon, IconSun } from "./components/Icons";
import { OnAirProvider, OnAirSign, useOnAir } from "./components/OnAir";
import { ToastProvider } from "./components/Toast";
import Episode from "./routes/Episode";
import History from "./routes/History";
import Home from "./routes/Home";
import Review from "./routes/Review";
import Studio from "./routes/Studio";

type Theme = "dark" | "light";
const THEME_KEY = "contraponto.theme";

function initialTheme(): Theme {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") return saved;
  } catch { /* ignore */ }
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function Header() {
  const { live } = useOnAir();
  const [theme, setTheme] = useState<Theme>(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem(THEME_KEY, theme); } catch { /* ignore */ }
  }, [theme]);
  return (
    <header className="masthead">
      <Link to="/" className="wordmark" aria-label={`${BRAND.name}, início`}>{BRAND.name}</Link>
      <OnAirSign live={live} />
      <nav className="masthead__nav" aria-label="Principal">
        <NavLink to="/" end>Novo</NavLink>
        <NavLink to="/historico">Histórico</NavLink>
        <button type="button" className="theme-toggle" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label={theme === "dark" ? "Usar tema claro" : "Usar tema escuro"}>
          {theme === "dark" ? <IconSun /> : <IconMoon />}
        </button>
      </nav>
    </header>
  );
}

function NotFound() {
  return (
    <div className="page page--narrow empty-state">
      <h1>Essa página não existe.</h1>
      <Link className="btn btn--primary" to="/">Ir para o início</Link>
    </div>
  );
}

export default function App() {
  return (
    <HashRouter>
      <ToastProvider>
        <OnAirProvider>
          <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>
            Pular para o conteúdo
          </a>
          <Header />
          <main id="main" tabIndex={-1}>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/e/:id" element={<Studio />} />
              <Route path="/e/:id/revisar" element={<Review />} />
              <Route path="/e/:id/ouvir" element={<Episode />} />
              <Route path="/historico" element={<History />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
          <footer className="colophon">
            <p>{BRAND.name} examina materiais com IA e vozes sintéticas. As conclusões são de cada episódio e podem divergir das fontes originais.</p>
          </footer>
        </OnAirProvider>
      </ToastProvider>
    </HashRouter>
  );
}
