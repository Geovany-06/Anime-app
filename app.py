import streamlit as st
import requests
import json

# =========================================================
# CONFIGURACIÓN DE PÁGINA
# =========================================================
st.set_page_config(page_title="AnimeFlix", page_icon="🎬", layout="wide")

# =========================================================
# ESTILO TIPO NETFLIX (CSS)
# =========================================================
st.markdown(
    """
    <style>
    .stApp { background-color: #141414; }
    h1, h2, h3, h4, p, span, label { color: #ffffff !important; }
    .anime-card {
        background-color: #1f1f1f;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 14px;
        transition: transform 0.15s ease-in-out;
    }
    .anime-card:hover { transform: scale(1.03); }
    .anime-title {
        font-weight: 700;
        font-size: 0.95rem;
        margin-top: 6px;
        min-height: 2.6em;
    }
    .anime-meta { color: #b3b3b3 !important; font-size: 0.8rem; }
    .netflix-title {
        color: #E50914 !important;
        font-weight: 900;
        letter-spacing: 1px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

JIKAN_BASE = "https://api.jikan.moe/v4"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


# =========================================================
# FUNCIONES PARA CONSUMIR LA API DE ANIMES (JIKAN)
# =========================================================
@st.cache_data(ttl=3600, show_spinner=False)
def jikan_top_anime(limit=12):
    try:
        r = requests.get(f"{JIKAN_BASE}/top/anime", params={"limit": limit}, timeout=15)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def jikan_search_anime(query, limit=12):
    try:
        r = requests.get(
            f"{JIKAN_BASE}/anime",
            params={"q": query, "limit": limit, "order_by": "popularity"},
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception:
        return []


def render_anime_grid(anime_list):
    if not anime_list:
        st.info("No se encontraron resultados.")
        return
    cols = st.columns(4)
    for i, anime in enumerate(anime_list):
        with cols[i % 4]:
            image_url = (
                anime.get("images", {}).get("jpg", {}).get("image_url", "")
            )
            title = anime.get("title", "Sin título")
            score = anime.get("score", "N/A")
            episodes = anime.get("episodes", "?")
            st.markdown('<div class="anime-card">', unsafe_allow_html=True)
            if image_url:
                st.image(image_url, use_container_width=True)
            st.markdown(f'<div class="anime-title">{title}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="anime-meta">⭐ {score} &nbsp;|&nbsp; {episodes} episodios</div>',
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# FUNCIÓN PARA CONSUMIR LA API DE IA (GOOGLE GEMINI)
# =========================================================
def get_ai_recommendations(preferences: str, api_key: str, debug_container=None):
    prompt = (
        "Eres un experto en anime. Basado en la siguiente descripción de gustos de un "
        "usuario, recomienda exactamente 5 animes reales y conocidos que encajen. "
        "Responde ÚNICAMENTE con un JSON válido, sin texto adicional, con este formato exacto: "
        '{"recomendaciones": [{"titulo": "...", "razon": "..."}]}\n\n'
        f"Gustos del usuario: {preferences}"
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    if debug_container is not None:
        debug_container.markdown("**📤 Petición enviada a la API (request):**")
        debug_container.code(
            f"POST {GEMINI_URL}\n\n" + json.dumps(payload, indent=2, ensure_ascii=False),
            language="json",
        )

    try:
        response = requests.post(
            f"{GEMINI_URL}?key={api_key}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if debug_container is not None:
            debug_container.markdown("**📥 Respuesta cruda de la API (response):**")
            debug_container.code(json.dumps(data, indent=2, ensure_ascii=False), language="json")

        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        raw_text = raw_text.strip().strip("```json").strip("```").strip()
        parsed = json.loads(raw_text)
        return parsed.get("recomendaciones", []), None
    except Exception as e:
        return [], str(e)


# =========================================================
# BARRA LATERAL
# =========================================================
st.sidebar.header("⚙️ Configuración")
api_key = st.sidebar.text_input(
    "API key de Google Gemini",
    type="password",
    help="Consíguela gratis en aistudio.google.com/apikey",
)
show_debug = st.sidebar.checkbox(
    "Mostrar consumo de la API (request/response)", value=True
)
st.sidebar.markdown("---")
st.sidebar.caption(
    "Catálogo de animes vía la API pública **Jikan** (MyAnimeList). "
    "Recomendaciones generadas con la API de **Google Gemini**."
)

# =========================================================
# ENCABEZADO
# =========================================================
st.markdown('<h1 class="netflix-title">🎬 ANIMEFLIX</h1>', unsafe_allow_html=True)
st.caption("Explora animes populares y recibe recomendaciones personalizadas con IA.")

# =========================================================
# BÚSQUEDA
# =========================================================
search_query = st.text_input("🔍 Buscar un anime", placeholder="Ej: Naruto, One Piece, Death Note...")

if search_query:
    st.subheader(f"Resultados para \"{search_query}\"")
    with st.spinner("Buscando..."):
        results = jikan_search_anime(search_query)
    render_anime_grid(results)
else:
    st.subheader("🔥 Top Animes")
    with st.spinner("Cargando catálogo..."):
        top_anime = jikan_top_anime()
    render_anime_grid(top_anime)

# =========================================================
# RECOMENDACIONES CON IA
# =========================================================
st.markdown("---")
st.subheader("🤖 Recomendaciones con Inteligencia Artificial")
st.caption("Describe qué tipo de anime te gusta y la IA te recomendará títulos.")

preferences = st.text_area(
    "¿Qué te gustaría ver?",
    placeholder="Ej: algo de acción y comedia, que no sea muy largo, con buena animación...",
)

col_btn, _ = st.columns([1, 3])
with col_btn:
    ask_ai = st.button("✨ Recomendarme animes", type="primary")

if ask_ai:
    if not api_key:
        st.warning("Pega tu API key de Gemini en la barra lateral para usar esta función.")
    elif not preferences.strip():
        st.warning("Escribe qué tipo de anime te gusta primero.")
    else:
        debug_box = st.container() if show_debug else None
        with st.spinner("Consultando a la IA..."):
            recommendations, error = get_ai_recommendations(preferences, api_key, debug_box)

        if error:
            st.error(f"Ocurrió un error al consumir la API: {error}")
        elif recommendations:
            st.success(f"La IA encontró {len(recommendations)} recomendaciones:")
            rec_cols = st.columns(len(recommendations))
            for i, rec in enumerate(recommendations):
                titulo = rec.get("titulo", "")
                razon = rec.get("razon", "")
                with rec_cols[i]:
                    found = jikan_search_anime(titulo, limit=1)
                    if found:
                        image_url = found[0].get("images", {}).get("jpg", {}).get("image_url", "")
                        if image_url:
                            st.image(image_url, use_container_width=True)
                    st.markdown(f"**{titulo}**")
                    st.caption(razon)
        else:
            st.info("La IA no devolvió recomendaciones, intenta de nuevo.")
