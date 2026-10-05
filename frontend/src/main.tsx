import React, { lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import App from "./App";
import "./index.css";
import "./appearance.css";
import "./account.css";
const AccountApp = lazy(() => import("./AccountApp"));
const PublicBooking = lazy(() => import("./PublicBooking"));
const EmailPreferences = lazy(() => import("./EmailPreferences"));

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/preferencias/:token" element={<Suspense fallback={<p role="status">Carregando…</p>}><EmailPreferences /></Suspense>} />
        {import.meta.env.VITE_DEMO_MODE !== "true" && <Route
          path="/agendar/:tenant"
          element={
            <Suspense fallback={<p role="status">Carregando serviços…</p>}>
              <PublicBooking />
            </Suspense>
          }
        />}
        <Route
          path="/conta/*"
          element={
            <Suspense
              fallback={
                <p role="status" className="account-page">
                  Carregando sua conta…
                </p>
              }
            >
              <AccountApp />
            </Suspense>
          }
        />
        <Route
          path="*"
          element={
            import.meta.env.VITE_DEMO_MODE !== "true" ? (
              <Navigate to="/conta" replace />
            ) : (
              <App />
            )
          }
        />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .catch(() => console.warn("Registro PWA indisponível."));
  });
}
