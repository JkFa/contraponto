import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { formatClock } from "../lib/format";
import { IconBack15, IconFwd15, IconPause, IconPlay } from "./Icons";

const BARS = 96;
const SPEEDS = [0.75, 1, 1.25, 1.5, 2];
type PlayerState = "loading" | "paused" | "playing" | "buffering" | "error";

async function computePeaks(src: string): Promise<number[] | null> {
  try {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!AC) return null;
    const buf = await (await fetch(src)).arrayBuffer();
    const ctx = new AC();
    const audio = await ctx.decodeAudioData(buf);
    void ctx.close();
    const data = audio.getChannelData(0);
    const size = Math.floor(data.length / BARS);
    const peaks: number[] = [];
    for (let b = 0; b < BARS; b++) {
      let sum = 0;
      for (let i = b * size; i < (b + 1) * size; i += 64) sum += Math.abs(data[i] ?? 0);
      peaks.push(sum / Math.max(1, size / 64));
    }
    const max = Math.max(...peaks, 0.0001);
    return peaks.map((p) => Math.max(0.06, p / max));
  } catch {
    return null;
  }
}

/** Big player: play/pause, ±15 s, speed, waveform scrubber, tape counter. Keys: Space, ←/→. */
export function Player({ src, title, initialDuration = 0 }: { src: string; title: string; initialDuration?: number }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [state, setState] = useState<PlayerState>("loading");
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(initialDuration);
  const [speed, setSpeed] = useState(1);
  const [peaks, setPeaks] = useState<number[] | null>(null);

  useEffect(() => {
    let alive = true;
    computePeaks(src).then((p) => { if (alive) setPeaks(p); });
    return () => { alive = false; };
  }, [src]);

  const toggle = useCallback(() => {
    const a = audioRef.current;
    if (!a) return;
    if (a.paused) a.play().catch(() => setState("error"));
    else a.pause();
  }, []);

  const seekBy = useCallback((delta: number) => {
    const a = audioRef.current;
    if (!a) return;
    a.currentTime = Math.max(0, Math.min((a.duration || duration) - 0.05, a.currentTime + delta));
  }, [duration]);

  const onKey = (e: KeyboardEvent) => {
    const tag = (e.target as HTMLElement).tagName;
    if (tag === "SELECT") return;
    if (e.key === " " && tag !== "BUTTON") { e.preventDefault(); toggle(); }
    if (e.key === "ArrowLeft" && tag !== "INPUT") { e.preventDefault(); seekBy(-5); }
    if (e.key === "ArrowRight" && tag !== "INPUT") { e.preventDefault(); seekBy(5); }
  };

  useEffect(() => {
    // Global shortcuts when nothing editable has focus.
    const handler = (e: globalThis.KeyboardEvent) => {
      const el = document.activeElement as HTMLElement | null;
      if (el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT", "BUTTON", "A"].includes(el.tagName))) return;
      if (e.key === " ") { e.preventDefault(); toggle(); }
      else if (e.key === "ArrowLeft") seekBy(-5);
      else if (e.key === "ArrowRight") seekBy(5);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggle, seekBy]);

  const progress = duration ? time / duration : 0;
  const playing = state === "playing";
  return (
    <section className="player" aria-label={`Player: ${title}`} onKeyDown={onKey}>
      <audio ref={audioRef} src={src} preload="metadata"
        onLoadedMetadata={(e) => { setDuration(e.currentTarget.duration || initialDuration); setState("paused"); }}
        onCanPlay={() => setState((s) => (s === "loading" || s === "buffering" ? (audioRef.current?.paused ? "paused" : "playing") : s))}
        onPlay={() => setState("playing")} onPause={() => setState("paused")}
        onWaiting={() => setState("buffering")} onPlaying={() => setState("playing")}
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
        onEnded={() => setState("paused")} onError={() => setState("error")} />

      <div className="player__deck">
        <button type="button" className="player__btn" onClick={() => seekBy(-15)} aria-label="Voltar 15 segundos">
          <IconBack15 width={26} height={26} />
        </button>
        <button type="button" className={`player__play${playing ? " is-playing" : ""}`} onClick={toggle}
          aria-label={playing ? "Pausar" : "Tocar"} disabled={state === "error"}>
          {playing ? <IconPause width={30} height={30} /> : <IconPlay width={30} height={30} />}
        </button>
        <button type="button" className="player__btn" onClick={() => seekBy(15)} aria-label="Avançar 15 segundos">
          <IconFwd15 width={26} height={26} />
        </button>
      </div>

      <div className="wave">
        <div className="wave__bars" aria-hidden="true">
          {(peaks ?? Array.from({ length: BARS }, (_, i) => 0.25 + 0.2 * Math.abs(Math.sin(i * 0.7)))).map((p, i) => (
            <span key={i} className={i / BARS < progress ? "is-played" : ""} style={{ height: `${Math.round(p * 100)}%` }} />
          ))}
        </div>
        <input type="range" className="wave__range" min={0} max={duration || 0} step={0.1} value={Math.min(time, duration || 0)}
          aria-label="Posição no episódio" aria-valuetext={`${formatClock(time)} de ${formatClock(duration)}`}
          onChange={(e) => { if (audioRef.current) audioRef.current.currentTime = Number(e.target.value); }} />
      </div>

      <div className="player__foot">
        <p className="counter mono" aria-hidden="true">{formatClock(time)} / {formatClock(duration)}</p>
        <p className="player__state" aria-live="polite">
          {state === "loading" && "Carregando o áudio…"}
          {state === "buffering" && "Carregando…"}
          {state === "error" && "Não consegui tocar o áudio. Tente baixar o MP3."}
        </p>
        <label className="speed">
          <span className="visually-hidden">Velocidade</span>
          <select className="select" value={speed}
            onChange={(e) => { const v = Number(e.target.value); setSpeed(v); if (audioRef.current) audioRef.current.playbackRate = v; }}>
            {SPEEDS.map((s) => <option key={s} value={s}>{String(s).replace(".", ",")}×</option>)}
          </select>
        </label>
      </div>
    </section>
  );
}
