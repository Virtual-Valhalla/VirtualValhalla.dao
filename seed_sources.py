"""
seed_sources.py — Poblar news_globo.db con fuentes de noticias de todo el mundo.
Ejecutar: python seed_sources.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from models.database import init_db, get_db

SOURCES = [
    # ──────────────────────────────────────────────────────────────────────────
    # 🌍 INTERNACIONAL / ENGLISH
    # ──────────────────────────────────────────────────────────────────────────
    ("BBC News – Top Stories",              "http://feeds.bbci.co.uk/news/rss.xml",                                          "rss",      "en", "General"),
    ("BBC News – World",                    "http://feeds.bbci.co.uk/news/world/rss.xml",                                    "rss",      "en", "General"),
    ("BBC News – Technology",               "http://feeds.bbci.co.uk/news/technology/rss.xml",                               "rss",      "en", "Tecnología"),
    ("BBC News – Science & Environment",    "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",                  "rss",      "en", "Ciencia"),
    ("BBC News – Health",                   "http://feeds.bbci.co.uk/news/health/rss.xml",                                   "rss",      "en", "Salud"),
    ("BBC News – Business",                 "http://feeds.bbci.co.uk/news/business/rss.xml",                                 "rss",      "en", "Economía"),
    ("BBC News – Sport",                    "http://feeds.bbci.co.uk/sport/0/rss.xml",                                       "rss",      "en", "Deportes"),
    ("Reuters – Top News",                  "https://feeds.reuters.com/reuters/topNews",                                     "rss",      "en", "General"),
    ("Reuters – Business",                  "https://feeds.reuters.com/reuters/businessNews",                                "rss",      "en", "Economía"),
    ("Reuters – Technology",                "https://feeds.reuters.com/reuters/technologyNews",                              "rss",      "en", "Tecnología"),
    ("Reuters – Science",                   "https://feeds.reuters.com/reuters/scienceNews",                                 "rss",      "en", "Ciencia"),
    ("Reuters – Sports",                    "https://feeds.reuters.com/reuters/sportsNews",                                  "rss",      "en", "Deportes"),
    ("Reuters – World",                     "https://feeds.reuters.com/Reuters/worldNews",                                   "rss",      "en", "General"),
    ("Al Jazeera – All",                    "https://www.aljazeera.com/xml/rss/all.xml",                                     "rss",      "en", "General"),
    ("CNN – Top Stories",                   "http://rss.cnn.com/rss/edition.rss",                                            "rss",      "en", "General"),
    ("CNN – World",                         "http://rss.cnn.com/rss/edition_world.rss",                                     "rss",      "en", "General"),
    ("CNN – Technology",                    "http://rss.cnn.com/rss/edition_technology.rss",                                "rss",      "en", "Tecnología"),
    ("CNN – Business",                      "http://rss.cnn.com/rss/money_news_international.rss",                          "rss",      "en", "Economía"),
    ("CNN – Sport",                         "http://rss.cnn.com/rss/edition_sport.rss",                                     "rss",      "en", "Deportes"),
    ("The Guardian – World",                "https://www.theguardian.com/world/rss",                                        "rss",      "en", "General"),
    ("The Guardian – Technology",           "https://www.theguardian.com/technology/rss",                                   "rss",      "en", "Tecnología"),
    ("The Guardian – Science",              "https://www.theguardian.com/science/rss",                                      "rss",      "en", "Ciencia"),
    ("The Guardian – Business",             "https://www.theguardian.com/business/rss",                                     "rss",      "en", "Economía"),
    ("The Guardian – Sport",                "https://www.theguardian.com/sport/rss",                                        "rss",      "en", "Deportes"),
    ("The Guardian – Environment",          "https://www.theguardian.com/environment/rss",                                  "rss",      "en", "Ciencia"),
    ("The New York Times – World",          "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",                       "rss",      "en", "General"),
    ("The New York Times – Technology",     "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",                  "rss",      "en", "Tecnología"),
    ("The New York Times – Science",        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",                     "rss",      "en", "Ciencia"),
    ("The New York Times – Business",       "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",                    "rss",      "en", "Economía"),
    ("The New York Times – Sports",         "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",                      "rss",      "en", "Deportes"),
    ("The Washington Post – World",         "https://feeds.washingtonpost.com/rss/world",                                   "rss",      "en", "General"),
    ("The Washington Post – Technology",    "https://feeds.washingtonpost.com/rss/business/technology",                     "rss",      "en", "Tecnología"),
    ("Associated Press – Top Headlines",    "https://feeds.apnews.com/rss/apf-topnews",                                     "rss",      "en", "General"),
    ("Associated Press – World",            "https://feeds.apnews.com/rss/apf-intlnews",                                    "rss",      "en", "General"),
    ("Associated Press – Technology",       "https://feeds.apnews.com/rss/apf-Technology",                                  "rss",      "en", "Tecnología"),
    ("Associated Press – Business",         "https://feeds.apnews.com/rss/apf-business",                                    "rss",      "en", "Economía"),
    ("Associated Press – Sports",           "https://feeds.apnews.com/rss/apf-sports",                                      "rss",      "en", "Deportes"),
    ("NPR – News",                          "https://feeds.npr.org/1001/rss.xml",                                           "rss",      "en", "General"),
    ("NPR – World",                         "https://feeds.npr.org/1004/rss.xml",                                           "rss",      "en", "General"),
    ("NPR – Science",                       "https://feeds.npr.org/1007/rss.xml",                                           "rss",      "en", "Ciencia"),
    ("NPR – Technology",                    "https://feeds.npr.org/1019/rss.xml",                                           "rss",      "en", "Tecnología"),
    ("NPR – Business",                      "https://feeds.npr.org/1006/rss.xml",                                           "rss",      "en", "Economía"),
    ("NPR – Politics",                      "https://feeds.npr.org/1014/rss.xml",                                           "rss",      "en", "Política"),
    ("Deutsche Welle – World (EN)",         "https://rss.dw.com/rdf/rss-en-world",                                          "rss",      "en", "General"),
    ("Deutsche Welle – Technology (EN)",    "https://rss.dw.com/rdf/rss-en-science-tech",                                   "rss",      "en", "Tecnología"),
    ("France 24 – World (EN)",              "https://www.france24.com/en/rss",                                              "rss",      "en", "General"),
    ("Euronews – World (EN)",               "https://feeds.feedburner.com/euronews/en/home",                                "rss",      "en", "General"),
    ("The Economist",                       "https://www.economist.com/latest/rss.xml",                                     "rss",      "en", "Economía"),
    ("Financial Times",                     "https://www.ft.com/rss/home/uk",                                               "rss",      "en", "Economía"),
    ("Bloomberg – Markets",                 "https://feeds.bloomberg.com/markets/news.rss",                                 "rss",      "en", "Economía"),
    ("Forbes – Business",                   "https://www.forbes.com/business/feed/",                                       "rss",      "en", "Economía"),
    ("Forbes – Technology",                 "https://www.forbes.com/technology/feed/",                                      "rss",      "en", "Tecnología"),
    ("Time – World",                        "https://time.com/feed/",                                                       "rss",      "en", "General"),
    ("The Atlantic",                        "https://www.theatlantic.com/feed/all/",                                        "rss",      "en", "General"),
    ("Politico – World",                    "https://rss.politico.com/politics-news.xml",                                   "rss",      "en", "Política"),
    ("Foreign Affairs",                     "https://www.foreignaffairs.com/rss.xml",                                       "rss",      "en", "Política"),
    ("Foreign Policy",                      "https://foreignpolicy.com/feed/",                                              "rss",      "en", "Política"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🖥️ TECNOLOGÍA
    # ──────────────────────────────────────────────────────────────────────────
    ("TechCrunch",                          "https://techcrunch.com/feed/",                                                 "rss",      "en", "Tecnología"),
    ("The Verge",                           "https://www.theverge.com/rss/index.xml",                                      "rss",      "en", "Tecnología"),
    ("Wired",                               "https://www.wired.com/feed/rss",                                               "rss",      "en", "Tecnología"),
    ("Ars Technica",                        "http://feeds.arstechnica.com/arstechnica/index",                               "rss",      "en", "Tecnología"),
    ("Engadget",                            "https://www.engadget.com/rss.xml",                                             "rss",      "en", "Tecnología"),
    ("Hacker News (Top)",                   "https://hnrss.org/frontpage",                                                  "rss",      "en", "Tecnología"),
    ("MIT Technology Review",               "https://www.technologyreview.com/feed/",                                       "rss",      "en", "Tecnología"),
    ("VentureBeat",                         "https://venturebeat.com/feed/",                                                "rss",      "en", "Tecnología"),
    ("CNET",                                "https://www.cnet.com/rss/news/",                                               "rss",      "en", "Tecnología"),
    ("ZDNet",                               "https://www.zdnet.com/news/rss.xml",                                           "rss",      "en", "Tecnología"),
    ("Mashable",                            "https://mashable.com/feeds/rss/all",                                           "rss",      "en", "Tecnología"),
    ("Gizmodo",                             "https://gizmodo.com/rss",                                                      "rss",      "en", "Tecnología"),
    ("9to5Mac",                             "https://9to5mac.com/feed/",                                                    "rss",      "en", "Tecnología"),
    ("9to5Google",                          "https://9to5google.com/feed/",                                                 "rss",      "en", "Tecnología"),
    ("Android Authority",                   "https://www.androidauthority.com/feed/",                                       "rss",      "en", "Tecnología"),
    ("Tom's Hardware",                      "https://www.tomshardware.com/feeds/all",                                       "rss",      "en", "Tecnología"),
    ("PCMag",                               "https://www.pcmag.com/rss",                                                    "rss",      "en", "Tecnología"),
    ("InfoQ",                               "https://feed.infoq.com/",                                                     "rss",      "en", "Tecnología"),
    ("Dev.to",                              "https://dev.to/feed",                                                          "rss",      "en", "Tecnología"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🔬 CIENCIA / SALUD
    # ──────────────────────────────────────────────────────────────────────────
    ("Science Daily",                       "https://www.sciencedaily.com/rss/all.xml",                                     "rss",      "en", "Ciencia"),
    ("Nature – News",                       "https://www.nature.com/nature.rss",                                            "rss",      "en", "Ciencia"),
    ("New Scientist",                       "https://www.newscientist.com/feed/home/",                                      "rss",      "en", "Ciencia"),
    ("NASA – Breaking News",                "https://www.nasa.gov/feeds/iotd-feed/",                                       "rss",      "en", "Ciencia"),
    ("Space.com",                           "https://www.space.com/feeds/all",                                              "rss",      "en", "Ciencia"),
    ("Phys.org",                            "https://phys.org/rss-feed/",                                                   "rss",      "en", "Ciencia"),
    ("Live Science",                        "https://www.livescience.com/feeds/all",                                        "rss",      "en", "Ciencia"),
    ("Medical News Today",                  "https://www.medicalnewstoday.com/rss",                                         "rss",      "en", "Salud"),
    ("WHO – News",                          "https://www.who.int/rss-feeds/news-english.xml",                               "rss",      "en", "Salud"),
    ("WebMD – Health News",                 "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC",                 "rss",      "en", "Salud"),
    ("Scientific American",                 "https://rss.sciam.com/ScientificAmerican-Global",                             "rss",      "en", "Ciencia"),
    ("Popular Science",                     "https://www.popsci.com/arcio/rss/",                                            "rss",      "en", "Ciencia"),

    # ──────────────────────────────────────────────────────────────────────────
    # 💹 ECONOMÍA / FINANZAS
    # ──────────────────────────────────────────────────────────────────────────
    ("MarketWatch – Top",                   "http://feeds.marketwatch.com/marketwatch/topstories/",                         "rss",      "en", "Economía"),
    ("Investing.com – News",                "https://www.investing.com/rss/news.rss",                                       "rss",      "en", "Economía"),
    ("CNBC – Top News",                     "https://www.cnbc.com/id/100003114/device/rss/rss.html",                       "rss",      "en", "Economía"),
    ("CNBC – Technology",                   "https://www.cnbc.com/id/19854910/device/rss/rss.html",                        "rss",      "en", "Tecnología"),
    ("Business Insider",                    "https://feeds.businessinsider.com/custom/all",                                 "rss",      "en", "Economía"),
    ("Yahoo Finance",                       "https://finance.yahoo.com/news/rssindex",                                      "rss",      "en", "Economía"),
    ("CoinDesk – Crypto",                   "https://www.coindesk.com/arc/outboundfeeds/rss/",                              "rss",      "en", "Economía"),
    ("CoinTelegraph",                       "https://cointelegraph.com/rss",                                                "rss",      "en", "Economía"),

    # ──────────────────────────────────────────────────────────────────────────
    # ⚽ DEPORTES
    # ──────────────────────────────────────────────────────────────────────────
    ("ESPN – Top Headlines",                "https://www.espn.com/espn/rss/news",                                           "rss",      "en", "Deportes"),
    ("ESPN – Soccer",                       "https://www.espn.com/espn/rss/soccer/news",                                    "rss",      "en", "Deportes"),
    ("ESPN – NBA",                          "https://www.espn.com/espn/rss/nba/news",                                       "rss",      "en", "Deportes"),
    ("ESPN – NFL",                          "https://www.espn.com/espn/rss/nfl/news",                                       "rss",      "en", "Deportes"),
    ("Sky Sports – News",                   "https://www.skysports.com/rss/12040",                                          "rss",      "en", "Deportes"),
    ("Sky Sports – Football",               "https://www.skysports.com/rss/12040",                                          "rss",      "en", "Deportes"),
    ("Goal.com",                            "https://www.goal.com/feeds/en/news",                                           "rss",      "en", "Deportes"),
    ("The Athletic – NFL",                  "https://theathletic.com/rss/feed/all/",                                        "rss",      "en", "Deportes"),
    ("Formula 1 – News",                    "https://www.formula1.com/content/fom-website/en/latest/all.xml",              "rss",      "en", "Deportes"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇪🇸 ESPAÑA / ESPAÑOL
    # ──────────────────────────────────────────────────────────────────────────
    ("El País – Portada",                   "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",             "rss",      "es", "General"),
    ("El País – Internacional",             "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada", "rss", "es", "General"),
    ("El País – Tecnología",                "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada",   "rss", "es", "Tecnología"),
    ("El País – Ciencia",                   "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/ciencia/portada",      "rss", "es", "Ciencia"),
    ("El País – Deportes",                  "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/deportes/portada",     "rss", "es", "Deportes"),
    ("El Mundo – Portada",                  "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",                         "rss",      "es", "General"),
    ("El Mundo – Internacional",            "https://e00-elmundo.uecdn.es/elmundo/rss/internacional.xml",                   "rss",      "es", "General"),
    ("El Mundo – Economía",                 "https://e00-elmundo.uecdn.es/elmundo/rss/economia.xml",                        "rss",      "es", "Economía"),
    ("El Mundo – Deportes",                 "https://e00-elmundo.uecdn.es/elmundo/rss/deportes.xml",                        "rss",      "es", "Deportes"),
    ("ABC – Portada",                       "https://www.abc.es/rss/feeds/abc_EspanaEspana.xml",                            "rss",      "es", "General"),
    ("ABC – Internacional",                 "https://www.abc.es/rss/feeds/abc_Internacional.xml",                           "rss",      "es", "General"),
    ("ABC – Deportes",                      "https://www.abc.es/rss/feeds/abc_Deportes.xml",                                "rss",      "es", "Deportes"),
    ("La Vanguardia",                       "https://www.lavanguardia.com/rss/home.xml",                                    "rss",      "es", "General"),
    ("El Confidencial",                     "https://www.elconfidencial.com/rss/",                                          "rss",      "es", "General"),
    ("El Diario.es",                        "https://www.eldiario.es/rss/",                                                 "rss",      "es", "General"),
    ("20 Minutos",                          "https://www.20minutos.es/rss/",                                                "rss",      "es", "General"),
    ("Marca",                               "https://www.marca.com/rss/portada.xml",                                        "rss",      "es", "Deportes"),
    ("AS – Fútbol",                         "https://as.com/rss/tags/ultimas_noticias.xml",                                 "rss",      "es", "Deportes"),
    ("Sport.es",                            "https://www.sport.es/es/rss/",                                                 "rss",      "es", "Deportes"),
    ("Xataka",                              "https://www.xataka.com/index.xml",                                             "rss",      "es", "Tecnología"),
    ("Genbeta",                             "https://www.genbeta.com/index.xml",                                            "rss",      "es", "Tecnología"),
    ("Hipertextual",                        "https://hipertextual.com/feed",                                                "rss",      "es", "Tecnología"),
    ("El Español",                          "https://www.elespanol.com/rss/",                                               "rss",      "es", "General"),
    ("La Razón",                            "https://www.larazon.es/rss/",                                                  "rss",      "es", "General"),
    ("Expansión",                           "https://e00-expansion.uecdn.es/rss/portada.xml",                               "rss",      "es", "Economía"),
    ("Cinco Días",                          "https://feeds.elpais.com/mrss-s/pages/ep/site/cincodias.elpais.com/portada",   "rss",      "es", "Economía"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇲🇽🇦🇷🇨🇴 LATINOAMÉRICA
    # ──────────────────────────────────────────────────────────────────────────
    ("Infobae",                             "https://www.infobae.com/feeds/rss/america/",                                   "rss",      "es", "General"),
    ("Infobae – Tecnología",                "https://www.infobae.com/feeds/rss/america/tecno/",                             "rss",      "es", "Tecnología"),
    ("Infobae – Deportes",                  "https://www.infobae.com/feeds/rss/america/deportes/",                          "rss",      "es", "Deportes"),
    ("Clarín – Noticias",                   "https://www.clarin.com/rss/lo-ultimo/",                                        "rss",      "es", "General"),
    ("Clarín – Deportes",                   "https://www.clarin.com/rss/deportes/",                                         "rss",      "es", "Deportes"),
    ("Clarín – Tecnología",                 "https://www.clarin.com/rss/tecnologia/",                                       "rss",      "es", "Tecnología"),
    ("La Nación (Argentina)",               "https://www.lanacion.com.ar/feed",                                             "rss",      "es", "General"),
    ("El Universal (México)",               "https://www.eluniversal.com.mx/rss.xml",                                       "rss",      "es", "General"),
    ("Milenio – México",                    "https://www.milenio.com/rss",                                                  "rss",      "es", "General"),
    ("El Economista (México)",              "https://www.eleconomista.com.mx/rss.xml",                                      "rss",      "es", "Economía"),
    ("BBC Mundo",                           "https://feeds.bbci.co.uk/mundo/rss.xml",                                       "rss",      "es", "General"),
    ("CNN en Español",                      "https://cnnespanol.cnn.com/feed/",                                             "rss",      "es", "General"),
    ("Deutsche Welle – Español",            "https://rss.dw.com/rdf/rss-es-all",                                            "rss",      "es", "General"),
    ("France 24 – Español",                 "https://www.france24.com/es/rss",                                              "rss",      "es", "General"),
    ("Univision – Noticias",                "https://www.univision.com/rss/noticias",                                       "rss",      "es", "General"),
    ("El Heraldo (Colombia)",               "https://www.elheraldo.co/rss",                                                 "rss",      "es", "General"),
    ("El Tiempo (Colombia)",                "https://www.eltiempo.com/rss/colombia.xml",                                    "rss",      "es", "General"),
    ("El Comercio (Perú)",                  "https://elcomercio.pe/rss/todas.xml",                                          "rss",      "es", "General"),
    ("La República (Perú)",                 "https://larepublica.pe/rss/todas.xml",                                         "rss",      "es", "General"),
    ("El Mercurio (Chile)",                 "https://www.emol.com/rss/index.rss",                                           "rss",      "es", "General"),
    ("La Tercera (Chile)",                  "https://www.latercera.com/feed/",                                              "rss",      "es", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇫🇷 FRANCE
    # ──────────────────────────────────────────────────────────────────────────
    ("Le Monde – À la une",                 "https://www.lemonde.fr/rss/une.xml",                                           "rss",      "fr", "General"),
    ("Le Monde – International",            "https://www.lemonde.fr/international/rss_full.xml",                           "rss",      "fr", "General"),
    ("Le Monde – Économie",                 "https://www.lemonde.fr/economie/rss_full.xml",                                 "rss",      "fr", "Economía"),
    ("Le Figaro",                           "https://www.lefigaro.fr/rss/figaro_actualites.xml",                            "rss",      "fr", "General"),
    ("Le Point",                            "https://www.lepoint.fr/rss.xml",                                               "rss",      "fr", "General"),
    ("Libération",                          "https://www.liberation.fr/arc/outboundfeeds/rss-all/?outputType=xml",          "rss",      "fr", "General"),
    ("France Info",                         "https://www.francetvinfo.fr/titres.rss",                                       "rss",      "fr", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇩🇪 ALEMANIA
    # ──────────────────────────────────────────────────────────────────────────
    ("Deutsche Welle – Deutsch",            "https://rss.dw.com/rdf/rss-de-all",                                            "rss",      "de", "General"),
    ("Der Spiegel",                         "https://www.spiegel.de/index.rss",                                             "rss",      "de", "General"),
    ("Die Zeit",                            "https://newsfeed.zeit.de/all",                                                 "rss",      "de", "General"),
    ("FAZ",                                 "https://www.faz.net/rss/aktuell/",                                             "rss",      "de", "General"),
    ("Süddeutsche Zeitung",                 "https://rss.sueddeutsche.de/rss/TopThemen",                                    "rss",      "de", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇮🇹 ITALIA
    # ──────────────────────────────────────────────────────────────────────────
    ("La Repubblica",                       "https://www.repubblica.it/rss/homepage/rss2.0.xml",                            "rss",      "it", "General"),
    ("Corriere della Sera",                 "https://xml2.corrieredellasera.it/rss/homepage.xml",                           "rss",      "it", "General"),
    ("Ansa – Ultime Notizie",               "https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",                         "rss",      "it", "General"),
    ("Gazzetta dello Sport",                "https://www.gazzetta.it/rss/home.xml",                                         "rss",      "it", "Deportes"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇵🇹 PORTUGAL
    # ──────────────────────────────────────────────────────────────────────────
    ("Público",                             "https://www.publico.pt/api/content/rss",                                       "rss",      "pt", "General"),
    ("Correio da Manhã",                    "https://www.cmjornal.pt/rss",                                                  "rss",      "pt", "General"),
    ("Jornal de Notícias",                  "https://www.jn.pt/rss/",                                                       "rss",      "pt", "General"),
    ("Observador",                          "https://observador.pt/feed/",                                                  "rss",      "pt", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇧🇷 BRASIL
    # ──────────────────────────────────────────────────────────────────────────
    ("Folha de S.Paulo",                    "https://feeds.folha.uol.com.br/folha/emcimadahora/rss091.xml",                 "rss",      "pt", "General"),
    ("O Globo",                             "https://oglobo.globo.com/rss.xml",                                             "rss",      "pt", "General"),
    ("G1 – Últimas Notícias",               "https://g1.globo.com/rss/g1/",                                                 "rss",      "pt", "General"),
    ("BBC Brasil",                          "https://feeds.bbci.co.uk/portuguese/rss.xml",                                  "rss",      "pt", "General"),
    ("UOL Notícias",                        "https://rss.uol.com.br/feed/noticias.xml",                                     "rss",      "pt", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇯🇵 JAPÓN
    # ──────────────────────────────────────────────────────────────────────────
    ("Japan Times",                         "https://www.japantimes.co.jp/feed",                                            "rss",      "en", "General"),
    ("NHK World – News",                    "https://www3.nhk.or.jp/rss/news/cat0.xml",                                     "rss",      "ja", "General"),
    ("Asahi Shimbun (EN)",                  "https://www.asahi.com/ajw/rss.rdf",                                            "rss",      "en", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇨🇳 CHINA
    # ──────────────────────────────────────────────────────────────────────────
    ("Xinhua – English",                    "http://www.xinhuanet.com/english/rss/worldrss.xml",                            "rss",      "en", "General"),
    ("South China Morning Post",            "https://www.scmp.com/rss/91/feed",                                             "rss",      "en", "General"),
    ("China Daily",                         "http://www.chinadaily.com.cn/rss/china_rss.xml",                               "rss",      "en", "General"),
    ("Global Times",                        "https://www.globaltimes.cn/rss/outbrain.xml",                                  "rss",      "en", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇮🇳 INDIA
    # ──────────────────────────────────────────────────────────────────────────
    ("The Hindu",                           "https://www.thehindu.com/feeder/default.rss",                                  "rss",      "en", "General"),
    ("The Times of India",                  "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",                   "rss",      "en", "General"),
    ("NDTV – India",                        "https://feeds.feedburner.com/ndtvnews-india-news",                             "rss",      "en", "General"),
    ("Hindustan Times",                     "https://www.hindustantimes.com/feeds/rss/latest-news/rssfeed.xml",             "rss",      "en", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇷🇺 RUSIA
    # ──────────────────────────────────────────────────────────────────────────
    ("RT – English",                        "https://www.rt.com/rss/",                                                      "rss",      "en", "General"),
    ("TASS – English",                      "https://tass.com/rss/v2.xml",                                                  "rss",      "en", "General"),
    ("Moscow Times",                        "https://www.themoscowtimes.com/rss/news",                                      "rss",      "en", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇸🇦 ORIENTE MEDIO / AFRICA
    # ──────────────────────────────────────────────────────────────────────────
    ("Al Jazeera Arabic",                   "https://www.aljazeera.net/xml/rss/all.xml",                                    "rss",      "ar", "General"),
    ("Al Arabiya (EN)",                     "https://english.alarabiya.net/tools/rss",                                      "rss",      "en", "General"),
    ("The Jerusalem Post",                  "https://www.jpost.com/rss/rssfeedsheadlines.aspx",                             "rss",      "en", "General"),
    ("Haaretz (EN)",                        "https://www.haaretz.com/cmlink/1.263335",                                      "rss",      "en", "General"),
    ("Ahram Online (Egypt EN)",             "http://english.ahram.org.eg/rss",                                              "rss",      "en", "General"),
    ("Daily Nation (Kenya)",                "https://nation.africa/kenya/rss.xml",                                           "rss",      "en", "General"),
    ("IOL – South Africa",                  "https://www.iol.co.za/cmlink/1.488",                                           "rss",      "en", "General"),
    ("DW – Africa (EN)",                    "https://rss.dw.com/rdf/rss-en-afr",                                            "rss",      "en", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇰🇷 COREA / 🇦🇺 AUSTRALIA / 🇨🇦 CANADÁ / 🇸🇬 SINGAPUR
    # ──────────────────────────────────────────────────────────────────────────
    ("The Sydney Morning Herald",           "https://www.smh.com.au/rss/feed.xml",                                          "rss",      "en", "General"),
    ("The Globe and Mail",                  "https://www.theglobeandmail.com/arc/outboundfeeds/rss/",                       "rss",      "en", "General"),
    ("CBC – Top Stories",                   "https://www.cbc.ca/cmlink/rss-topstories",                                     "rss",      "en", "General"),
    ("The Straits Times",                   "https://www.straitstimes.com/news/rss",                                        "rss",      "en", "General"),
    ("Korea Herald",                        "http://www.koreaherald.com/rss/",                                              "rss",      "en", "General"),
    ("Yonhap News",                         "https://en.yna.co.kr/RSS/news.xml",                                            "rss",      "en", "General"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🌱 MEDIO AMBIENTE / CLIMA
    # ──────────────────────────────────────────────────────────────────────────
    ("The Guardian – Environment",          "https://www.theguardian.com/environment/rss",                                  "rss",      "en", "Medio Ambiente"),
    ("Climate Home News",                   "https://www.climatechangenews.com/feed/",                                      "rss",      "en", "Medio Ambiente"),
    ("Carbon Brief",                        "https://www.carbonbrief.org/feed",                                             "rss",      "en", "Medio Ambiente"),
    ("Yale Environment 360",                "https://e360.yale.edu/feed",                                                   "rss",      "en", "Medio Ambiente"),
    ("Inside Climate News",                 "https://insideclimatenews.org/feed/",                                          "rss",      "en", "Medio Ambiente"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🎮 GAMING / ENTRETENIMIENTO
    # ──────────────────────────────────────────────────────────────────────────
    ("IGN",                                 "https://feeds.ign.com/ign/all",                                                "rss",      "en", "Entretenimiento"),
    ("Kotaku",                              "https://kotaku.com/rss",                                                       "rss",      "en", "Entretenimiento"),
    ("GameSpot",                            "https://www.gamespot.com/feeds/mashup/",                                       "rss",      "en", "Entretenimiento"),
    ("Variety",                             "https://variety.com/feed/",                                                    "rss",      "en", "Entretenimiento"),
    ("The Hollywood Reporter",              "https://www.hollywoodreporter.com/feed/",                                      "rss",      "en", "Entretenimiento"),
    ("Rolling Stone",                       "https://www.rollingstone.com/feed/",                                           "rss",      "en", "Entretenimiento"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🔒 CIBERSEGURIDAD
    # ──────────────────────────────────────────────────────────────────────────
    ("Krebs on Security",                   "https://krebsonsecurity.com/feed/",                                            "rss",      "en", "Ciberseguridad"),
    ("Threatpost",                          "https://threatpost.com/feed/",                                                 "rss",      "en", "Ciberseguridad"),
    ("Dark Reading",                        "https://www.darkreading.com/rss.xml",                                          "rss",      "en", "Ciberseguridad"),
    ("Bleeping Computer",                   "https://www.bleepingcomputer.com/feed/",                                       "rss",      "en", "Ciberseguridad"),
    ("The Hacker News",                     "https://feeds.feedburner.com/TheHackersNews",                                  "rss",      "en", "Ciberseguridad"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🤖 IA / INTELIGENCIA ARTIFICIAL
    # ──────────────────────────────────────────────────────────────────────────
    ("Towards Data Science",                "https://towardsdatascience.com/feed",                                          "rss",      "en", "Tecnología"),
    ("AI News",                             "https://artificialintelligence-news.com/feed/",                                "rss",      "en", "Tecnología"),
    ("OpenAI Blog",                         "https://openai.com/news/rss/",                                                 "rss",      "en", "Tecnología"),
    ("MIT AI News",                         "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml",               "rss",      "en", "Tecnología"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🗳️ POLÍTICA INTERNACIONAL
    # ──────────────────────────────────────────────────────────────────────────
    ("Axios – Politics",                    "https://api.axios.com/feed/",                                                  "rss",      "en", "Política"),
    ("The Hill – Politics",                 "https://thehill.com/feed/",                                                    "rss",      "en", "Política"),
    ("RealClearPolitics",                   "https://feeds.feedburner.com/realclearpolitics/qlMj",                          "rss",      "en", "Política"),
    ("UN News",                             "https://news.un.org/feed/subscribe/en/news/all/rss.xml",                       "rss",      "en", "Política"),
    ("Council on Foreign Relations",        "https://www.cfr.org/index.xml",                                                "rss",      "en", "Política"),

    # ──────────────────────────────────────────────────────────────────────────
    # 🇷🇺🇺🇦 CONFLICTOS / DEFENSA
    # ──────────────────────────────────────────────────────────────────────────
    ("Defense News",                        "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml",            "rss",      "en", "Política"),
    ("The War Zone",                        "https://www.thedrive.com/the-war-zone/rss",                                    "rss",      "en", "Política"),
    ("Kyiv Independent",                    "https://kyivindependent.com/feed/",                                            "rss",      "en", "General"),
    ("Ukrinform (EN)",                      "https://www.ukrinform.net/rss/block-lastnews",                                 "rss",      "en", "General"),
]

def seed():
    init_db()
    inserted = 0
    skipped  = 0
    updated  = 0
    with get_db() as conn:
        # Get existing URLs to avoid re-inserting defaults
        existing = {r[0] for r in conn.execute("SELECT url FROM sources").fetchall()}
        for row in SOURCES:
            nombre   = row[0]
            url      = row[1]
            tipo     = row[2]
            lang     = row[3] if len(row) > 3 else 'en'
            categoria = row[4] if len(row) > 4 else 'General'

            if url in existing:
                # Update categoria and lang for existing sources (in case they were empty)
                try:
                    conn.execute(
                        "UPDATE sources SET categoria = ?, lang = ? WHERE url = ? AND (categoria IS NULL OR categoria = '' OR categoria = 'General')",
                        (categoria, lang, url)
                    )
                    if conn.execute("SELECT changes()").fetchone()[0] > 0:
                        updated += 1
                except Exception:
                    pass
                skipped += 1
                continue
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO sources (nombre, url, tipo, activa, lang, categoria) VALUES (?,?,?,1,?,?)",
                    (nombre, url, tipo, lang, categoria)
                )
                inserted += 1
                existing.add(url)
            except Exception as e:
                print(f"  ⚠️  Error insertando '{nombre}': {e}")
    print(f"\n✅ Fuentes insertadas:  {inserted}")
    print(f"🔄 Fuentes actualizadas: {updated}")
    print(f"⏭️  Ya existían:         {skipped}")
    print(f"📊 Total en DB:         {inserted + skipped}")

if __name__ == "__main__":
    seed()
