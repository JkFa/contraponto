"""Pydantic schemas mirroring docs/03-API.md §1."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["critica", "react"]
Tone = Literal["descontraido", "analitico", "provocativo"]
Status = Literal[
    "created", "ingesting", "scripting", "script_ready", "rendering", "ready", "failed"
]
SourceRole = Literal["primaria", "confronto"]
VerificationStatus = Literal["apoiada", "contestada", "parcial", "nao_verificavel"]
TurnKind = Literal["contexto", "citacao", "confronto", "opiniao", "pergunta", "transicao"]
Speaker = Literal["HOST_1", "HOST_2"]


class Turn(BaseModel):
    speaker: Speaker
    text: str = Field(min_length=1, max_length=600)
    kind: TurnKind
    role: SourceRole | None = None
    source_ts: str | None = None


class VerificationItem(BaseModel):
    claim: str = Field(min_length=1, max_length=220)
    claim_ts: str | None = None
    status: VerificationStatus
    note: str = Field(max_length=280)
    evidence_role: SourceRole | Literal["interna"]


class Hosts(BaseModel):
    HOST_1: str = Field(min_length=1, max_length=40)
    HOST_2: str = Field(min_length=1, max_length=40)


class Script(BaseModel):
    title: str = Field(min_length=1, max_length=90)
    summary: str = Field(max_length=280)
    hosts: Hosts
    turns: list[Turn] = Field(min_length=1)
    verification: list[VerificationItem]
    verdict: str = Field(max_length=300)
    fidelity_notes: list[str] = Field(default_factory=list)


class Source(BaseModel):
    role: SourceRole
    kind: Literal["youtube", "text", "file"]
    title: str | None = None
    author: str | None = None
    url: str | None = None
    has_timestamps: bool = False
    char_count: int = 0


class AudioInfo(BaseModel):
    url: str
    duration_s: float
    bytes: int


class ErrorInfo(BaseModel):
    code: str
    message: str


class Episode(BaseModel):
    id: str
    status: Status
    mode: Mode
    created_at: str
    expires_at: str
    sources: list[Source]
    script: Script | None = None
    audio: AudioInfo | None = None
    share_url: str | None = None
    error: ErrorInfo | None = None


class RegenerateBody(BaseModel):
    instructions: str | None = Field(default=None, max_length=1000)


class RenderBody(BaseModel):
    music: bool = False
