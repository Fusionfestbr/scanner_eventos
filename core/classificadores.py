"""
Módulo de classificação automática de eventos.
Classifica eventos por escopo geográfico e categoria com base em palavras-chave.
NÃO modifica dados existentes — apenas adiciona campos novos.
"""
import re
import unicodedata

CIDADES_BRASILEIRAS = {
    "são paulo", "sp", "rio de janeiro", "rj", "brasília", "df",
    "belo horizonte", "bh", "curitiba", "pr", "porto alegre", "rs",
    "salvador", "ba", "recife", "pe", "fortaleza", "ce", "manaus", "am",
    "belém", "pa", "goiânia", "go", "campinas", "sp", "florianópolis", "sc",
    "vitoria", "es", "campo grande", "ms", "cuiabá", "mt", "joão pessoa", "pb",
    "natal", "rn", "maceió", "al", "aracaju", "se", "teresina", "pi",
    "são luís", "ma", "palmas", "to", "rio branco", "ac", "boa vista", "rr",
    "macapá", "ap", "santos", "sp", "ribeirão preto", "sp", "uberlândia", "mg",
    "londrina", "pr", "joinville", "sc", "niterói", "rj", "contagem", "mg",
    "são bernardo", "sp", "santo andré", "sp", "osasco", "sp", "guarulhos", "sp",
    "bh", "barueri", "alphaville", "interlagos", "morumbi", "copacabana",
    "leblon", "ipanema", "botafogo", "flamengo", "tijuca", "vila madalena",
    "pinheiros", "itaim", "moema", "paraíso", "berrini", "faria lima",
    "anhangabaú", "pacaembu", "marchetti", "lapa", "bom retiro",
    "brasilia", "brasília", "df", "distrito federal"
}

PAISES_INTERNACIONAIS = {
    "usa", "eua", "estados unidos", "united states", "new york", "los angeles",
    "miami", "orlando", "las vegas", "chicago", "houston", "atlanta",
    "portugal", "lisboa", "porto", "faro", "braga", "coimbra",
    "espanha", "spain", "madrid", "barcelona", "sevilha", "valencia",
    "france", "frança", "paris", "lyon", "marseille", "nice",
    "italia", "itália", "rome", "roma", "milan", "milão", "florence", "florença",
    "uk", "london", "londres", "manchester", "liverpool", "england", "inglaterra",
    "germany", "alemanha", "berlin", "berlim", "munich", "munique", "hamburg",
    "japan", "japão", "tokyo", "tóquio", "osaka", "kyoto",
    "argentina", "buenos aires", "cordoba", "rosario",
    "mexico", "méxico", "mexico city", "cancun", "guadalajara",
    "colombia", "colômbia", "bogota", "bogotá", "medellin",
    "chile", "santiago",
    "peru", "lima",
    "uruguay", "uruguai", "montevideo",
    "canada", "canadá", "toronto", "vancouver", "montreal",
    "australia", "austrália", "sydney", "melbourne",
    "holanda", "netherlands", "amsterdam",
    "suiça", "suíça", "switzerland", "zurich", "zurique",
    "austria", "áustria", "vienna", "viena",
    "suecia", "suécia", "sweden", "stockholm",
    "noruega", "norway", "oslo",
    "dinamarca", "denmark", "copenhagen",
    "irlanda", "ireland", "dublin",
    "grécia", "greece", "athens", "atenas",
    "turquia", "turkey", "istanbul",
    "emirados", "dubai", "dubae", "uae"
}

CATEGORIAS = {
    "show": [
        "show", "concerto", "turnê", "tour", "live", "apresentação",
        "acústico", "unplugged", "ao vivo", "musical", "música",
        "festival de música", "batidão", "rave", "balada", "dj set",
        "sertanejo", "pagode", "samba", "funk", "rap", "hip hop",
        "rock", "pop", "mpb", "sertanejo", "forró", "piseiro",
        "eletrônica", "techno", "house", "trance", "edm"
    ],
    "festival": [
        "festival", "fest", "lollapalooza", "rock in rio",
        "coachella", "tomorrowland", "edc", "ultra", "arpoador",
        "virada cultural", "parada", "carnaval", "réveillon",
        "ano novo", "virada", "mega fest", "summer fest"
    ],
    "esporte": [
        "futebol", "jogo", "partida", "campeonato", "copa",
        "liga", "final", "semi", "quartas", "clássico",
        "corrida", "maratona", "triathlon", "ironman",
        "mma", "ufc", "luta", "boxing", "boxe",
        "basquete", "nba", "vôlei", "tênis", "atp", "wta",
        "fórmula 1", "f1", "stock car", "motocross", "rally",
        "surf", "skate", "games", "esports", "e-sports"
    ],
    "teatro": [
        "teatro", "peça", "drama", "comédia", "musical teatro",
        "ópera", "opera", "ballet", "balé", "dança", "circo",
        "stand-up", "stand up", "comedy", "humor", "improviso"
    ],
    "standup": [
        "stand-up", "stand up", "standup", "comedy", "comédia stand",
        "humor", "improviso", "comediante", "stand-up comedy"
    ],
    "conferencia": [
        "conferência", "congresso", "seminário", "workshop",
        "palestra", "talk", "ted", "expo", "feira", "convenção",
        "summit", "meetup", "encontro", "fórum", "symposium"
    ],
    "religioso": [
        "gospel", "religioso", "igreja", "culto", "missa",
        "retiro", "louvor", "adoração", "worship", "congresso gospel"
    ]
}

# Categorias que interessam ao negócio (revenda de ingressos de música)
CATEGORIAS_MUSICAIS = {"show", "festival"}

# Categorias fora do escopo musical — rejeitadas quando
# COLETA_SOMENTE_MUSICA está ativo
CATEGORIAS_NAO_MUSICAS = {"esporte", "teatro", "standup", "conferencia", "religioso"}

# Gêneros musicais reconhecidos no título/artista
GENEROS = {
    "sertanejo": ["sertanejo", "caipira", "viola", "universitário", "churrasquinho"],
    "funk": ["funk", "baile funk", "mandelão", "bruxaria", "dj vazado"],
    "rap": ["rap", "hip hop", "hiphop"],
    "trap": ["trap", "drill"],
    "rock": ["rock", "metal", "punk", "grunge", "indie rock", "emo"],
    "pop": ["pop", "k-pop", "kpop", "j-pop", "jpop"],
    "eletronica": ["eletrônica", "eletronica", "techno", "house", "trance",
                   "edm", "progressive", "drum and bass", "dnb", "dubstep",
                   "hardstyle", "rave"],
    "samba": ["samba", "sambista", "gafieira", "roda de samba", "pagode de mesa"],
    "pagode": ["pagode", "pagodão", "pagodao"],
    "mpb": ["mpb", "bossa nova", "bossa"],
    "forro": ["forró", "forro", "piseiro", "pisadinha", "corridinha", "arrocha"],
    "gospel": ["gospel", "louvor", "adoração", "worship"],
    "reggae": ["reggae"],
    "jazz": ["jazz", "blues", "soul"],
    "axe": ["axé", "axé"],
    "reveillon": ["réveillon", "reveillon", "vira-ano", "ano novo", "baile de gala"],
}

# Palavras que indicam NÃO ser um show musical
# (ajuda contra categoria "outros", sem depender de LLM)
_NAO_MUSICAL_FORTES = [
    "workshop", "curso", "palestra", "congresso", "seminário", "seminario",
    "feira", "expo ", "expopais", "convenção", "convencao", "leilão", "leilao",
    "futebol", "campeonato", "brasileirão", "brasileirao", "corrida", "maratona",
    "ufc", "luta", "jogo do", "clássico", "clássicos",
    "peça de teatro", "teatro infantil", "musical infantil",
    "biblioteca", "museu", "galeria", "cinema", "documentário",
    "aula", "treinamento", "imersão", "imersao", "formação",
    "lançamento de produto",
]


def classificar_escopo(evento: dict) -> str:
    """
    Classifica evento como nacional ou internacional.
    
    Args:
        evento: Dict com campos 'cidade' e/ou 'nome'
    
    Returns:
        "nacional" ou "internacional"
    """
    cidade = (evento.get("cidade", "") or "").lower()
    nome = (evento.get("nome", "") or "").lower()
    texto = f"{cidade} {nome}"

    for pais in PAISES_INTERNACIONAIS:
        if pais in texto:
            return "internacional"

    for cidade_br in CIDADES_BRASILEIRAS:
        if cidade_br in texto:
            return "nacional"

    if cidade and len(cidade) > 0:
        return "nacional"

    return "nacional"


def classificar_categoria(evento: dict) -> str:
    """
    Classifica evento por categoria com base em palavras-chave.
    
    Args:
        evento: Dict com campos 'nome' e/ou 'artista'
    
    Returns:
        Categoria identificada ou "outros"
    """
    nome = (evento.get("nome", "") or "").lower()
    artista = (evento.get("artista", "") or "").lower()
    texto = f"{nome} {artista}"

    for categoria, palavras in CATEGORIAS.items():
        for palavra in palavras:
            if palavra in texto:
                return categoria

    return "outros"


def extrair_pais(evento: dict) -> str:
    """
    Extrai o país do evento com base na cidade.
    
    Args:
        evento: Dict com campo 'cidade'
    
    Returns:
        Nome do país ou "Brasil"
    """
    cidade = (evento.get("cidade", "") or "").lower()

    mapa_paises = {
        "usa": "EUA", "eua": "EUA", "estados unidos": "EUA",
        "united states": "EUA", "new york": "EUA", "miami": "EUA",
        "los angeles": "EUA", "las vegas": "EUA", "orlando": "EUA",
        "portugal": "Portugal", "lisboa": "Portugal", "porto": "Portugal",
        "espanha": "Espanha", "spain": "Espanha", "madrid": "Espanha",
        "barcelona": "Espanha",
        "france": "França", "frança": "França", "paris": "França",
        "italia": "Itália", "itália": "Itália", "roma": "Itália",
        "uk": "Reino Unido", "london": "Reino Unido", "londres": "Reino Unido",
        "england": "Reino Unido", "inglaterra": "Reino Unido",
        "germany": "Alemanha", "alemanha": "Alemanha", "berlin": "Alemanha",
        "japan": "Japão", "japão": "Japão", "tokyo": "Japão",
        "argentina": "Argentina", "buenos aires": "Argentina",
        "mexico": "México", "méxico": "México",
        "colombia": "Colômbia", "colômbia": "Colômbia",
        "chile": "Chile", "santiago": "Chile",
        "canada": "Canadá", "canadá": "Canadá", "toronto": "Canadá",
        "australia": "Austrália", "austrália": "Austrália", "sydney": "Austrália",
        "emirados": "Emirados Árabes", "dubai": "Emirados Árabes",
        "holanda": "Holanda", "netherlands": "Holanda", "amsterdam": "Holanda"
    }

    for chave, pais in mapa_paises.items():
        if chave in cidade:
            return pais

    return "Brasil"


def enriquecer_evento(evento: dict) -> dict:
    """
    Adiciona campos de classificação ao evento.
    NÃO remove nenhum campo existente.
    
    Args:
        evento: Dict do evento
    
    Returns:
        Mesmo dict com campos adicionais:
        - tipo_geografico: "nacional" ou "internacional"
        - categoria: "show", "festival", "esporte", "teatro", "standup", etc.
        - pais: nome do país
    """
    evento["tipo_geografico"] = classificar_escopo(evento)
    evento["categoria"] = classificar_categoria(evento)
    evento["pais"] = extrair_pais(evento)
    return evento


def enriquecer_lista(eventos: list) -> list:
    """
    Enriquece uma lista inteira de eventos.
    
    Args:
        eventos: Lista de eventos
    
    Returns:
        Nova lista com eventos enriquecidos
    """
    return [enriquecer_evento(e.copy()) for e in eventos]


def classificar_genero(evento: dict) -> str:
    """
    Identifica o gênero musical do evento pelo título/artista.

    Returns:
        Nome do gênero ("rock", "sertanejo", ...) ou "" quando
        não é possível identificar por regras.
    """
    nome = (evento.get("nome", "") or "").lower()
    artista = (evento.get("artista", "") or "").lower()
    categoria_fonte = (evento.get("categoria_fonte", "") or "").lower()
    texto = _sem_acentos(f"{nome} {artista} {categoria_fonte}")

    for genero, palavras in GENEROS.items():
        for palavra in palavras:
            # \b evita falso-positivo ("emo" dentro de "memórias")
            if re.search(r"\b" + re.escape(_sem_acentos(palavra)) + r"\b", texto, re.IGNORECASE):
                return genero

    return ""


def _sem_acentos(texto: str) -> str:
    if not texto:
        return ""
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def parece_nao_musical(evento: dict) -> bool:
    """
    Heurística rápida (sem IA): o título bate em alguma expressão
    forte de não-música (workshop, futebol, palestra...)?
    """
    texto = _sem_acentos(
        f"{(evento.get('nome') or '')} {(evento.get('categoria_fonte') or '')}"
    ).lower()
    return any(palavra in texto for palavra in _NAO_MUSICAL_FORTES)
