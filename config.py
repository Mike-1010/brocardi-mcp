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

# --- Salto diretto a un articolo per numero -----------------------------------
# Scoperto via browser il 29/09/2026: la ricerca testuale generica (/search) è
# INAFFIDABILE per riferimenti tipo "art. 2043 codice civile" - il motore di
# ricerca del sito tratta tutto come full-text e spesso restituisce come primo
# risultato un articolo completamente estraneo che cita solo di sfuggita quei
# termini. Il sito però offre un meccanismo dedicato e affidabile: ogni pagina
# di un codice ha un form POST a /articolo.php con due campi, "numero" (es.
# "2043" o "2645 bis", spazio prima del suffisso) e "codice" (sigla breve della
# fonte), che risponde con un redirect diretto alla pagina canonica
# dell'articolo. Va preferito alla ricerca testuale ogni volta che il
# riferimento contiene sia un numero di articolo sia il nome di una fonte
# riconosciuta qui sotto.
ARTICOLO_JUMP_URL = f"{BASE}/articolo.php"

# Sigle raccolte dal menu a tendina del form (102 fonti in totale sul sito;
# qui solo le più comuni/richieste - altre si trovano nella stessa select se
# servisse ampliarle). Le chiavi sono forme in cui una persona nomina la
# fonte in italiano corrente; il matching in server.py è case-insensitive.
CODICE_MAP = {
    "costituzione": "cost",
    "cost": "cost",
    "codice civile": "cc",
    "c.c.": "cc",
    "cc": "cc",
    "preleggi": "pre",
    "codice di procedura civile": "cpc",
    "codice procedura civile": "cpc",
    "c.p.c.": "cpc",
    "cpc": "cpc",
    "codice penale": "cp",
    "c.p.": "cp",
    "cp": "cp",
    "codice di procedura penale": "cpp",
    "codice procedura penale": "cpp",
    "c.p.p.": "cpp",
    "cpp": "cpp",
    "codice della strada": "strada",
    "codice strada": "strada",
    "c.d.s.": "strada",
    "cds": "strada",
    "codice del processo tributario": "cproctri",
    "codice della privacy": "cprivacy",
    "codice del consumo": "ccons",
    "codice delle assicurazioni private": "casspriv",
    "codice dei beni culturali e del paesaggio": "cculpae",
    "codice dei contratti pubblici": "ccontpub",
    "codice del processo amministrativo": "cprocamm",
    "codice del turismo": "cturis",
    "codice dell'ambiente": "camb",
    "codice delle comunicazioni elettroniche": "ccomuelet",
    "codice delle pari opportunità": "cpariopp",
    "codice di giustizia contabile": "cgiuconta",
    "codice della nautica da diporto": "cnaudip",
    "codice della proprietà industriale": "cpropind",
    "codice dell'amministrazione digitale": "cammdigit",
    "codice antimafia": "cantimaf",
    "codice del terzo settore": "tsettore",
    "codice della protezione civile": "cprotciv",
    "codice della crisi d'impresa e dell'insolvenza": "ccrisiimpr",
    "codice della crisi d'impresa": "ccrisiimpr",
    "codice degli appalti": "capp",
    "nuovo codice appalti": "nca",
    "statuto dei lavoratori": "statlav",
    "statuto lavoratori": "statlav",
    "legge fallimentare": "lfall",
    "legge sul divorzio": "ldivo",
    "legge sull'adozione": "ladoz",
    "legge 104": "legge104",
    "t.u.p.i.": "tupubimp",
    "testo unico sul pubblico impiego": "tupubimp",
    "t.u.e.l.": "tuel",
    "testo unico bancario": "tunibanc",
    "t.u.b.": "tunibanc",
    "testo unico edilizia": "tued",
    "testo unico sull'immigrazione": "tuimm",
    "t.u.i.r.": "tuir",
    "testo unico delle imposte sui redditi": "tuir",
    "t.u.f.": "tuf",
    "testo unico della finanza": "tuf",
}

# --- Limiti di dimensione delle risposte --------------------------------------
# Alcuni articoli molto commentati (es. art. 2043 c.c.) hanno centinaia di
# massime sulla stessa pagina (una pagina sola può superare 500 massime e
# 600KB di testo): vanno troncate, altrimenti un'unica lettura di articolo
# travolgerebbe il contesto della conversazione.
MAX_MASSIME_ARTICOLO = 12
MAX_RISULTATI_PER_AREA = 8    # quando si cerca su tutte le aree insieme
MAX_RISULTATI_AREA_SINGOLA = 15  # quando si specifica una singola "area"
MAX_CARATTERI_SEZIONE = 6000  # tetto per ogni sezione testuale lunga (es. spiegazione)
