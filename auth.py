"""
auth.py — Controle de sessão e permissões
"""
import streamlit as st
from database import autenticar

NAVY  = "#1C2B4A"
RED   = "#C8202E"
LIGHT = "#F4F6FB"

def login_page():
    """Renderiza tela de login. Retorna True se autenticado."""
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html,body,[class*="css"]{{font-family:'Inter',sans-serif;background:{LIGHT};}}
    #MainMenu{{visibility:hidden;}}footer{{visibility:hidden;}}
    header[data-testid="stHeader"]{{display:none;}}
    .login-wrap{{
      max-width:420px;margin:80px auto;
      background:white;border-radius:16px;
      box-shadow:0 8px 40px rgba(28,43,74,.13);
      padding:48px 40px;text-align:center;
    }}
    .login-logo{{
      width:64px;height:64px;background:{NAVY};border-radius:14px;
      display:flex;align-items:center;justify-content:center;
      margin:0 auto 20px;font-size:28px;font-weight:800;color:white;
      letter-spacing:-1px;
    }}
    .login-title{{font-size:22px;font-weight:700;color:{NAVY};margin:0 0 4px;}}
    .login-sub{{font-size:13px;color:#8A9BB0;margin-bottom:32px;}}
    .login-err{{
      background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;
      color:#DC2626;font-size:13px;padding:10px 14px;margin-bottom:16px;
    }}
    </style>
    <div class="login-wrap">
      <div class="login-logo">GD</div>
      <div class="login-title">Plataforma Delga</div>
      <div class="login-sub">Gestão de Projetos & Redução de Custos</div>
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
    """Chama no topo de cada página. Redireciona para login se não autenticado."""
    if "user" not in st.session_state:
        st.warning("Faça login para acessar esta página.")
        st.stop()

def require_perfil(*perfis):
    """Garante que o usuário tem o perfil necessário."""
    user = st.session_state.get("user", {})
    if user.get("perfil") not in perfis:
        st.error("Você não tem permissão para acessar esta área.")
        st.stop()

def user_pode_ver_unidade(unidade_nome: str) -> bool:
    """Admin e gestor global veem tudo. Operador só vê sua unidade."""
    user = st.session_state.get("user", {})
    if user.get("perfil") in ("admin", "gestor") and not user.get("unidade"):
        return True
    return user.get("unidade") == unidade_nome

def sidebar_user():
    """Renderiza info do usuário na sidebar."""
    user = st.session_state.get("user", {})
    with st.sidebar:
        st.markdown(f"""
        <div style="background:{NAVY};border-radius:10px;padding:14px 16px;margin-bottom:16px;">
          <div style="color:rgba(255,255,255,.5);font-size:9px;text-transform:uppercase;letter-spacing:.6px;">Conectado como</div>
          <div style="color:white;font-size:13px;font-weight:600;margin-top:3px;">{user.get('nome','')}</div>
          <div style="color:rgba(255,255,255,.45);font-size:11px;">{user.get('unidade') or 'Acesso Global'}</div>
          <div style="display:inline-block;background:rgba(255,255,255,.12);color:rgba(255,255,255,.7);
               font-size:9px;padding:2px 8px;border-radius:10px;margin-top:6px;text-transform:uppercase;
               letter-spacing:.4px;">{user.get('perfil','')}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Sair", use_container_width=True):
            del st.session_state["user"]
            st.rerun()
