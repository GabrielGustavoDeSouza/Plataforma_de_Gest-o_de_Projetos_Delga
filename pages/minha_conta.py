import streamlit as st
from database import alterar_senha, listar_usuarios, atualizar_projeto

def render(user, **colors):
    NAVY=colors.get("NAVY","#0B0F2B")
    GREEN=colors.get("GREEN","#1AA260")
    RED=colors.get("RED","#D93B3B")
    SILVER=colors.get("SILVER","#8A9BB0")

    st.markdown('<span class="st">Minha Conta</span>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:white;border-radius:12px;padding:20px 24px;
         box-shadow:0 1px 4px rgba(28,43,74,.06);margin-bottom:16px;">
      <div style="font-size:9px;font-weight:600;color:{SILVER};
           text-transform:uppercase;letter-spacing:.8px;margin-bottom:8px;">
        Seus dados</div>
      <div style="font-size:18px;font-weight:700;color:{NAVY};">
        {user.get('nome','')}</div>
      <div style="font-size:12px;color:{SILVER};margin-top:4px;">
        {user.get('email','')}</div>
      <div style="display:flex;gap:10px;margin-top:10px;">
        <span style="background:#EEF0F3;color:{NAVY};font-size:10px;
             padding:3px 10px;border-radius:10px;font-weight:600;">
          {user.get('perfil','').upper()}</span>
        <span style="background:#EEF0F3;color:{NAVY};font-size:10px;
             padding:3px 10px;border-radius:10px;">
          {user.get('unidade') or 'Acesso Global'}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Alterar minha senha**")
    with st.form("form_minha_senha"):
        atual = st.text_input("Senha atual", type="password")
        nova  = st.text_input("Nova senha", type="password")
        conf  = st.text_input("Confirmar nova senha", type="password")
        salvar = st.form_submit_button("🔑 Alterar Senha",
                                        use_container_width=True)

    if salvar:
        from database import hash_senha, get_conn
        conn = get_conn()
        row  = conn.execute(
            "SELECT senha_hash FROM usuarios WHERE id=?",
            (user["id"],)).fetchone()
        conn.close()
        if not row or row["senha_hash"] != hash_senha(atual):
            st.error("Senha atual incorreta.")
        elif nova != conf:
            st.error("As senhas não conferem.")
        elif len(nova) < 6:
            st.error("Mínimo 6 caracteres.")
        else:
            alterar_senha(user["id"], nova)
            st.success("✅ Senha alterada com sucesso!")
