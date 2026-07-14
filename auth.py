import streamlit as st
from database import autenticar

NAVY = "#1C2B4A"
RED  = "#C8202E"

def login_page():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html,body,[class*="css"]{{font-family:'Inter',sans-serif;background:#F4F6FB;}}
    #MainMenu{{visibility:hidden;}}footer{{visibility:hidden;}}
    header[data-testid="stHeader"]{{display:none;}}
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:48px 40px;
             box-shadow:0 8px 40px rgba(28,43,74,.13);text-align:center;margin-top:60px;">
          <div style="width:64px;height:64px;background:{NAVY};border-radius:14px;
               display:flex;align-items:center;justify-content:center;
               margin:0 auto 20px;font-size:22px;font-weight:800;color:white;">GD</div>
          <div style="font-size:22px;font-weight:700;color:{NAVY};margin-bottom:4px;">
            Plataforma Delga</div>
          <div style="font-size:13px;color:#8A9BB0;margin-bottom:32px;">
            Gestão de Projetos & Redução de Custos</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("E-mail", placeholder="seu@delga.com.br")
            senha = st.text_input("Senha", type="password", placeholder="••••••••")
            btn   = st.form_submit_button("Entrar", use_container_width=True)

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
        <div style="background:{NAVY};border-radius:10px;padding:14px 16px;margin-bottom:16px;">
          <div style="color:rgba(255,255,255,.5);font-size:9px;text-transform:uppercase;
               letter-spacing:.6px;">Conectado como</div>
          <div style="color:white;font-size:13px;font-weight:600;margin-top:3px;">
            {user.get('nome','')}</div>
          <div style="color:rgba(255,255,255,.45);font-size:11px;">
            {user.get('unidade') or 'Acesso Global'}</div>
          <div style="display:inline-block;background:rgba(255,255,255,.12);
               color:rgba(255,255,255,.7);font-size:9px;padding:2px 8px;
               border-radius:10px;margin-top:6px;text-transform:uppercase;
               letter-spacing:.4px;">{user.get('perfil','')}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Sair", use_container_width=True):
            del st.session_state["user"]
            st.rerun()
