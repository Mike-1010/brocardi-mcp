"""Connettore MCP per la ricerca e la lettura ragionata di norme, massime di
giurisprudenza e commenti dottrinali su Brocardi.it.

Brocardi.it è interamente pubblico: nessun login, nessun token, nessuna
sessione da mantenere. Ogni pagina di articolo/norma è già renderizzata lato
server con tutti i contenuti in un'unica risposta HTML (dispositivo della
norma, ratio legis, brocardi latini correlati, spiegazione dottrinale,
relazione ministeriale, massime di giurisprudenza, notizie e tesi correlate),
quindi il connettore usa solo richieste HTTP dirette (nessun browser).

Avvio remoto (connettore personalizzato di Claude):
    python server.py                       # http://0.0.0.0:8000/mcp
Avvio locale (Claude Desktop):
    MCP_TRANSPORT=stdio python server.py
Prova da riga di comando, senza Claude:
    python server.py --probe "licenziamento per giusta causa"
"""
import argparse
import asyncio
import json
import os
import re
import time
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

import config

INSTRUCTIONS = (
    "Accesso in tempo reale a Brocardi.it: codici e leggi italiane commentate "
    "articolo per articolo (dispositivo, ratio legis, brocardi latini "
    "correlati, spiegazione dottrinale, relazione ministeriale, massime di "
    "giurisprudenza), oltre a notizie giuridiche, consulenze legali e tesi di "
    "laurea. Contenuto interamente pubblico e gratuito, nessun abbonamento.\n\n"
    "Flusso consigliato per rispondere a una domanda giuridica: usa prima "
    "`cerca_brocardi` (senza filtro 'area', per vedere di che tipo di "
    "materiale si dispone: norme, giurisprudenza, notizie, consulenze), poi "
    "`leggi_articolo_brocardi` sulla norma pertinente per avere il testo "
    "aggiornato E le massime di giurisprudenza che lo interpretano, citando "
    "sempre gli estremi (numero di articolo, codice/legge, estremi delle "
    "sentenze). Usa `leggi_massima_brocardi` quando serve il testo completo "
    "di una singola massima trovata nella ricerca o elencata in un articolo. "
    "Le massime sono sunti redazionali: per un giudizio operativo, invita "
    "comunque a verificare il testo integrale della sentenza sulla fonte "
    "ufficiale. Nota: `leggi_articolo_brocardi` limita il numero di massime "
    "restituite (alcuni articoli molto commentati, es. art. 2043 c.c., ne "
    "hanno centinaia); il conteggio totale è sempre indicato, e si può "
    "approfondire una singola massima con `leggi_massima_brocardi`."
)

mcp = FastMCP(
    "brocardi",
    instructions=INSTRUCTIONS,
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
    # Consiglio: imposta MCP_PATH a un percorso segreto, es. /k3j9x-mcp
    streamable_http_path=os.getenv("MCP_PATH", "/mcp"),
)

# ---------------------------------------------------------------- HTTP layer
_client = httpx.AsyncClient(
    headers={"User-Agent": config.USER_AGENT, "Accept-Language": "it-IT,it;q=0.9"},
    timeout=config.TIMEOUT,
    follow_redirects=True,
)
_lock = asyncio.Lock()
_last_request = 0.0
_cache: dict[str, tuple[float, str]] = {}
_robots: robotparser.RobotFileParser | None = None


async def _allowed(url: str) -> bool:
    """Rispetta robots.txt del sito (verificato: consente /search senza slash
    finale, cioè il percorso che usiamo qui - vedi nota in config.py)."""
    global _robots
    if _robots is None:
        rp = robotparser.RobotFileParser()
        try:
            r = await _client.get(urljoin(config.BASE, "/robots.txt"))
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except httpx.HTTPError:
            rp.parse([])
        _robots = rp
    return _robots.can_fetch(config.USER_AGENT, url)


async def fetch(url: str, params: dict | None = None) -> str:
    """GET generico e cortese (rate limit + cache in memoria + robots.txt)."""
    global _last_request
    key = url + "?" + json.dumps(params or {}, sort_keys=True)
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < config.CACHE_TTL:
        return hit[1]
    check_url = url if not params else str(httpx.URL(url, params=params))
    if not await _allowed(check_url):
        raise PermissionError(f"robots.txt del sito non consente l'accesso a {check_url}")
    async with _lock:
        wait = config.MIN_INTERVAL - (time.monotonic() - _last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            r = await _client.get(url, params=params)
        finally:
            _last_request = time.monotonic()
    r.raise_for_status()
    text = r.text
    _cache[key] = (time.monotonic(), text)
    return text


async def _jump_to_articolo(numero: str, codice: str) -> tuple[str, str] | None:
    """Segue il meccanismo 'vai all'articolo' del sito (POST /articolo.php con
    "numero" e "codice"), verificato via browser il 29/09/2026: risponde con
    un redirect diretto alla pagina canonica dell'articolo. Molto più
    affidabile della ricerca testuale per riferimenti "art. N <fonte>".
    Restituisce (url_finale, html) oppure None se il salto non porta a una
    vera pagina di articolo (numero/codice non esistente in quella fonte)."""
    global _last_request
    if not await _allowed(config.ARTICOLO_JUMP_URL):
        return None
    async with _lock:
        wait = config.MIN_INTERVAL - (time.monotonic() - _last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            r = await _client.post(
                config.ARTICOLO_JUMP_URL, data={"numero": numero, "codice": codice}
            )
        finally:
            _last_request = time.monotonic()
    if r.status_code >= 400:
        return None
    final_url = str(r.url)
    # Il salto fallito ricarica semplicemente la pagina del codice (niente
    # "artNNN.html" nel percorso finale): lo trattiamo come "non trovato".
    if not re.search(r"/art[\w-]*\.html", urlparse(final_url).path):
        return None
    return final_url, r.text


_ART_RIFERIMENTO_RE = re.compile(
    r"art(?:icol[oi])?\.?\s*(\d+\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies)?)"
    r"\s+(?:del\s+|della\s+|dell[oa']\s*)?(.+)$",
    re.IGNORECASE,
)


def _resolve_codice(nome: str) -> str | None:
    nome = _clean(nome).lower().rstrip(",;: ")
    if nome in config.CODICE_MAP:
        return config.CODICE_MAP[nome]
    # riprova togliendo un eventuale punto finale (ma non i punti interni:
    # servono per sigle come "c.c." o "t.u.p.i.")
    return config.CODICE_MAP.get(nome.rstrip("."))


async def _try_direct_jump(riferimento: str) -> tuple[str, str] | None:
    """Se `riferimento` è del tipo 'art. 2043 codice civile', prova il salto
    diretto via /articolo.php invece della ricerca testuale. Restituisce
    (url, html) se riuscito, altrimenti None (si ricorre alla ricerca)."""
    m = _ART_RIFERIMENTO_RE.match(_clean(riferimento))
    if not m:
        return None
    numero, resto = m.group(1), m.group(2)
    codice = _resolve_codice(resto)
    if not codice:
        return None
    try:
        return await _jump_to_articolo(numero, codice)
    except httpx.HTTPError:
        return None


# ------------------------------------------------------------------- Parsing
def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _abs_url(href: str) -> str:
    return urljoin(config.BASE, href or "")


def _is_brocardi_url(s: str) -> bool:
    if s.startswith("/") and ".html" in s:
        return True
    try:
        return urlparse(s).netloc.endswith("brocardi.it")
    except ValueError:
        return False


# --- Ricerca -----------------------------------------------------------------
_AREA_LABELS = {
    "negli articoli": "articoli",
    "nel massimario": "massime",
    "nelle notizie giuridiche": "notizie",
    "nelle consulenze legali": "quesiti",
    "nelle tesi di laurea": "tesi",
}


def _parse_search_results(html_text: str) -> dict:
    """Analizza la pagina /search, che raggruppa i risultati in blocchi
    (uno per categoria), ciascuno <div class="search_content ..."> con un
    <h3>Trovati N risultati <categoria></h3> e una <ul> di risultati.
    Struttura per categoria (verificata via browser il 29/09/2026):
      - articoli: <li><a>titolo</a></li>
      - massime:  <li><strong><a>estremi</a></strong><div class="massima-preview">estratto</div></li>
      - notizie:  <li><a>titolo - data</a></li>
      - quesiti:  <li><strong><a>titolo</a></strong><br><div class="quesito-preview">estratto</div></li>
      - tesi:     <li><strong><a>titolo</a></strong><br><div class="tesi-preview">estratto</div></li>
    """
    soup = BeautifulSoup(html_text, "html.parser")
    out: dict[str, dict] = {}
    for block in soup.select("div.search_content"):
        h3 = block.find("h3")
        if not h3:
            continue
        heading = _clean(h3.get_text())
        area = next((v for k, v in _AREA_LABELS.items() if k in heading), None)
        if not area:
            continue
        m = re.search(r"Trovati\s+(\d+)", heading)
        totale = int(m.group(1)) if m else None
        items = []
        for li in block.select("ul > li"):
            a = li.find("a")
            if not a:
                continue
            titolo = _clean(a.get_text())
            url = _abs_url(a.get("href", ""))
            preview = li.find("div", class_=re.compile(r"(massima|quesito|tesi)-preview"))
            estratto = _clean(preview.get_text()) if preview else None
            items.append({"titolo": titolo, "url": url, "estratto": estratto})
        out[area] = {"totale_trovati": totale, "risultati": items}
    return out


async def _search(query: str, area: str | None, pagina: int) -> dict:
    params = {"q": query}
    if area:
        params["area"] = area
        if pagina and pagina > 1:
            params["page"] = pagina
    try:
        html_text = await fetch(config.SEARCH_URL, params=params)
    except (httpx.HTTPError, PermissionError) as e:
        return {"errore": f"Ricerca non riuscita: {e}"}
    parsed = _parse_search_results(html_text)
    cap = config.MAX_RISULTATI_AREA_SINGOLA if area else config.MAX_RISULTATI_PER_AREA
    for a in parsed.values():
        a["risultati"] = a["risultati"][:cap]
    res = {"query": query, "area": area or "tutte", "pagina": pagina, "per_categoria": parsed}
    if not parsed:
        res["nota"] = "Nessun risultato in nessuna categoria. Prova termini più generici."
    return res


# --- Pagina di un articolo/norma ---------------------------------------------
def _section_map(soup: BeautifulSoup) -> dict[str, list]:
    """Le sezioni di una pagina-articolo (Dispositivo, Ratio Legis, Brocardi,
    Spiegazione, Relazione, Massime, Notizie correlate, Tesi correlate...)
    sono tutte intestazioni <h2>/<h3 class="tab-title">, seguite da elementi
    fratelli fino alla prossima intestazione dello stesso tipo (verificato via
    browser il 29/09/2026: non sono tab caricate via JS, è tutto nella stessa
    pagina)."""
    sections: dict[str, list] = {}
    for h in soup.select(".tab-title"):
        label = _clean(h.get_text())
        nodes = []
        node = h.find_next_sibling()
        while node is not None and "tab-title" not in (node.get("class") or []):
            nodes.append(node)
            node = node.find_next_sibling()
        sections[label] = nodes
    return sections


def _section_text(sections: dict, *substrings: str, max_chars: int | None = None) -> str | None:
    for label, nodes in sections.items():
        if any(s.lower() in label.lower() for s in substrings):
            parts = []
            for n in nodes:
                if n.find("form"):  # es. box "scarica in PDF / iscriviti"
                    continue
                t = _clean(n.get_text())
                if t:
                    parts.append(t)
            text = "\n\n".join(parts)
            if not text:
                continue
            if max_chars and len(text) > max_chars:
                text = text[:max_chars] + "…"
            return text
    return None


def _parse_massime(sections: dict, limit: int) -> tuple[list, int]:
    """Ogni massima nella pagina-articolo è <div class="sentenza corpoDelTesto">
    con <p><strong>citazione breve</strong></p>, il testo della massima, e un
    <div class="extended-judgment"><a href="/massimario/ID.html">estremi
    completi</a></div> finale (verificato via browser il 29/09/2026)."""
    for label, nodes in sections.items():
        if not label.lower().startswith("massime"):
            continue
        tutte = []
        for n in nodes:
            tutte.extend(n.select(".sentenza"))
        totale = len(tutte)
        out = []
        for s in tutte[:limit]:
            strong = s.find("strong")
            citazione_breve = _clean(strong.get_text()) if strong else None
            ext = s.find("div", class_="extended-judgment")
            link = ext.find("a") if ext else None
            estremi_completi = _clean(link.get_text()) if link else None
            url = _abs_url(link.get("href", "")) if link else None
            testo = _clean(s.get_text())
            if citazione_breve:
                testo = testo.replace(citazione_breve, "", 1)
            if estremi_completi:
                testo = testo.replace(f"({estremi_completi})", "")
            out.append({
                "citazione": estremi_completi or citazione_breve,
                "massima": _clean(testo),
                "url": url,
            })
        return out, totale
    return [], 0


def _parse_brocardi_correlati(sections: dict) -> list:
    for label, nodes in sections.items():
        if label.strip() != "Brocardi":
            continue
        out = []
        for n in nodes:
            for item in n.select(".brocardi-content"):
                a = item.find("a")
                footer = item.find("div", class_="brocardi-footer")
                if a:
                    out.append({
                        "brocardo": _clean(a.get_text()),
                        "significato": _clean(footer.get_text()) if footer else None,
                        "url": _abs_url(a.get("href", "")),
                    })
        return out
    return []


def _parse_correlati_semplici(sections: dict, *substrings: str, limit: int = 10) -> list:
    """Notizie/tesi correlate: liste semplici <ul><li><a>titolo - data</a></li>."""
    for label, nodes in sections.items():
        if not any(s.lower() in label.lower() for s in substrings):
            continue
        out = []
        for n in nodes:
            for a in n.select("li a"):
                out.append({"titolo": _clean(a.get_text()), "url": _abs_url(a.get("href", ""))})
        return out[:limit]
    return []


def _parse_article_page(html_text: str, url: str) -> dict:
    soup = BeautifulSoup(html_text, "html.parser")
    h1 = soup.find("h1")
    titolo = _clean(h1.get_text()) if h1 else None
    fonte = None
    rubrica = None
    if h1:
        h2 = h1.find_next_sibling("h2")
        if h2 and "hbox-header" in (h2.get("class") or []):
            fonte = _clean(h2.get_text())
        h3 = h1.find_next_sibling("h3") or (h2.find_next_sibling("h3") if h2 else None)
        if h3:
            rubrica = _clean(h3.get_text())

    sections = _section_map(soup)
    dispositivo = _section_text(sections, "dispositivo", max_chars=config.MAX_CARATTERI_SEZIONE)
    ratio_legis = _section_text(sections, "ratio legis", max_chars=config.MAX_CARATTERI_SEZIONE)
    spiegazione = _section_text(sections, "spiegazione dell", max_chars=config.MAX_CARATTERI_SEZIONE)
    relazione = _section_text(sections, "relazione al", max_chars=config.MAX_CARATTERI_SEZIONE)
    brocardi_correlati = _parse_brocardi_correlati(sections)
    massime, massime_totale = _parse_massime(sections, config.MAX_MASSIME_ARTICOLO)
    notizie_correlate = _parse_correlati_semplici(sections, "notizie giuridiche correlate")
    tesi_correlate = _parse_correlati_semplici(sections, "tesi di laurea correlate")

    res = {
        "url": url,
        "titolo": titolo,
        "fonte_normativa": fonte,
        "rubrica": rubrica,
        "dispositivo": dispositivo,
        "ratio_legis": ratio_legis,
        "brocardi_correlati": brocardi_correlati or None,
        "spiegazione": spiegazione,
        "relazione_ministeriale": relazione,
        "massime": massime,
        "massime_totale_disponibili": massime_totale,
        "notizie_correlate": notizie_correlate or None,
        "tesi_correlate": tesi_correlate or None,
    }
    if massime_totale > len(massime):
        res["nota_massime"] = (
            f"Mostrate {len(massime)} massime su {massime_totale} disponibili in pagina. "
            "Usa leggi_massima_brocardi sull'url di una massima per il testo completo, "
            "oppure cerca_brocardi(area='massime') per una ricerca mirata su questo articolo."
        )
    if dispositivo is None:
        res["nota"] = "Pagina non riconosciuta come articolo di legge (struttura inattesa)."
    return res


# --- Singola massima (pagina /massimario/ID.html) ----------------------------
def _parse_massima_page(html_text: str, url: str) -> dict:
    soup = BeautifulSoup(html_text, "html.parser")
    h1 = soup.find("h1")
    spans = h1.find_all("span", recursive=False) if h1 else []
    giudice = _clean(spans[0].get_text()) if len(spans) > 0 else None
    sezione = _clean(spans[1].get_text()) if len(spans) > 1 else None
    estremi = _clean(spans[2].get_text()) if len(spans) > 2 else None

    massime = []
    for div in soup.select(".content-judgment .corpoDelTesto"):
        numero_h2 = div.find("h2", class_="numero-massima")
        numero = _clean(numero_h2.get_text()) if numero_h2 else None
        testo = _clean(div.get_text())
        if numero:
            testo = testo.replace(numero, "", 1).strip()
        massime.append({"numero": numero, "testo": _clean(testo)})

    articoli_correlati = []
    for h in soup.find_all(["h2", "h3"]):
        if _clean(h.get_text()) == "Articoli correlati":
            container = h.parent
            for a in container.select("ul a"):
                articoli_correlati.append({
                    "titolo": _clean(a.get_text()),
                    "url": _abs_url(a.get("href", "")),
                })
            break

    return {
        "url": url,
        "autorita": giudice,
        "sezione": sezione,
        "estremi": estremi,
        "massime": massime,
        "articoli_correlati": articoli_correlati or None,
    }


# --------------------------------------------------------------------- Tools
@mcp.tool()
async def cerca_brocardi(query: str, area: str | None = None, pagina: int = 1) -> dict:
    """Cerca su Brocardi.it: norme di legge commentate, massime di
    giurisprudenza, notizie giuridiche e consulenze legali (quesiti risolti).

    Senza `area`, restituisce un riepilogo con i migliori risultati di ogni
    categoria (utile per capire subito che tipo di materiale esiste su un
    argomento). Con `area` impostata a "articoli", "massime", "notizie" o
    "quesiti", restringe la ricerca a quella sola categoria e permette di
    scorrere le pagine successive con `pagina`.

    Per leggere il testo completo di un articolo trovato qui, passa il suo
    "url" a leggi_articolo_brocardi. Per una massima, passa il suo "url" a
    leggi_massima_brocardi.
    """
    if area is not None and area not in config.SEARCH_AREAS:
        return {"errore": f"'area' deve essere una di {config.SEARCH_AREAS} oppure omessa."}
    return await _search(query, area, max(1, pagina))


@mcp.tool()
async def leggi_articolo_brocardi(riferimento: str) -> dict:
    """Legge una norma/articolo di legge su Brocardi.it con tutto il suo
    apparato di commento: dispositivo (testo vigente), ratio legis, brocardi
    latini correlati, spiegazione dottrinale, relazione ministeriale (se
    presente) e le massime di giurisprudenza che lo interpretano (troncate a
    un tetto: il totale disponibile è sempre indicato).

    `riferimento` può essere:
    - un riferimento naturale con numero e fonte, es. "art. 2043 codice
      civile", "articolo 18 statuto dei lavoratori", "art. 2645 bis c.c."
      (consigliato: risolto con un salto diretto e affidabile, non con la
      ricerca testuale del sito, che per questo tipo di riferimento spesso
      sbaglia articolo);
    - l'"url" di un articolo restituito da cerca_brocardi;
    - un riferimento più descrittivo senza numero (es. "responsabilità
      extracontrattuale codice civile"): in questo caso viene cercato su
      Brocardi.it e si legge il primo risultato pertinente - meno affidabile,
      verifica sempre titolo e rubrica nel risultato.
    """
    riferimento = riferimento.strip()
    url = None
    html_text = None

    if _is_brocardi_url(riferimento):
        url = _abs_url(riferimento)
    else:
        jump = await _try_direct_jump(riferimento)
        if jump:
            url, html_text = jump

    if url is None:
        trovati = await _search(riferimento, "articoli", 1)
        risultati = trovati.get("per_categoria", {}).get("articoli", {}).get("risultati", [])
        if not risultati:
            return {
                "errore": f"Nessun articolo trovato per '{riferimento}'.",
                "suggerimento": "Prova con cerca_brocardi(area='articoli') usando termini diversi.",
            }
        url = risultati[0]["url"]
        note_ricerca = (
            "Risolto tramite ricerca testuale (non tramite salto diretto per numero "
            "articolo): verifica titolo e rubrica nel risultato prima di usarlo."
        )
    else:
        note_ricerca = None

    if html_text is None:
        try:
            html_text = await fetch(url)
        except (httpx.HTTPError, PermissionError) as e:
            return {"errore": f"Articolo non recuperabile: {e}", "url": url}
    res = _parse_article_page(html_text, url)
    if note_ricerca:
        res["nota_risoluzione"] = note_ricerca
    return res


@mcp.tool()
async def leggi_massima_brocardi(riferimento: str) -> dict:
    """Legge il testo completo di una massima di giurisprudenza dalla sua
    pagina permalink su Brocardi.it (/massimario/ID.html), inclusi autorità,
    sezione, estremi della decisione e gli articoli di legge correlati.

    `riferimento` può essere l'"url" di una massima restituito da
    cerca_brocardi o da leggi_articolo_brocardi, oppure il solo ID numerico
    (es. "5935").
    """
    riferimento = riferimento.strip()
    if riferimento.isdigit():
        url = f"{config.BASE}/massimario/{riferimento}.html"
    elif _is_brocardi_url(riferimento):
        url = _abs_url(riferimento)
    else:
        return {"errore": "Fornisci l'url di una massima (es. da cerca_brocardi) o il suo ID numerico."}
    try:
        html_text = await fetch(url)
    except (httpx.HTTPError, PermissionError) as e:
        return {"errore": f"Massima non recuperabile: {e}", "url": url}
    return _parse_massima_page(html_text, url)


# ---------------------------------------------------------------------- Main
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", help="esegue una ricerca di prova e stampa il JSON")
    args = ap.parse_args()
    if args.probe:
        print(json.dumps(asyncio.run(_search(args.probe, None, 1)), ensure_ascii=False, indent=2))
    else:
        mcp.run(transport=os.getenv("MCP_TRANSPORT", "streamable-http"))
