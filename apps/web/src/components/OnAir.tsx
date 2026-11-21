import { createContext, useContext, useState, type ReactNode } from "react";

interface OnAirApi { live: boolean; setLive: (v: boolean) => void }
const OnAirContext = createContext<OnAirApi>({ live: false, setLive: () => undefined });

export function OnAirProvider({ children }: { children: ReactNode }) {
  const [live, setLive] = useState(false);
  return <OnAirContext.Provider value={{ live, setLive }}>{children}</OnAirContext.Provider>;
}

export function useOnAir(): OnAirApi {
  return useContext(OnAirContext);
}

/** The studio "NO AR" sign: dark when idle, lit and pulsing while recording. */
export function OnAirSign({ live, size = "s" }: { live: boolean; size?: "s" | "l" }) {
  return (
    <span className={`onair onair--${size}${live ? " is-live" : ""}`} role="img"
      aria-label={live ? "No ar: o estúdio está trabalhando" : "Estúdio em silêncio"}>
      <span className="onair__lamp" aria-hidden="true" />
      <span className="onair__text" aria-hidden="true">No ar</span>
    </span>
  );
}
