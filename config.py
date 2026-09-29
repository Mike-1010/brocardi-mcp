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

# Sigle raccolte dal menu a tendina del form (101 fonti reali sul sito, più la
# voce segnaposto "Scegli fonte:" che non è mai una fonte valida - verificate
# per intero via browser il 29/09/2026, elenco completo). Le chiavi sono forme
# in cui una persona nomina la fonte in italiano corrente; il matching in
# server.py è case-insensitive. Ogni fonte del sito ha almeno una voce qui;
# le più comuni hanno anche sigle/abbreviazioni frequenti come alias.
CODICE_MAP = {
    # --- Costituzione e codici principali ---------------------------------
    "costituzione": "cost",
    "cost": "cost",
    "codice civile": "cc",
    "c.c.": "cc",
    "cc": "cc",
    "preleggi": "pre",
    "disposizioni sulla legge in generale": "pre",
    "disposizioni di attuazione del codice civile": "dispattcc",
    "disp. att. c.c.": "dispattcc",
    "disp att cc": "dispattcc",
    "codice di procedura civile": "cpc",
    "codice procedura civile": "cpc",
    "c.p.c.": "cpc",
    "cpc": "cpc",
    "disposizioni di attuazione del codice di procedura civile": "dispattcpc",
    "disp. att. c.p.c.": "dispattcpc",
    "codice penale": "cp",
    "c.p.": "cp",
    "cp": "cp",
    "disposizioni di attuazione e coordinamento del codice penale": "dispattcp",
    "disp. att. c.p.": "dispattcp",
    "codice di procedura penale": "cpp",
    "codice procedura penale": "cpp",
    "c.p.p.": "cpp",
    "cpp": "cpp",
    "disposizioni di attuazione del codice di procedura penale": "dispattcpp",
    "disp. att. c.p.p.": "dispattcpp",
    "codice del processo penale minorile": "ppm",
    "processo penale minorile": "ppm",
    "codice della strada": "strada",
    "codice strada": "strada",
    "c.d.s.": "strada",
    "cds": "strada",

    # --- Altri codici settoriali -------------------------------------------
    "codice del processo tributario": "cproctri",
    "codice di giustizia tributaria": "cproctri",
    "codice della privacy": "cprivacy",
    "codice privacy": "cprivacy",
    "codice in materia di protezione dei dati personali": "cprivacy",
    "codice del consumo": "ccons",
    "codice delle assicurazioni private": "casspriv",
    "codice dei beni culturali e del paesaggio": "cculpae",
    "codice dei contratti pubblici": "ccontpub",
    "codice del processo amministrativo": "cprocamm",
    "codice del turismo": "cturis",
    "codice dell'ambiente": "camb",
    "codice ambientale": "camb",
    "codice delle comunicazioni elettroniche": "ccomuelet",
    "codice delle pari opportunità": "cpariopp",
    "codice di giustizia contabile": "cgiuconta",
    "codice della nautica da diporto": "cnaudip",
    "codice della proprietà industriale": "cpropind",
    "codice dell'amministrazione digitale": "cammdigit",
    "c.a.d.": "cammdigit",
    "codice antimafia": "cantimaf",
    "codice del terzo settore": "tsettore",
    "codice della protezione civile": "cprotciv",
    "codice della crisi d'impresa e dell'insolvenza": "ccrisiimpr",
    "codice della crisi d'impresa": "ccrisiimpr",
    "ccii": "ccrisiimpr",
    "codice degli appalti": "capp",
    "nuovo codice appalti": "nca",
    "nuovo codice dei contratti pubblici": "nca",
    "codice dei contratti pubblici 2023": "nca",

    # --- Leggi su famiglia, diritti della persona ---------------------------
    "legge sull'affidamento condiviso dei figli": "affido",
    "affidamento condiviso": "affido",
    "legge sull'aborto": "aborto",
    "legge 194": "aborto",
    "legge sul divorzio": "ldivo",
    "legge cirinnà": "cirinna",
    "unioni civili": "cirinna",
    "legge sull'adozione": "ladoz",
    "legge sulla procreazione medicalmente assistita": "promeda",
    "procreazione medicalmente assistita": "promeda",
    "legge 40": "promeda",
    "legge sul biotestamento": "biotest",
    "biotestamento": "biotest",
    "legge 104": "legge104",

    # --- Decreti recenti -----------------------------------------------------
    "decreto lavoro 2023": "dlav23",
    "decreto semplificazioni bis": "semplbis",
    "decreto sostegni": "desost",
    "decreto rilancio": "rilancio",
    "decreto cura italia": "curait",

    # --- Lavoro ---------------------------------------------------------------
    "statuto dei lavoratori": "statlav",
    "statuto lavoratori": "statlav",
    "disciplina organica dei contratti di lavoro": "mansionilav",
    "contratto di lavoro a tutele crescenti": "lavotutecre",
    "jobs act": "lavotutecre",
    "misure per la tutela del lavoro autonomo": "lavagile",
    "lavoro agile": "lavagile",
    "disposizioni in materia di ammortizzatori sociali": "ammsoc",
    "ammortizzatori sociali": "ammsoc",
    "legge sui licenziamenti individuali": "licind",
    "licenziamenti individuali": "licind",
    "organizzazione dell'orario di lavoro": "oralav",
    "orario di lavoro": "oralav",

    # --- Professioni, fallimento, proprietà, contratti speciali -------------
    "legge sulla professione forense": "lproffor",
    "ordinamento della professione forense": "lproffor",
    "legge fallimentare": "lfall",
    "legge sul diritto d'autore": "ldiraut",
    "diritto d'autore": "ldiraut",
    "disposizioni per lo sviluppo della proprietà coltivatrice": "dispcoltivatr",
    "norme sui contratti agrari": "contagr",
    "legge sulla responsabilità del personale sanitario": "respsan",
    "legge gelli-bianco": "respsan",
    "responsabilità sanitaria": "respsan",
    "legge sulle locazioni abitative": "llocab",
    "legge sull'equo canone": "lequoc",
    "legge sul procedimento amministrativo": "lprocamm",
    "legge 241": "lprocamm",
    "ricorsi amministrativi": "ricamm",
    "responsabilità amministrativa degli enti": "respammpergiu",
    "responsabilità delle persone giuridiche": "respammpergiu",
    "decreto 231": "respammpergiu",
    "d.lgs. 231": "respammpergiu",

    # --- Terzo settore, mediazione, ordinamenti speciali ---------------------
    "legge quadro sul volontariato": "lqvolont",
    "legge sulle onlus": "lonlus",
    "legge sulle aps": "laps",
    "associazioni di promozione sociale": "laps",
    "mediazione delle controversie civili e commerciali": "mediaz",
    "legge sull'ordinamento penitenziario": "lordpen",
    "diritto internazionale privato": "dirintpriv",
    "legge 218": "dirintpriv",
    "legge sui reati tributari": "lreatitri",

    # --- Testi unici -----------------------------------------------------------
    "testo unico sul sostegno della maternità e della paternità": "mater",
    "t.u.p.i.": "tupubimp",
    "testo unico sul pubblico impiego": "tupubimp",
    "t.u.e.l.": "tuel",
    "testo unico degli enti locali": "tuel",
    "testo unico bancario": "tunibanc",
    "t.u.b.": "tunibanc",
    "testo unico dell'edilizia": "tued",
    "testo unico edilizia": "tued",
    "testo unico sull'immigrazione": "tuimm",
    "testo unico stupefacenti": "tustup",
    "t.u.l.p.s.": "tulps",
    "testo unico delle leggi di pubblica sicurezza": "tulps",
    "testo unico sull'assicurazione infortuni sul lavoro": "tuail",
    "testo unico espropri": "tuepu",
    "testo unico sugli espropri": "tuepu",
    "t.u.f.": "tuf",
    "testo unico della finanza": "tuf",
    "t.u.s.l.": "tusl",
    "testo unico sicurezza sul lavoro": "tusl",
    "testo unico agricoltura": "tuagri",
    "testo unico piante officinali": "tupianteoff",
    "t.u.s.p.": "tusp",
    "testo unico società partecipate": "tusp",
    "testo unico successioni e donazioni": "tusd",
    "t.u.i.r.": "tuir",
    "testo unico delle imposte sui redditi": "tuir",
    "t.u.r.": "tur",
    "testo unico dell'imposta di registro": "tur",
    "testo unico iva": "tuiva",

    # --- Fiscale/tributario -----------------------------------------------------
    "disposizioni sull'accertamento delle imposte sui redditi": "dispaccimpred",
    "disposizioni sulla riscossione delle imposte sul reddito": "dispriscimpred",
    "disposizioni urgenti in materia fiscale": "dispurgfisc",
    "disposizioni su accertamento con adesione e conciliazione giudiziale": "dispaccadeconc",
    "disposizioni sanzioni amministrative per violazioni di norme tributarie": "dispsanzvioltri",
    "ordinamento degli organi speciali di giurisdizione tributaria": "ordorgtrib",
    "statuto del contribuente": "statcontri",
    "decreto imposte enti territoriali": "impoentiloc",

    # --- Varie ------------------------------------------------------------------
    "regolamento sulla posta elettronica certificata": "regpec",
    "pec": "regpec",
    "gdpr": "privacyue",
    "regolamento ue privacy": "privacyue",
    "regolamento generale sulla protezione dei dati": "privacyue",
    "contratto collettivo colf e badanti": "ccndl",
    "ccnl colf e badanti": "ccndl",
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
