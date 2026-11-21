"""Public share page /s/{id}: self-contained HTML, escaped, no third-party scripts."""

from __future__ import annotations

from html import escape

from app.models import Episode

CSS = """
:root{--ink:#0d0c0b;--panel:#151311;--line:#2d2924;--paper:#f4ecdf;--dim:#b9ae9b;
--onair:#e8412a;--amber:#f2a93b}
*{box-sizing:border-box}
body{margin:0;background:var(--ink);color:var(--paper);
font:18px/1.55 "Iowan Old Style","Palatino Linotype",Georgia,serif}
main{max-width:680px;margin:0 auto;padding:48px 20px 64px}
.k{font:600 12px/1 ui-monospace,"SFMono-Regular",Menlo,monospace;letter-spacing:.14em;
text-transform:uppercase;color:var(--dim)}
.onair{display:inline-flex;align-items:center;gap:8px;color:var(--onair)}
.onair:before{content:"";width:9px;height:9px;border-radius:50%;background:var(--onair)}
h1{font-size:clamp(30px,6vw,46px);line-height:1.08;margin:18px 0 12px;font-weight:700}
p{margin:0 0 16px}.dim{color:var(--dim)}
audio{width:100%;margin:24px 0}
blockquote{margin:28px 0;padding:18px 20px;border-left:3px solid var(--amber);
background:var(--panel)}
blockquote .k{color:var(--amber);display:block;margin-bottom:8px}
hr{border:0;border-top:1px solid var(--line);margin:32px 0}
a{color:var(--paper);text-decoration-color:var(--amber);text-underline-offset:3px}
a:focus-visible{outline:2px solid var(--amber);outline-offset:2px}
.cta{display:inline-block;margin-top:12px;padding:12px 20px;background:var(--onair);
color:var(--ink);font:700 16px/1 system-ui,sans-serif;text-decoration:none;border-radius:4px}
ul{padding-left:20px}small{font-size:14px}
"""


def render_share_page(ep: Episode, audio_url: str, frontend_url: str, page_url: str) -> str:
    script = ep.script
    title = escape(script.title if script else "Episódio Contraponto")
    summary = escape(script.summary if script else "")
    verdict = escape(script.verdict if script else "")
    hosts = (
        f"{escape(script.hosts.HOST_1)} e {escape(script.hosts.HOST_2)}" if script else "Davi e Lia"
    )
    source_items = []
    for src in ep.sources:
        label = "Fonte primária" if src.role == "primaria" else "Material de confronto"
        name = escape(
            src.title or src.url or ("texto enviado" if src.kind == "text" else "arquivo")
        )
        author = f" — {escape(src.author)}" if src.author else ""
        link = (
            f'<a href="{escape(src.url, quote=True)}" rel="noopener noreferrer">{name}</a>'
            if src.url
            else name
        )
        source_items.append(f"<li>{label}: {link}{author}</li>")
    audio_tag = (
        f'<audio controls preload="metadata" src="{escape(audio_url, quote=True)}"></audio>'
        if ep.audio
        else '<p class="dim">O áudio deste episódio ainda não foi gerado.</p>'
    )
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · Contraponto</title>
<meta name="description" content="{summary}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{summary}">
<meta property="og:type" content="music.song">
<meta property="og:url" content="{escape(page_url, quote=True)}">
<meta property="og:audio" content="{escape(audio_url, quote=True)}">
<meta property="og:audio:type" content="audio/mpeg">
<meta name="robots" content="noindex">
<style>{CSS}</style></head>
<body><main>
<span class="k onair">Contraponto · episódio</span>
<h1>{title}</h1>
<p class="dim">{summary}</p>
<p class="k">Com {hosts} · Vozes sintéticas · Gerado com IA</p>
{audio_tag}
<blockquote><span class="k">Veredito do episódio</span>{verdict}</blockquote>
<hr>
<p class="k">Fontes</p>
<ul>{"".join(source_items)}</ul>
<p><small class="dim">Episódio gerado com IA. As vozes são sintéticas. As conclusões são deste
episódio e podem divergir das fontes originais. Disponível por até 24 horas.</small></p>
<a class="cta" href="{escape(frontend_url, quote=True)}">Criar o seu</a>
</main></body></html>"""


def render_not_found(frontend_url: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Episódio expirado · Contraponto</title><style>{CSS}</style></head>
<body><main><span class="k onair">Fora do ar</span>
<h1>Esse episódio expirou.</h1>
<p class="dim">Os episódios ficam disponíveis por 24 horas. Peça a quem compartilhou que envie o
MP3, ou crie um episódio novo.</p>
<a class="cta" href="{escape(frontend_url, quote=True)}">Criar o seu</a>
</main></body></html>"""
