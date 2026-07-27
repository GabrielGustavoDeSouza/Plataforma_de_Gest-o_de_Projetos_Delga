import streamlit as st
from database import autenticar
from assets import LOGO_LIGHT_DATA_URI
from theme import toggle_tema_button

NAVY  = "#0B0F2B"
BLUE  = "#1B2A9E"
BLUE2 = "#33459E"
RED   = "#D93B3B"

def login_page():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html,body,[class*="css"]{{font-family:'Inter',sans-serif;}}
    #MainMenu{{visibility:hidden;}}footer{{visibility:hidden;}}
    header[data-testid="stHeader"]{{display:none;}}
    section[data-testid="stSidebar"]{{display:none!important;}}
    .block-container{{padding-top:3vh!important;max-width:1400px;}}

    [data-testid="stAppViewContainer"], .stApp{{
      background:
        radial-gradient(circle at 12% 8%,{BLUE}33 0%,transparent 38%),
        radial-gradient(circle at 88% 85%,{BLUE2}2b 0%,transparent 42%),
        repeating-linear-gradient(115deg,rgba(255,255,255,.02) 0px,rgba(255,255,255,.02) 1px,transparent 1px,transparent 64px),
        linear-gradient(160deg,{NAVY} 0%,#10143A 55%,#151A4A 100%);
      background-attachment:fixed;
    }}

    .login-logo-wrap{{display:flex;justify-content:center;margin-bottom:22px;}}
    .login-logo-wrap img{{height:54px;filter:drop-shadow(0 4px 18px rgba(20,40,255,.35));}}

    .login-eyebrow{{text-align:center;color:rgba(255,255,255,.45);font-size:11px;
      font-weight:600;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:8px;}}
    .login-title{{text-align:center;color:white;font-size:26px;font-weight:800;
      letter-spacing:.2px;margin-bottom:6px;}}
    .login-sub{{text-align:center;color:rgba(255,255,255,.5);font-size:13px;
      margin-bottom:36px;}}

    [data-testid="stForm"]{{
      background:rgba(255,255,255,.045);backdrop-filter:blur(18px);
      -webkit-backdrop-filter:blur(18px);border:1px solid rgba(255,255,255,.09)!important;
      border-radius:20px!important;padding:34px 40px 26px!important;
      box-shadow:0 24px 70px rgba(0,0,0,.35),0 2px 0 rgba(255,255,255,.04) inset;}}
    [data-testid="stForm"] [data-testid="stTextInput"] label{{
      color:rgba(255,255,255,.55)!important;font-size:11px!important;
      font-weight:600!important;text-transform:uppercase;letter-spacing:.6px;}}
    [data-testid="stForm"] [data-testid="stTextInput"] input{{
      background:rgba(255,255,255,.07)!important;border:1px solid rgba(255,255,255,.16)!important;
      border-radius:9px!important;color:white!important;padding:11px 14px!important;
      caret-color:{BLUE2};}}
    [data-testid="stForm"] [data-testid="stTextInput"] input::placeholder{{color:rgba(255,255,255,.30)!important;}}
    [data-testid="stForm"] [data-testid="stTextInput"] input:focus{{
      border-color:{BLUE2}!important;box-shadow:0 0 0 3px {BLUE}30!important;}}
    [data-testid="stForm"] [data-testid="stTextInputRootElement"]{{
      background:transparent!important;border:none!important;}}
    [data-testid="stForm"] svg{{fill:rgba(255,255,255,.55)!important;}}
    [data-testid="stForm"] [data-testid="stFormSubmitButton"] button{{
      background:linear-gradient(120deg,{BLUE} 0%,{BLUE2} 100%)!important;
      border:none!important;border-radius:9px!important;width:100%;
      font-weight:700!important;letter-spacing:.3px;padding:11px 0!important;
      box-shadow:0 8px 24px {BLUE}45!important;transition:filter .15s;margin-top:6px;}}
    [data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover{{filter:brightness(1.15);}}
    [data-testid="stForm"] [data-testid="stFormSubmitButton"] button p{{color:white!important;font-weight:700!important;}}

    .login-foot{{text-align:center;color:rgba(255,255,255,.28);font-size:10px;
      margin-top:26px;letter-spacing:.3px;}}
    .login-credit{{text-align:center;color:rgba(255,255,255,.16);font-size:9px;
      margin-top:6px;letter-spacing:.3px;}}
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.15, 1])
    with col2:
        st.markdown(f"""
        <div style="margin-top:4vh;">
          <div class="login-logo-wrap"><img src="{LOGO_LIGHT_DATA_URI}"></div>
          <div class="login-eyebrow">Grupo Delga</div>
          <div class="login-title">Plataforma de Gestão de Projetos</div>
          <div class="login-sub">Redução de Custos &amp; Performance Operacional</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("E-mail", placeholder="seu@delga.com.br")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            btn   = st.form_submit_button("Entrar", use_container_width=True)

        st.markdown(f"""
        <div class="login-foot">Grupo Delga Ind. e Com. · Acesso restrito a colaboradores autorizados</div>
        <div class="login-credit">Desenvolvido por Gabriel Souza · Lato Sensu em Gestão de Projetos</div>
        """, unsafe_allow_html=True)

        if btn:
            user = autenticar(email, senha)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")

    return "user" in st.session_state

def require_login():
    if "user" not in st.session_state:
        st.warning("Faça login para acessar esta página.")
        st.stop()

def sidebar_user():
    user = st.session_state.get("user", {})
    with st.sidebar:
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,{NAVY} 0%,#171B4C 100%);
             border-radius:10px;padding:14px 16px;margin-bottom:16px;
             border:1px solid rgba(255,255,255,.06);">
          <div style="color:rgba(255,255,255,.5);font-size:9px;text-transform:uppercase;
               letter-spacing:.6px;">Conectado como</div>
          <div style="color:white;font-size:13px;font-weight:600;margin-top:3px;">
            {user.get('nome','')}</div>
          <div style="color:rgba(255,255,255,.45);font-size:11px;">
            {user.get('unidade') or 'Acesso Global'}</div>
          <div style="display:inline-block;background:{BLUE}26;
               color:{BLUE2};font-size:9px;padding:2px 8px;
               border-radius:10px;margin-top:6px;text-transform:uppercase;
               letter-spacing:.4px;border:1px solid {BLUE}40;">{user.get('perfil','')}</div>
        </div>
        """, unsafe_allow_html=True)

        toggle_tema_button()

        if st.button("🚪 Sair", use_container_width=True):
            del st.session_state["user"]
            st.rerun()
