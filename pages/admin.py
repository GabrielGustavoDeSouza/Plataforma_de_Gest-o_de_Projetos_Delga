"""pages/admin.py — Painel de Administração"""
import streamlit as st
from database import listar_usuarios, criar_usuario, listar_unidades, atualizar_meta, alterar_senha

def render(user, NAVY, RED, GREEN, AMBER, LIGHT):
    if user.get("perfil") != "admin":
        st.error("⛔ Acesso restrito a administradores.")
        return

    st.markdown(f'<span class="st">Administração da Plataforma</span>', unsafe_allow_html=True)

    tab_users, tab_metas, tab_senha = st.tabs(["👥 Usuários", "🎯 Metas por Unidade", "🔑 Alterar Senha"])

    # ── Usuários ──────────────────────────────────────────────────────────────
    with tab_users:
        usuarios = listar_usuarios()
        st.markdown(f"**{len(usuarios)} usuários cadastrados**")

        rows = "".join(f"""<tr>
          <td style="font-size:11px;font-weight:600;">{u['nome']}</td>
          <td style="font-size:11px;">{u['email']}</td>
          <td style="font-size:11px;">{u['perfil']}</td>
          <td style="font-size:11px;">{u.get('unidade_nome') or '— Global'}</td>
          <td style="font-size:11px;">{'✅ Ativo' if u['ativo'] else '❌ Inativo'}</td>
        </tr>""" for u in usuarios)

        st.markdown(f"""
        <table class="dt">
          <thead><tr><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Unidade</th><th>Status</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Criar novo usuário**")
        unidades = listar_unidades()
        nomes_u  = ["— Acesso Global"] + [u["nome"] for u in unidades]

        with st.form("form_novo_user"):
            c1, c2 = st.columns(2)
            with c1:
                nome_u  = st.text_input("Nome completo")
                email_u = st.text_input("E-mail")
                senha_u = st.text_input("Senha inicial", type="password")
            with c2:
                perfil_u  = st.selectbox("Perfil", ["operador","gestor","admin"])
                unidade_u = st.selectbox("Unidade (opcional)", nomes_u)

            criar_btn = st.form_submit_button("➕ Criar Usuário", use_container_width=True)

        if criar_btn:
            if not nome_u or not email_u or not senha_u:
                st.error("Preencha todos os campos obrigatórios.")
            else:
                unid = None if unidade_u == "— Acesso Global" else unidade_u
                try:
                    criar_usuario(nome_u, email_u, senha_u, perfil_u, unid)
                    st.success(f"✅ Usuário **{nome_u}** criado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    # ── Metas ─────────────────────────────────────────────────────────────────
    with tab_metas:
        st.markdown("**Definir Meta Anual por Unidade**")
        unidades = listar_unidades()

        with st.form("form_metas"):
            metas = {}
            for u in unidades:
                metas[u["nome"]] = st.number_input(
                    f"{u['nome']} ({u['tipo']})",
                    value=float(u.get("meta_anual",0)),
                    step=10000.0, format="%.2f", key=f"meta_{u['id']}"
                )
            salvar_m = st.form_submit_button("💾 Salvar Metas", use_container_width=True)

        if salvar_m:
            for nome, meta in metas.items():
                atualizar_meta(nome, meta)
            st.success("✅ Metas atualizadas!")

    # ── Alterar Senha ─────────────────────────────────────────────────────────
    with tab_senha:
        usuarios = listar_usuarios()
        sel_u = st.selectbox("Usuário:", [u["nome"] for u in usuarios])
        user_sel = next(u for u in usuarios if u["nome"]==sel_u)

        with st.form("form_senha"):
            nova = st.text_input("Nova senha", type="password")
            conf = st.text_input("Confirmar senha", type="password")
            alt  = st.form_submit_button("🔑 Alterar Senha")

        if alt:
            if nova != conf:
                st.error("Senhas não conferem.")
            elif len(nova) < 6:
                st.error("Senha deve ter ao menos 6 caracteres.")
            else:
                alterar_senha(user_sel["id"], nova)
                st.success(f"✅ Senha de **{sel_u}** alterada!")
