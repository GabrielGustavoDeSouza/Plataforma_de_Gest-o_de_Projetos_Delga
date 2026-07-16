import streamlit as st
from datetime import date
from database import (listar_unidades, criar_projeto,
                      add_link, TIPOS_PROJETO, VA_GGF_OPTS, STATUS_OPTS)

def pode_editar(user, unidade_nome):
    if user["perfil"] == "admin": return True
    if user["perfil"] in ("facilitador","gestor"):
        return user.get("unidade") == unidade_nome
    return False

def render(user, **colors):
    NAVY=colors.get("NAVY","#1C2B4A"); AMBER=colors.get("AMBER","#E8A838")
    SILVER=colors.get("SILVER","#8A9BB0"); RED=colors.get("RED","#C8202E")

    st.markdown('<span class="st">Novo Projeto</span>', unsafe_allow_html=True)

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    if user["perfil"] == "admin":
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np_uni")
    elif user["perfil"] in ("facilitador","gestor","cost_control"):
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np_uni")
        if user.get("unidade") and unidade_sel != user.get("unidade"):
            st.info(f"👁️ Você cria projetos apenas em **{user.get('unidade')}**")
    else:
        unidade_sel = user.get("unidade","")
        if unidade_sel not in nomes_u:
            st.warning("Unidade não configurada."); return

    pode = pode_editar(user, unidade_sel)
    if not pode:
        st.warning(f"⛔ Você só pode criar projetos em **{user.get('unidade','')}**.")
        return

    with st.form("form_novo", clear_on_submit=True):

        # ── Identificação ─────────────────────────────────────────────────────
        st.markdown("#### Identificação")
        c1,c2,c3 = st.columns(3)
        with c1: tipo = st.selectbox("Tipo *", TIPOS_PROJETO)
        with c2: va   = st.selectbox("VA / GGF / Material Auxiliar *", VA_GGF_OPTS)
        with c3: resp = st.text_input("Responsável")

        nome = st.text_input("Nome do Projeto *")
        desc = st.text_area("Descrição", height=80)

        # ── Datas e Valores ───────────────────────────────────────────────────
        st.markdown("#### Datas e Valores")
        c1,c2,c3 = st.columns(3)
        with c1: inicio  = st.date_input("Data de Início do Projeto")
        with c2: termino = st.date_input("Data de Fim do Projeto")
        with c3: mpr     = st.date_input(
            "Ganho a partir de... *",
            help="Mês em que o projeto começa a gerar ganho financeiro. "
                 "A partir daqui contam 12 meses de vida útil.")

        previsto = st.number_input(
            "Valor Previsto (R$) *",
            min_value=0.0, step=1000.0, format="%.2f",
            help="Valor estimado pela unidade. "
                 "Será distribuído igualmente nos 12 meses de vida útil.")

        # ── Links e Evidências ────────────────────────────────────────────────
        st.markdown("#### Links e Evidências (SharePoint / OneDrive)")
        c1,c2 = st.columns([2,4])
        with c1: link1_tit = st.text_input("Nome do link 1",
                                            placeholder="ex: A3 do Projeto")
        with c2: link1_url = st.text_input("URL 1", placeholder="https://...")
        c1,c2 = st.columns([2,4])
        with c1: link2_tit = st.text_input("Nome do link 2",
                                            placeholder="ex: Memória de Cálculo")
        with c2: link2_url = st.text_input("URL 2", placeholder="https://...")
        c1,c2 = st.columns([2,4])
        with c1: link3_tit = st.text_input("Nome do link 3",
                                            placeholder="ex: Planilha de Apoio")
        with c2: link3_url = st.text_input("URL 3", placeholder="https://...")

        # ── Acompanhamento ────────────────────────────────────────────────────
        st.markdown("#### Acompanhamento")
        status = st.selectbox("Status", STATUS_OPTS)

        st.caption("Os campos abaixo são opcionais e podem ser preenchidos "
                   "durante os acompanhamentos semanais.")
        c1,c2,c3 = st.columns(3)
        with c1: ativ     = st.text_input("Atual Atribuição",
                                           placeholder="Atividade em andamento...")
        with c2: resp_ativ= st.text_input("Responsável da Atual Atribuição",
                                           placeholder="Nome do responsável...")
        with c3: dt_ativ  = st.text_input("Data Final desta Atribuição",
                                           placeholder="ex: 07/2026")

        st.markdown("**Checklist** — quando os 3 estiverem marcados "
                    "o projeto vai para validação de Custos")
        c1,c2,c3 = st.columns(3)
        with c1: ck_a3  = st.checkbox("✅ A3 e Plano de Projeto desenvolvido")
        with c2: ck_mem = st.checkbox("✅ Memória de Cálculo desenvolvida")
        with c3: ck_for = st.checkbox("✅ Formalizado com Custos")

        if ck_a3 and ck_mem and ck_for:
            st.success("✅ Checklist completo — projeto será encaminhado para Custos.")

        # ── Observações ───────────────────────────────────────────────────────
        st.markdown("#### Observações")
        obs = st.text_area("Observações gerais", height=80,
                            label_visibility="collapsed")

        st.markdown("---")
        salvar = st.form_submit_button("💾 Cadastrar Projeto",
                                       use_container_width=True,
                                       type="primary")

    if salvar:
        if not nome:
            st.error("Preencha o Nome do Projeto.")
        elif previsto <= 0:
            st.error("Preencha o Valor Previsto.")
        else:
            # resp_ativ vai para o campo onde_parado por ora (campo genérico)
            pid = criar_projeto(unidade_sel, {
                "nome": nome, "tipo": tipo, "va_ggf": va,
                "responsavel": resp, "descricao": desc, "obs": obs,
                "inicio": str(inicio), "termino": str(termino),
                "mes_primeiro_retorno": str(mpr),
                "previsto_unidade": previsto,
                "status": status,
                "atividade_atual": ativ,
                "data_conclusao_ativ": dt_ativ,
                "onde_parado": resp_ativ,
                "check_a3": ck_a3,
                "check_memoria": ck_mem,
                "check_formalizado": ck_for,
            }, user["id"])
            for tit, url in [(link1_tit,link1_url),
                             (link2_tit,link2_url),
                             (link3_tit,link3_url)]:
                if tit and url:
                    add_link(pid, tit, url)
            st.success(f"✅ Projeto **{nome}** cadastrado! ID #{pid}")
            st.rerun()
