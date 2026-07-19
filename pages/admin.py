import streamlit as st
from database import (listar_usuarios, criar_usuario, editar_usuario,
                      alterar_senha, listar_unidades, criar_unidade,
                      get_todas_metas, set_meta, resetar_projetos_teste,
                      listar_projetos, deletar_usuario, PERFIS_LBL)

def render(user, **colors):
    NAVY=colors.get("NAVY","#0B0F2B"); RED=colors.get("RED","#D93B3B")
    if user["perfil"] != "admin":
        st.error("⛔ Acesso restrito a administradores."); return

    st.markdown('<span class="st">Administração</span>', unsafe_allow_html=True)
    tab_users, tab_editar, tab_metas, tab_unid, tab_senha, tab_reset = st.tabs([
        "👥 Usuários","✏️ Editar Usuário","🎯 Metas","🏭 Unidades","🔑 Senhas","🗑️ Reset"])

    with tab_users:
        usuarios = listar_usuarios()
        rows = "".join(f"""<tr>
          <td style="font-size:11px;font-weight:600;">{u['nome']}</td>
          <td style="font-size:11px;">{u['email']}</td>
          <td style="font-size:11px;">{PERFIS_LBL.get(u['perfil'],u['perfil'])}</td>
          <td style="font-size:11px;">{u.get('unidade') or '— Global'}</td>
          <td style="font-size:11px;">{'✅' if u['ativo'] else '❌'}</td>
        </tr>""" for u in usuarios)
        st.markdown(f"""<table class="dt"><thead><tr>
          <th>Nome</th><th>E-mail</th><th>Perfil</th><th>Unidade</th><th>Ativo</th>
        </tr></thead><tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Criar novo usuário**")
        unidades = listar_unidades()
        nomes_u  = ["— Acesso Global"] + [u["nome"] for u in unidades]
        with st.form("form_user", clear_on_submit=True):
            c1,c2=st.columns(2)
            with c1:
                nome_u  = st.text_input("Nome completo *")
                email_u = st.text_input("E-mail *")
                senha_u = st.text_input("Senha inicial *", type="password")
            with c2:
                perfil_u  = st.selectbox("Perfil *", list(PERFIS_LBL.keys()),
                                          format_func=lambda x: PERFIS_LBL[x])
                unidade_u = st.selectbox(
                    "Unidade (Global para admin/cost_control/visualizador global)",
                    nomes_u)
            if st.form_submit_button("➕ Criar Usuário", use_container_width=True):
                if not nome_u or not email_u or not senha_u:
                    st.error("Preencha todos os campos.")
                else:
                    unid = None if unidade_u=="— Acesso Global" else unidade_u
                    try:
                        criar_usuario(nome_u,email_u,senha_u,perfil_u,unid)
                        st.success(f"✅ **{nome_u}** criado!"); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

    with tab_editar:
        usuarios = listar_usuarios()
        unidades = listar_unidades()
        nomes_u2 = ["— Acesso Global"] + [u["nome"] for u in unidades]
        sel_u = st.selectbox("Selecionar:",[u["nome"] for u in usuarios],key="ed_user")
        u_sel = next(u for u in usuarios if u["nome"]==sel_u)
        with st.form("form_ed_user"):
            c1,c2=st.columns(2)
            with c1:
                novo_nome  = st.text_input("Nome", value=u_sel["nome"])
                novo_email = st.text_input("E-mail", value=u_sel["email"])
                ativo      = st.checkbox("Ativo", value=bool(u_sel["ativo"]))
            with c2:
                novo_perfil = st.selectbox("Perfil", list(PERFIS_LBL.keys()),
                    index=list(PERFIS_LBL.keys()).index(u_sel["perfil"])
                    if u_sel["perfil"] in PERFIS_LBL else 0,
                    format_func=lambda x: PERFIS_LBL[x])
                unid_atual = u_sel.get("unidade") or "— Acesso Global"
                idx_unid   = nomes_u2.index(unid_atual) if unid_atual in nomes_u2 else 0
                nova_unid  = st.selectbox("Unidade", nomes_u2, index=idx_unid)
            if st.form_submit_button("💾 Salvar", use_container_width=True):
                editar_usuario(u_sel["id"],{
                    "nome":novo_nome,"email":novo_email.lower(),
                    "perfil":novo_perfil,
                    "unidade":None if nova_unid=="— Acesso Global" else nova_unid,
                    "ativo":int(ativo)})
                st.success(f"✅ **{novo_nome}** atualizado!"); st.rerun()

        st.markdown("---")
        st.markdown("**🗑️ Excluir usuário**")
        admins_ativos = [u for u in usuarios if u["perfil"]=="admin" and u["ativo"]]
        if u_sel["id"] == user["id"]:
            st.info("Você não pode excluir seu próprio usuário logado.")
        elif u_sel["perfil"]=="admin" and u_sel["ativo"] and len(admins_ativos) <= 1:
            st.info("Esse é o único administrador ativo — não pode ser excluído.")
        else:
            conf_del = st.checkbox(
                f"Confirmo que quero excluir **{u_sel['nome']}** permanentemente.",
                key=f"confdel_{u_sel['id']}")
            if st.button("🗑️ Excluir Usuário", disabled=not conf_del,
                        key=f"btndel_{u_sel['id']}"):
                if deletar_usuario(u_sel["id"]):
                    st.success(f"✅ **{u_sel['nome']}** excluído."); st.rerun()
                else:
                    st.error(
                        f"Não foi possível excluir **{u_sel['nome']}**: existem projetos "
                        f"ou lançamentos no histórico vinculados a ele. Desative-o "
                        f"(campo Ativo acima) em vez de excluir.")

    with tab_metas:
        st.markdown("**Definir Meta Anual por Unidade / Área**")
        anos = list(range(2026,2031))
        ano_sel = st.selectbox("Ano:",anos,key="adm_ano")
        metas = get_todas_metas(ano_sel)
        with st.form("form_metas"):
            vals={}
            for m in metas:
                vals[m["nome"]] = st.number_input(
                    f"{m['nome']} ({m['tipo']})",
                    value=float(m["valor"]),step=10000.0,format="%.2f",
                    key=f"meta_{m['nome']}_{ano_sel}")
            if st.form_submit_button("💾 Salvar Metas", use_container_width=True):
                for nome,val in vals.items(): set_meta(nome,ano_sel,val)
                st.success("✅ Metas salvas!")

    with tab_unid:
        unidades = listar_unidades(so_ativas=False)
        rows_u="".join(f"""<tr>
          <td style="font-size:11px;font-weight:600;">{u['nome']}</td>
          <td style="font-size:11px;">{u['tipo']}</td>
          <td style="font-size:11px;">{'✅ Ativa' if u['ativo'] else '❌ Inativa'}</td>
        </tr>""" for u in unidades)
        st.markdown(f"""<table class="dt">
          <thead><tr><th>Nome</th><th>Tipo</th><th>Status</th></tr></thead>
          <tbody>{rows_u}</tbody></table>""", unsafe_allow_html=True)
        st.markdown("---")
        with st.form("form_unid", clear_on_submit=True):
            c1,c2=st.columns(2)
            with c1: nome_nu=st.text_input("Nome *")
            with c2: tipo_nu=st.selectbox("Tipo",["planta","area"])
            if st.form_submit_button("➕ Criar", use_container_width=True):
                if nome_nu: criar_unidade(nome_nu,tipo_nu); st.success(f"✅ **{nome_nu}** criada!"); st.rerun()

    with tab_senha:
        usuarios=listar_usuarios()
        sel_s=st.selectbox("Usuário:",[u["nome"] for u in usuarios],key="adm_senha")
        u_s=next(u for u in usuarios if u["nome"]==sel_s)
        with st.form("form_senha"):
            nova=st.text_input("Nova senha",type="password")
            conf=st.text_input("Confirmar",type="password")
            if st.form_submit_button("🔑 Alterar Senha"):
                if nova!=conf: st.error("Senhas não conferem.")
                elif len(nova)<6: st.error("Mínimo 6 caracteres.")
                else: alterar_senha(u_s["id"],nova); st.success(f"✅ Senha alterada!")

    with tab_reset:
        n_proj = len(listar_projetos(incluir_campeao=True))
        st.markdown(f"**🗑️ Resetar Projetos de Teste**")
        st.warning(
            f"Isso apaga **todos os {n_proj} projeto(s)** cadastrados — junto com seus "
            f"links e lançamentos de real. **Usuários, unidades e metas são mantidos.**\n\n"
            f"Use isso para limpar os dados de teste antes de começar a operação real.")
        confirmar = st.checkbox("Entendo que essa ação é irreversível e quero apagar todos os projetos.")
        if st.button("🗑️ Apagar todos os projetos", disabled=not confirmar,
                     use_container_width=True, type="primary"):
            resetar_projetos_teste()
            st.success("✅ Todos os projetos, links e lançamentos foram apagados. Usuários, unidades e metas foram mantidos.")
            st.rerun()
