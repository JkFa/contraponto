"""Text clean-up before TTS (docs/04 §5)."""

from __future__ import annotations

import re

UNITS = [
    "zero",
    "um",
    "dois",
    "três",
    "quatro",
    "cinco",
    "seis",
    "sete",
    "oito",
    "nove",
    "dez",
    "onze",
    "doze",
    "treze",
    "quatorze",
    "quinze",
    "dezesseis",
    "dezessete",
    "dezoito",
    "dezenove",
]
TENS = [
    "",
    "",
    "vinte",
    "trinta",
    "quarenta",
    "cinquenta",
    "sessenta",
    "setenta",
    "oitenta",
    "noventa",
]
HUNDREDS = [
    "",
    "cento",
    "duzentos",
    "trezentos",
    "quatrocentos",
    "quinhentos",
    "seiscentos",
    "setecentos",
    "oitocentos",
    "novecentos",
]
SCALES = [(10**9, "bilhão", "bilhões"), (10**6, "milhão", "milhões")]
ACRONYMS = {"IA": "I A", "EUA": "É U A", "UE": "U E", "TV": "tê vê", "PT-BR": "português"}


def _below_1000(n: int) -> str:
    if n < 20:
        return UNITS[n]
    if n < 100:
        tens, unit = divmod(n, 10)
        return TENS[tens] + (f" e {UNITS[unit]}" if unit else "")
    if n == 100:
        return "cem"
    hundreds, rest = divmod(n, 100)
    return HUNDREDS[hundreds] + (f" e {_below_1000(rest)}" if rest else "")


def number_to_words(n: int) -> str:
    """Cardinal number in pt-BR (0 – 999 999 999 999)."""
    if n < 0:
        return "menos " + number_to_words(-n)
    if n < 1000:
        return _below_1000(n)
    parts: list[str] = []
    rest = n
    for value, singular, plural in SCALES:
        if rest >= value:
            q, rest = divmod(rest, value)
            parts.append(f"{number_to_words(q)} {singular if q == 1 else plural}")
    if rest >= 1000:
        q, rest = divmod(rest, 1000)
        parts.append("mil" if q == 1 else f"{_below_1000(q)} mil")
    if rest:
        joiner = "e " if rest < 100 or rest % 100 == 0 else ""
        parts.append(joiner + _below_1000(rest))
    return " ".join(parts)


def _money(match: re.Match[str]) -> str:
    raw = match.group(1).replace(".", "")
    reais, _, cents = raw.partition(",")
    value = int(reais or "0")
    text = f"{number_to_words(value)} {'real' if value == 1 else 'reais'}"
    if cents and int(cents):
        c = int(cents.ljust(2, "0")[:2])
        text += f" e {number_to_words(c)} {'centavo' if c == 1 else 'centavos'}"
    return text


def _percent(match: re.Match[str]) -> str:
    whole, _, frac = match.group(1).partition(",")
    text = number_to_words(int(whole))
    if frac:
        text += " vírgula " + " ".join(UNITS[int(d)] for d in frac)
    return f"{text} por cento"


def tts_prepare(text: str) -> str:
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    text = re.sub(r"R\$\s?(\d[\d.]*(?:,\d{1,2})?)", _money, text)
    text = re.sub(r"(\d+(?:,\d+)?)\s?%", _percent, text)
    text = text.replace("%", " por cento")
    for acronym, spoken in ACRONYMS.items():
        text = re.sub(rf"\b{re.escape(acronym)}\b", spoken, text)
    text = text.replace("&", " e ")
    return re.sub(r"\s+", " ", text).strip()
