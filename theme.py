import streamlit as st

# ── Paletas ──────────────────────────────────────────────────────────────
# Cada paleta cobre tanto as cores "de marca" (NAVY, BLUE, GREEN...) que já
# eram passadas pra cada página quanto as cores "estruturais" novas (fundo
# de página, fundo de cartão, borda, texto apagado) que a casca do app usa
# pra se adaptar ao tema.
PALETAS = {
    "claro": {
        "NAVY": "#0B0F2B", "BLUE": "#1B2A9E", "BLUE2": "#33459E", "GREEN": "#1AA260",
        "AMBER": "#E8A838", "RED": "#D93B3B", "TEAL": "#20C997", "SILVER": "#8A9BB0",
        "LIGHT": "#F4F6FB",
        "BG": "#F4F6FB", "SURFACE": "#FFFFFF", "SURFACE_2": "#FAFBFC",
        "BORDER": "#EEF0F3", "TEXT": "#0B0F2B", "TEXT_MUTED": "#8A9BB0",
        "HOVER": "#F0F4FA", "SHADOW_1": "rgba(11,15,43,.06)", "SHADOW_2": "rgba(11,15,43,.04)",
        "INPUT_BG": "#FFFFFF", "SIDEBAR_BG": "#FFFFFF",
    },
    "escuro": {
        "NAVY": "#E7E9F5", "BLUE": "#5B7CFA", "BLUE2": "#7E96FF", "GREEN": "#3DD68C",
        "AMBER": "#F0B94D", "RED": "#F16565", "TEAL": "#3EE0B0", "SILVER": "#9AA3C0",
        "LIGHT": "#171B33",
        "BG": "#0B0E1F", "SURFACE": "#151935", "SURFACE_2": "#11142B",
        "BORDER": "#262B4A", "TEXT": "#E7E9F5", "TEXT_MUTED": "#9AA3C0",
        "HOVER": "#1D2142", "SHADOW_1": "rgba(0,0,0,.35)", "SHADOW_2": "rgba(0,0,0,.25)",
        "INPUT_BG": "#1B1F40", "SIDEBAR_BG": "#0E1130",
    },
}

def tema_atual():
    return st.session_state.get("tema", "claro")

def cores():
    """Dict com todas as cores da paleta ativa — usar pra montar o CSS
    global e pra passar como **colors pras páginas, igual já era feito."""
    return PALETAS[tema_atual()]

def toggle_tema_button():
    """Botão de alternância claro/escuro — chamar dentro da sidebar, perto
    do bloco 'Conectado como'."""
    tema = tema_atual()
    st.markdown('<p style="font-size:9px;color:var(--muted,#8A9BB0);text-transform:uppercase;'
               'letter-spacing:.6px;margin:10px 0 4px;">Aparência</p>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("☀️ Claro", key="btn_tema_claro", use_container_width=True,
                     type="primary" if tema == "claro" else "secondary"):
            if tema != "claro":
                st.session_state["tema"] = "claro"; st.rerun()
    with c2:
        if st.button("🌙 Escuro", key="btn_tema_escuro", use_container_width=True,
                     type="primary" if tema == "escuro" else "secondary"):
            if tema != "escuro":
                st.session_state["tema"] = "escuro"; st.rerun()
