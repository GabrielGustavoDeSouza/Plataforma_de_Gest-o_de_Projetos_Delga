"""pages/novo_projeto.py — Cadastro e edição de projetos"""
import streamlit as st
from database import listar_unidades, listar_projetos, criar_projeto, atualizar_projeto, deletar_projeto, TIPOS_PROJETO, STATUS_PROJETO

def render(user, NAVY, RED, GREEN, AMBER, LIGHT):
    st.markdown(f'<span class="st">Cadastro de Projetos</span>', unsafe_allow_html=True)

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    # Filtrar unidade conforme perfil
    if user.get("perfil") in ("admin","gestor") and not user.get("unidade"):
        unidade_sel = st.selectbox("Unidade:", nomes_u)
    else:
        unidade_sel = user.get("unidade")
        if not unidade_sel:
            st.warning("Sem unidade vinculada.")
            return
        st.markdown(f"**Unidade:** {unidade_sel}")

    tab_novo, tab_editar = st.tabs(["➕ Novo Projeto", "✏️ Editar / Excluir"])

    # ── Novo Projeto ──────────────────────────────────────────────────────────
    with tab_novo:
        with st.form("form_novo"):
            c1, c2 = st.columns(2)
            with c1:
                nome       = st.text_input("Nome do Projeto *")
                tipo       = st.selectbox("Tipo *", TIPOS_PROJETO)
                responsavel= st.text_input("Responsável")
            with c2:
                previsto   = st.number_input("Previsto (R$) *", min_value=0.0, step=1000.0, format="%.2f")
                inicio     = st.date_input("Início")
                termino    = st.date_input("Término")

            descricao = st.text_area("Descrição / Objetivo", height=80)
            salvar = st.form_submit_button("💾 Salvar Projeto", use_container_width=True)

        if salvar:
            if not nome or previsto <= 0:
                st.error("Preencha Nome e Valor Previsto.")
            else:
                criar_projeto(
                    unidade_nome=unidade_sel, nome=nome, tipo=tipo,
                    responsavel=responsavel, descricao=descricao,
                    previsto_rs=previsto,
                    inicio=str(inicio), termino=str(termino),
                    user_id=user["id"]
                )
                st.success(f"✅ Projeto **{nome}** cadastrado com sucesso!")

    # ── Editar / Excluir ──────────────────────────────────────────────────────
    with tab_editar:
        projetos = listar_projetos(unidade_sel)
        if not projetos:
            st.info("Nenhum projeto cadastrado ainda.")
            return

        nomes_p = [f"[{p['tipo'][:8]}] {p['nome']}" for p in projetos]
        idx = st.selectbox("Selecionar projeto:", range(len(nomes_p)),
                           format_func=lambda i: nomes_p[i])
        p = projetos[idx]

        with st.form("form_editar"):
            c1, c2 = st.columns(2)
            with c1:
                nome_e    = st.text_input("Nome", value=p["nome"])
                tipo_e    = st.selectbox("Tipo", TIPOS_PROJETO,
                                         index=TIPOS_PROJETO.index(p["tipo"]) if p["tipo"] in TIPOS_PROJETO else 0)
                resp_e    = st.text_input("Responsável", value=p.get("responsavel",""))
                status_e  = st.selectbox("Status", STATUS_PROJETO,
                                          index=STATUS_PROJETO.index(p["status"]) if p["status"] in STATUS_PROJETO else 0)
            with c2:
                prev_e    = st.number_input("Previsto (R$)", value=float(p["previsto_rs"]), step=1000.0, format="%.2f")
                saving_e  = st.number_input("Saving Validado (R$)", value=float(p["saving_valid"]), step=1000.0, format="%.2f")
                ok_e      = st.selectbox("Validador Custos", ["Pendente","OK","NOK"], index=["Pendente","OK","NOK"].index(p.get("validado_ok","Pendente")))
                onde_e    = st.text_input("Onde Parado", value=p.get("onde_parado","") or "")
                data_e    = st.text_input("Previsão Liberação", value=p.get("data_lib","") or "")

            desc_e = st.text_area("Descrição", value=p.get("descricao","") or "", height=60)
            col_s, col_d = st.columns([3,1])
            with col_s: salvar_e  = st.form_submit_button("💾 Salvar Alterações", use_container_width=True)
            with col_d: excluir_e = st.form_submit_button("🗑️ Excluir", use_container_width=True, type="secondary")

        if salvar_e:
            atualizar_projeto(p["id"], {
                "nome": nome_e, "tipo": tipo_e, "responsavel": resp_e,
                "status": status_e, "previsto_rs": prev_e, "saving_valid": saving_e,
                "validado_ok": ok_e, "onde_parado": onde_e, "data_lib": data_e,
                "descricao": desc_e,
            })
            st.success("✅ Projeto atualizado!")
            st.rerun()

        if excluir_e:
            deletar_projeto(p["id"])
            st.success("🗑️ Projeto excluído.")
            st.rerun()
