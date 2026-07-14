import streamlit as st
from database import (listar_usuarios, criar_usuario, alterar_senha,
                      listar_unidades, criar_unidade,
                      get_todas_metas, set_meta)

PERFIS_LBL = {
    "operador":     "Operador — só vê sua unidade",
    "cost_control": "Cost Control — valida e lança real em todas as unidades",
    "gestor":       "Gestor — visualiza todas as unidades",
    "admin":        "Admin — acesso total",
}

def render(user, **colors):
    NAVY=colors.get("NAVY","#1C2B4A")
    TEAL=colors.get("TEAL","#20C997")

    if user["perfil"] != "admin":
        st.error("⛔ Acesso restrito a administradores.")
        return

    st.markdown('<span class="st">Administração da Plataforma</span>',
                unsafe_allow_html=True)

    tab_users, tab_metas, tab_unid, tab_senha = st.tabs([
        "👥 Usuários",
        "🎯 Metas por Unidade",
        "🏭 Unidades / Áreas",
        "🔑 Alterar Senhas"
    ])

    # ── Usuários ──────────────────────────────────────────────────────────────
    with tab_users:
        usuarios = listar_usuarios()
        rows = "".join(f"""<tr>
          <td style="font-size:11px;font-weight:600;">{u['nome']}</td>
          <td style="font-size:11px;">{u['email']}</td>
          <td style="font-size:11px;">{PERFIS_LBL.get(u['perfil'], u['perfil'])}</td>
          <td style="font-size:11px;">{u.get('unidade') or '— Global'}</td>
          <td style="font-size:11px;">{'✅ Ativo' if u['ativo'] else '❌ Inativo'}</td>
        </tr>""" for u in usuarios)

        st.markdown(f"""
        <table class="dt">
          <thead><tr>
            <th>Nome</th><th>E-mail</th><th>Perfil</th>
            <th>Unidade</th><th>Status</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Criar novo usuário**")

        unidades = listar_unidades()
        nomes_u  = ["— Acesso Global"] + [u["nome"] for u in unidades]

        with st.form("form_user", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1:
                nome_u  = st.text_input("Nome completo *")
                email_u = st.text_input("E-mail *")
                senha_u = st.text_input("Senha inicial *", type="password")
            with c2:
                perfil_u  = st.selectbox("Perfil *",
                    list(PERFIS_LBL.keys()),
                    format_func=lambda x: PERFIS_LBL[x])
                unidade_u = st.selectbox(
                    "Unidade (Global para admin/gestor/Cost Control)",
                    nomes_u)

            if st.form_submit_button("➕ Criar Usuário",
                                      use_container_width=True):
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
        st.markdown("**Definir Meta Anual por Unidade / Área**")

        anos = list(range(2025, 2030))
        ano_sel = st.selectbox("Ano:", anos,
            index=anos.index(2026) if 2026 in anos else 0,
            key="adm_ano")

        metas = get_todas_metas(ano_sel)

        with st.form("form_metas"):
            vals = {}
            for m in metas:
                vals[m["nome"]] = st.number_input(
                    f"{m['nome']} ({m['tipo']})",
                    value=float(m["valor"]),
                    step=10000.0, format="%.2f",
                    key=f"meta_{m['nome']}_{ano_sel}")

            if st.form_submit_button("💾 Salvar Metas",
                                      use_container_width=True):
                for nome, val in vals.items():
                    set_meta(nome, ano_sel, val)
                st.success("✅ Metas salvas!")

    # ── Unidades ──────────────────────────────────────────────────────────────
    with tab_unid:
        unidades = listar_unidades(so_ativas=False)
        rows_u = "".join(f"""<tr>
          <td style="font-size:11px;font-weight:600;">{u['nome']}</td>
          <td style="font-size:11px;">{u['tipo']}</td>
          <td style="font-size:11px;">
            {'✅ Ativa' if u['ativo'] else '❌ Inativa'}</td>
        </tr>""" for u in unidades)

        st.markdown(f"""
        <table class="dt">
          <thead><tr><th>Nome</th><th>Tipo</th><th>Status</th></tr></thead>
          <tbody>{rows_u}</tbody>
        </table>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Criar nova unidade ou área**")

        with st.form("form_unid", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1: nome_nu = st.text_input("Nome *")
            with c2: tipo_nu = st.selectbox("Tipo", ["planta","area"])

            if st.form_submit_button("➕ Criar", use_container_width=True):
                if nome_nu:
                    criar_unidade(nome_nu, tipo_nu)
                    st.success(f"✅ **{nome_nu}** criada!")
                    st.rerun()

    # ── Senhas ────────────────────────────────────────────────────────────────
    with tab_senha:
        usuarios = listar_usuarios()
        nomes_us = [u["nome"] for u in usuarios]
        sel_u    = st.selectbox("Selecionar usuário:", nomes_us)
        user_sel = next(u for u in usuarios if u["nome"] == sel_u)

        with st.form("form_senha"):
            nova = st.text_input("Nova senha", type="password")
            conf = st.text_input("Confirmar senha", type="password")

            if st.form_submit_button("🔑 Alterar Senha"):
                if nova != conf:
                    st.error("As senhas não conferem.")
                elif len(nova) < 6:
                    st.error("Mínimo 6 caracteres.")
                else:
                    alterar_senha(user_sel["id"], nova)
                    st.success(f"✅ Senha de **{sel_u}** alterada!")
