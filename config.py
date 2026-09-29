"""Configurazione del connettore Brocardi.it. Modifica qui, non in server.py."""
import os

BASE = "https://www.brocardi.it"

# Identificati in modo onesto: metti un contatto reale.
USER_AGENT = os.getenv(
    "BROCARDI_UA", "brocardi-mcp/0.1 (uso professionale personale; contatto: TUA_EMAIL)"
)

# Brocardi.it è interamente pubblico (nessun login, nessun abbonamento): ogni
# pagina di articolo/norma è già renderizzata lato server con tutti i
# contenuti (dispositivo, spiegazione, massime, brocardi latini correlati) in
# un'unica risposta HTML. Non serve un browser: bastano richieste HTTP dirette.
MIN_INTERVAL = 1.0   # secondi minimi tra due richieste al sito (cortesia)
CACHE_TTL = 900       # secondi di cache in memoria
TIMEOUT = 20

# --- Ricerca -----------------------------------------------------------------
# Endpoint di ricerca reale del sito, scoperto via browser il 29/09/2026:
# GET /search?q=<query>[&area=<categoria>][&page=<n>]
# "area" filtra per categoria di contenuto; valori osservati:
#   "articoli"  -> norme/articoli di legge commentati
#   "massime"   -> massime di giurisprudenza (massimario)
#   "notizie"   -> notizie giuridiche
#   "quesiti"   -> consulenze legali (quesiti risposti dalla redazione)
# Senza "area" il sito restituisce un riepilogo su tutte le categorie assieme
# (comprese le tesi di laurea, che però non hanno un valore "area" dedicato
# per la ricerca filtrata).
SEARCH_URL = f"{BASE}/search"
SEARCH_AREAS = ("articoli", "massime", "notizie", "quesiti")

# NOTA SU robots.txt (verificato il 29/09/2026): il sito disallow-a la
# scansione di "/search/?q=" (con slash finale prima del "?"), ma il form di
# ricerca del sito stesso invia le richieste a "/search" SENZA slash finale -
# esattamente il percorso che usiamo qui, ed è quindi consentito (lo si può
# verificare con urllib.robotparser). Il controllo _allowed() in server.py lo
# verifica comunque ad ogni avvio, invece di fidarsi ciecamente di questa nota.

# --- Limiti di dimensione delle risposte --------------------------------------
# Alcuni articoli molto commentati (es. art. 2043 c.c.) hanno centinaia di
# massime sulla stessa pagina (una pagina sola può superare 500 massime e
# 600KB di testo): vanno troncate, altrimenti un'unica lettura di articolo
# travolgerebbe il contesto della conversazione.
MAX_MASSIME_ARTICOLO = 12
MAX_RISULTATI_PER_AREA = 8    # quando si cerca su tutte le aree insieme
MAX_RISULTATI_AREA_SINGOLA = 15  # quando si specifica una singola "area"
MAX_CARATTERI_SEZIONE = 6000  # tetto per ogni sezione testuale lunga (es. spiegazione)
