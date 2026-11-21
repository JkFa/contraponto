// Mirrors docs/03-API.md §1 — keep identical.
export type Mode = "critica" | "react";
export type Tone = "descontraido" | "analitico" | "provocativo";
export type Status =
  | "created" | "ingesting" | "scripting" | "script_ready"
  | "rendering" | "ready" | "failed";
export type SourceRole = "primaria" | "confronto";
export type VerificationStatus = "apoiada" | "contestada" | "parcial" | "nao_verificavel";
export type TurnKind = "contexto" | "citacao" | "confronto" | "opiniao" | "pergunta" | "transicao";

export interface Turn {
  speaker: "HOST_1" | "HOST_2";
  text: string;
  kind: TurnKind;
  role?: SourceRole | null;
  source_ts?: string | null;
}

export interface VerificationItem {
  claim: string;
  claim_ts?: string | null;
  status: VerificationStatus;
  note: string;
  evidence_role: SourceRole | "interna";
}

export interface Script {
  title: string;
  summary: string;
  hosts: { HOST_1: string; HOST_2: string };
  turns: Turn[];
  verification: VerificationItem[];
  verdict: string;
  fidelity_notes: string[];
}

export interface Source {
  role: SourceRole;
  kind: "youtube" | "text" | "file";
  title?: string | null;
  author?: string | null;
  url?: string | null;
  has_timestamps: boolean;
  char_count: number;
}

export interface Episode {
  id: string;
  status: Status;
  mode: Mode;
  created_at: string;
  expires_at: string;
  sources: Source[];
  script?: Script | null;
  audio?: { url: string; duration_s: number; bytes: number } | null;
  share_url?: string | null;
  error?: { code: string; message: string } | null;
}

export interface ProgressEvent {
  status: Status;
  step: string;
  pct: number;
}

export type EpisodeEvent =
  | { type: "progress"; data: ProgressEvent }
  | { type: "done"; data: { status: Status } }
  | { type: "error"; data: { code: string; message: string } };

export type SourceInput =
  | { kind: "youtube"; url: string }
  | { kind: "text"; text: string }
  | { kind: "file"; file: File };

export interface CreateEpisodeForm {
  mode: Mode;
  primary: SourceInput;
  confronto?: SourceInput | null;
  thesis?: string;
  focus_points?: string;
  duration_min?: 3 | 5 | 8 | 12;
  tone?: Tone;
  host1_name?: string;
  host2_name?: string;
}
