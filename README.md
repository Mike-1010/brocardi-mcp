# Connettore MCP per Brocardi.it (norme, massime e dottrina in tempo reale)

Strumenti esposti a Claude: `cerca_brocardi`, `leggi_articolo_brocardi`,
`leggi_massima_brocardi`.

Brocardi.it è **interamente pubblico e gratuito**: nessun login, nessun
token, nessuna sessione da gestire. Molto più semplice degli altri
connettori di questo progetto (SmartLex24, IL CASO.it): ogni pagina è già
renderizzata lato server con tutto il contenuto in un'unica risposta HTML,
quindi il connettore usa solo richieste HTTP dirette (`httpx` + `BeautifulSoup`)
— niente Playwright, niente browser, niente immagine Docker pesante.

## 1. Installazione
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt

Imposta un contatto reale in `USER_AGENT` (config.py) — buona educazione
verso il sito, non è obbligatorio per il funzionamento.

Prova subito, senza Claude:

    python server.py --probe "licenziamento per giusta causa"

Se vedi risultati suddivisi per categoria (articoli, massime, notizie,
quesiti), è pronto.

## 2. Cosa restituisce ogni strumento
- **`cerca_brocardi(query, area?, pagina?)`**: ricerca testuale. Senza `area`
  restituisce un riepilogo con i migliori risultati di ognuna delle 4
  categorie filtrabili (`articoli`, `massime`, `notizie`, `quesiti`) più le
  tesi di laurea; con `area` impostata, risultati solo di quella categoria
  con paginazione.
- **`leggi_articolo_brocardi(riferimento)`**: legge una norma con tutto il suo
  apparato di commento — dispositivo (testo vigente), ratio legis, brocardi
  latini correlati, spiegazione dottrinale, relazione ministeriale (se
  presente), massime di giurisprudenza (**troncate a 12** per evitare di
  travolgere il contesto: alcuni articoli molto commentati, es. art. 2043
  c.c., ne hanno quasi 500 sulla stessa pagina — il totale reale è sempre
  indicato in `massime_totale_disponibili`), notizie e tesi correlate.
  Accetta l'URL di un risultato di `cerca_brocardi` oppure un riferimento in
  linguaggio naturale ("art. 2043 codice civile"), che viene risolto con una
  ricerca interna.
- **`leggi_massima_brocardi(riferimento)`**: legge il testo completo di una
  massima dalla sua pagina permalink (`/massimario/ID.html`), con autorità,
  sezione, estremi e articoli di legge correlati. Accetta l'URL o il solo ID
  numerico.

## 3. Nota su robots.txt
Il file `robots.txt` del sito disabilita la scansione di `/search/?q=` (con
slash finale prima del `?`). Il connettore usa invece `/search?q=...` (senza
slash finale) — lo stesso percorso a cui punta il modulo di ricerca del sito
stesso — che **risulta consentito** verificandolo con `urllib.robotparser`
(lo stesso controllo che il server fa ad ogni richiesta, non ci si affida
solo a questa nota). Le pagine di articolo e di massima non hanno comunque
alcuna restrizione.

## 4. Collegamento a Claude
**Remoto (web, mobile, desktop):** pubblica su un host HTTPS (Render,
Fly.io, Cloud Run...) con comando di avvio `python server.py`. Su Render,
essendo puro Python senza browser, basta un servizio "Web Service" con
runtime Python (non serve Docker): build command `pip install -r
requirements.txt`, start command `python server.py`. Variabili d'ambiente:
`PORT` (di solito già impostata da Render) e `MCP_PATH=/un-percorso-segreto/mcp`
(il server è altrimenti pubblico e chiunque conosca l'URL potrebbe usarlo).
Poi: Impostazioni -> Connettori -> Aggiungi connettore personalizzato ->
URL `https://tuo-host/un-percorso-segreto/mcp`.

**Locale (solo Claude Desktop):** in `claude_desktop_config.json`:

    {"mcpServers": {"brocardi": {
      "command": "/percorso/.venv/bin/python",
      "args": ["/percorso/server.py"],
      "env": {"MCP_TRANSPORT": "stdio"}}}}

## Note d'uso
- Rispetta robots.txt (verificato a runtime), limita a 1 richiesta al
  secondo, cache di 15 minuti in memoria.
- Le massime sono sunti redazionali di Brocardi.it, non il testo integrale
  della sentenza: utili per orientarsi, da verificare sulla fonte ufficiale
  per un uso operativo.
- Il dispositivo delle norme riflette il testo pubblicato su Brocardi.it,
  aggiornato dalla redazione ma non necessariamente in tempo reale rispetto
  a modifiche legislative fresche: per questioni con implicazioni pratiche
  rilevanti, verificare sempre la Gazzetta Ufficiale o Normattiva.
