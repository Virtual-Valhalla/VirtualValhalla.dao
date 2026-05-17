"""
config.py — Constantes globales y configuración de API keys

Contiene:
  - TTLs de caché (tiempo de vida de entradas en memoria)
  - COUNTRY_NAMES: mapa ISO-A2 → nombre legible (usado en logs y fallbacks)
  - NEWSAPI_COUNTRIES: conjunto de códigos con soporte nativo en top-headlines
  - build_api_keys(): construye la lista de objetos de API key desde el entorno
"""

import os
import logging

import random

# Lista blanca de fuentes confiables (Zero-Cost Quality)
TRUSTED_SOURCES = ["Reuters", "BBC News", "Associated Press", "The New York Times", "CNN", "The Guardian"]

# Palabras clave de alto impacto
IMPACT_KEYWORDS = ["breaking", "urgente", "alerta", "crisis", "importante", "histórico"]

# Configuración de L1 con Jitter [4, 5]
BASE_TTL = 21600  # 6 horas en segundos
def get_ttl_with_jitter():
    return BASE_TTL + random.randint(-300, 300) # +/- 5 minutos

logger = logging.getLogger(__name__)

# ── Tiempos de vida del caché en memoria ──────────────────────────────────────
# Las noticias por país se mantienen 6 horas; el feed global, 4 horas.
CACHE_TTL_COUNTRY = 6 * 3600   # 21 600 segundos
CACHE_TTL_GLOBAL  = 4 * 3600   # 14 400 segundos

# ── Mapa ISO-A2 → nombre de país en inglés ────────────────────────────────────
# Usado para construir queries de "everything" en NewsAPI cuando top-headlines
# no soporta el código ISO (deep-scan).
# Nota: algunos códigos aparecen duplicados al final; Python usa el último valor.
COUNTRY_NAMES = {
    "ae": "United Arab Emirates", "ar": "Argentina", "at": "Austria",
    "au": "Australia", "be": "Belgium", "bg": "Bulgaria", "br": "Brazil",
    "ca": "Canada", "ch": "Switzerland", "cn": "China", "co": "Colombia",
    "cu": "Cuba", "cz": "Czech Republic", "de": "Germany", "eg": "Egypt",
    "fr": "France", "gb": "United Kingdom", "gr": "Greece", "hk": "Hong Kong",
    "hu": "Hungary", "id": "Indonesia", "ie": "Ireland", "il": "Israel",
    "in": "India", "it": "Italy", "jp": "Japan", "kr": "South Korea",
    "lt": "Lithuania", "lv": "Latvia", "ma": "Morocco", "mx": "Mexico",
    "my": "Malaysia", "ng": "Nigeria", "nl": "Netherlands", "no": "Norway",
    "nz": "New Zealand", "ph": "Philippines", "pl": "Poland", "pt": "Portugal",
    "ro": "Romania", "rs": "Serbia", "ru": "Russia", "sa": "Saudi Arabia",
    "se": "Sweden", "sg": "Singapore", "si": "Slovenia", "sk": "Slovakia",
    "th": "Thailand", "tr": "Turkey", "tw": "Taiwan", "ua": "Ukraine",
    "us": "United States", "ve": "Venezuela", "za": "South Africa",
    "es": "Spain", "pe": "Peru", "cl": "Chile", "ec": "Ecuador",
    "bo": "Bolivia", "py": "Paraguay", "uy": "Uruguay", "pa": "Panama",
    "cr": "Costa Rica", "gt": "Guatemala", "hn": "Honduras", "sv": "El Salvador",
    "ni": "Nicaragua", "do": "Dominican Republic", "pr": "Puerto Rico",
    "ke": "Kenya", "gh": "Ghana", "et": "Ethiopia", "tz": "Tanzania",
    "ug": "Uganda", "dz": "Algeria", "tn": "Tunisia", "ly": "Libya",
    "sd": "Sudan", "cm": "Cameroon", "ci": "Ivory Coast", "sn": "Senegal",
    "zw": "Zimbabwe", "zm": "Zambia", "mz": "Mozambique", "mg": "Madagascar",
    "ao": "Angola", "cd": "Congo", "pk": "Pakistan", "bd": "Bangladesh",
    "lk": "Sri Lanka", "np": "Nepal", "mm": "Myanmar", "vn": "Vietnam",
    "kh": "Cambodia", "la": "Laos", "af": "Afghanistan", "ir": "Iran",
    "iq": "Iraq", "sy": "Syria", "jo": "Jordan", "lb": "Lebanon",
    "om": "Oman", "kw": "Kuwait", "qa": "Qatar", "bh": "Bahrain",
    "ye": "Yemen", "fi": "Finland", "dk": "Denmark", "ee": "Estonia",
    "by": "Belarus", "md": "Moldova", "ge": "Georgia", "am": "Armenia",
    "az": "Azerbaijan", "kz": "Kazakhstan", "uz": "Uzbekistan",
    "al": "Albania", "ba": "Bosnia", "hr": "Croatia", "mk": "North Macedonia",
    "me": "Montenegro", "mt": "Malta", "cy": "Cyprus", "is": "Iceland",
    "lu": "Luxembourg", "li": "Liechtenstein", "mc": "Monaco", "ad": "Andorra",
    "sm": "San Marino", "va": "Vatican", "nk": "North Korea", "so": "Somalia",
    "mr": "Mauritania", "ml": "Mali", "bf": "Burkina Faso", "ne": "Niger",
    "td": "Chad", "cf": "Central African Republic", "rw": "Rwanda",
    "bi": "Burundi", "er": "Eritrea", "dj": "Djibouti",
    "xk": "Kosovo", "ss": "South Sudan", "tl": "East Timor",
    "ps": "Palestine", "fj": "Fiji", "pg": "Papua New Guinea",
    "sb": "Solomon Islands", "vu": "Vanuatu", "ws": "Samoa", "to": "Tonga",
    "ki": "Kiribati", "fm": "Micronesia", "pw": "Palau", "mh": "Marshall Islands",
    "nr": "Nauru", "tv": "Tuvalu", "ck": "Cook Islands",
    "gn": "Guinea", "gw": "Guinea-Bissau", "gq": "Equatorial Guinea",
    "ga": "Gabon", "cg": "Republic of Congo", "sl": "Sierra Leone",
    "lr": "Liberia", "tg": "Togo", "bj": "Benin", "gm": "Gambia",
    "cv": "Cape Verde", "st": "Sao Tome and Principe", "km": "Comoros",
    "sc": "Seychelles", "mu": "Mauritius", "mw": "Malawi",
    "sz": "Eswatini", "ls": "Lesotho", "na": "Namibia", "bw": "Botswana",
    "tj": "Tajikistan", "tm": "Turkmenistan", "kg": "Kyrgyzstan",
    "mn": "Mongolia", "bt": "Bhutan", "mv": "Maldives",
    "gy": "Guyana", "sr": "Suriname",
    "tt": "Trinidad and Tobago", "jm": "Jamaica",
    "ht": "Haiti", "bs": "Bahamas", "bb": "Barbados",
    "lc": "Saint Lucia", "vc": "Saint Vincent", "ag": "Antigua",
    "dm": "Dominica", "gd": "Grenada", "kn": "Saint Kitts",
    "bz": "Belize",
}

# ── Países con soporte nativo en el endpoint top-headlines de NewsAPI ─────────
# Para estos códigos se usa ?country=XX directamente.
# Para cualquier otro código se cae al endpoint "everything" con búsqueda por nombre.
NEWSAPI_COUNTRIES = {
    "ae","ar","at","au","be","bg","br","ca","ch","cn","co","cu","cz",
    "de","eg","fr","gb","gr","hk","hu","id","ie","il","in","it","jp",
    "kr","lt","lv","ma","mx","my","ng","nl","no","nz","ph","pl","pt",
    "ro","rs","ru","sa","se","sg","si","sk","th","tr","tw","ua","us","ve","za"
}


def build_api_keys():
    """
    Lee la variable de entorno NEWS_API_KEY y construye la lista de objetos de clave.

    Soporta múltiples claves separadas por coma para rotación automática
    cuando una clave supera su límite de peticiones (rate limit).

    Cada objeto tiene:
      - key:           la cadena de la API key
      - requests_used: contador de peticiones realizadas con esta clave
      - rate_limited:  si True, se salta esta clave en la rotación

    Si no hay clave configurada, inserta un placeholder y emite una advertencia.
    El sistema seguirá funcionando con noticias de la BD local.
    """
    keys = []
    raw = os.environ.get("NEWS_API_KEY", "")
    for k in raw.split(","):
        k = k.strip()
        if k:
            keys.append({'key': k, 'requests_used': 0, 'rate_limited': False})
    if not keys:
        logger.warning("⚠️ No NEWS_API_KEY encontrada.")
        keys.append({'key': 'PLACEHOLDER', 'requests_used': 0, 'rate_limited': False})
    return keys
