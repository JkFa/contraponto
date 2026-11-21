"""Error codes and pt-BR messages (docs/03-API.md §4)."""

from __future__ import annotations

MESSAGES: dict[str, str] = {
    "INVALID_URL": "Esse link não parece ser do YouTube.",
    "TRANSCRIPT_UNAVAILABLE": (
        "Não consegui ler a transcrição da fonte primária. Cole o texto abaixo para continuar."
    ),
    "CONFRONTO_TRANSCRIPT_UNAVAILABLE": (
        "Não consegui ler a transcrição do material de confronto. "
        "Cole o texto ou remova essa fonte."
    ),
    "INPUT_TOO_LONG": "O material é longo demais. Tente um trecho de até 60 000 caracteres.",
    "FILE_UNSUPPORTED": "Envie um arquivo .txt, .srt ou .pdf com texto.",
    "PDF_NO_TEXT": "Esse PDF parece ser uma imagem escaneada. Cole o texto no lugar.",
    "MULTIPLE_CONFRONTO_INPUTS": (
        "Escolha só uma forma de enviar o material de confronto: link, texto ou arquivo."
    ),
    "MISSING_PRIMARY": "Envie a fonte primária: um link do YouTube, um texto ou um arquivo.",
    "MULTIPLE_PRIMARY_INPUTS": (
        "Escolha só uma forma de enviar a fonte primária: link, texto ou arquivo."
    ),
    "THESIS_REQUIRED": "No modo Crítica, escreva a sua tese (pode ser em tópicos soltos).",
    "VALIDATION_ERROR": "Algum campo veio num formato inesperado. Confira e tente de novo.",
    "LLM_FAILED": "A IA não respondeu direito. Tente de novo em instantes.",
    "LLM_NOT_CONFIGURED": (
        "A IA não está configurada neste servidor. Informe sua própria chave Gemini em Ajustes."
    ),
    "LLM_QUOTA": (
        "O limite gratuito da IA acabou por agora. Tente mais tarde ou use sua própria chave."
    ),
    "SCRIPT_INVALID": "O roteiro saiu fora do formato. Tente regenerar.",
    "CONTENT_REFUSED": "Não posso criar um episódio com esse material. Tente outro conteúdo.",
    "TTS_FAILED": "Não consegui gerar as vozes agora. Tente de novo.",
    "RATE_LIMITED": "Muitos pedidos. Espere um minuto.",
    "EXPIRED": "Esse episódio expirou.",
    "INVALID_STATE": "Essa ação não é possível no estado atual do episódio.",
    "NOT_READY": "Esse arquivo ainda não está pronto.",
    "INTERNAL": "Algo deu errado do nosso lado. Tente de novo.",
}


class ApiError(Exception):
    """Error carrying a stable code, an HTTP status and a pt-BR message."""

    def __init__(self, code: str, status: int = 400, message: str | None = None) -> None:
        self.code = code
        self.status = status
        self.message = message or MESSAGES.get(code, MESSAGES["INTERNAL"])
        super().__init__(code)

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}
