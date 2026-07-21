import streamlit as st
from datetime import date
from database import (listar_unidades, criar_projeto, add_link,
                      TIPOS_PROJETO, VA_GGF_OPTS, STATUS_OPTS,
                      EXTRA_DRE_TIPOS)

def pode_editar(user, unidade_nome):
    if user["perfil"] == "admin": return True
    if user["perfil"] in ("facilitador","gestor"):
        return user.get("unidade") == unidade_nome
    return False

def render(user, **colors):
    NAVY=colors.get("NAVY","#0B0F2B"); AMBER=colors.get("AMBER","#E8A838")
    GREEN=colors.get("GREEN","#1AA260"); SILVER=colors.get("SILVER","#8A9BB0")

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

    # ── Identificação (fora do form para a nota DRE reagir na hora) ────────────
    st.markdown("#### Identificação")
    c1,c2,c3 = st.columns(3)
    with c1: tipo = st.selectbox("Tipo *", TIPOS_PROJETO, key="np_tipo")
    with c2: va   = st.selectbox("VA / GGF / Material Auxiliar *", VA_GGF_OPTS, key="np_va")
    with c3: resp = st.text_input("Responsável", key="np_resp")

    # Badge DRE / N/DRE dinâmico — atualiza a cada troca de Tipo
    is_extra = tipo in EXTRA_DRE_TIPOS
    if is_extra:
        st.markdown(
            f'<div style="background:#F3E8FF;border-left:3px solid #9B59B6;'
            f'border-radius:0 6px 6px 0;padding:10px 14px;font-size:11px;color:#6C3483;">'
            f'<b>↷ Extra DRE</b> — <b>{tipo}</b> gera valor operacional mas <b>não impacta o DRE</b>. '
            f'Custos valida o valor, mas não há lançamento de real mensal para este projeto. '
            f'O valor acumula mês a mês no indicador <b>Extra DRE</b> do dashboard.<br>'
            f'<span style="color:#555;">São Extra DRE: Kaizen - Custo Evitado, '
            f'Kaizen - Capital de Giro e Meta Executiva.</span></div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="background:#E6F4EC;border-left:3px solid {GREEN};'
            f'border-radius:0 6px 6px 0;padding:10px 14px;font-size:11px;color:#1A5C2E;">'
            f'<b>✓ Dentro do DRE</b> — <b>{tipo}</b> impacta diretamente o DRE. '
            f'Após aprovação de Custos, o valor é distribuído em 12 meses a partir do '
            f'"Ganho a partir de" e passa a ter acompanhamento de real mensal.<br>'
            f'<span style="color:#555;">São DRE: BSW, Kaizen, Kaizen - Ganho Recorrente, '
            f'Redução de Custo, Você Resolve e Estratégia Comercial.</span></div>',
            unsafe_allow_html=True)

    with st.form("form_novo", clear_on_submit=True):

        nome = st.text_input("Nome do Projeto *")
        desc = st.text_area("Descrição / Objetivo", height=70)

        # ── Datas e Valores ───────────────────────────────────────────────────
        st.markdown("#### Datas e Valores")
        c1,c2,c3 = st.columns(3)
        with c1: inicio  = st.date_input("Data de Início do Projeto", format="DD/MM/YYYY")
        with c2: termino = st.date_input("Data de Fim do Projeto", format="DD/MM/YYYY")
        with c3: mpr     = st.date_input(
            "Ganho a partir de... *", format="DD/MM/YYYY",
            help="Mês em que o projeto começa a gerar ganho financeiro. "
                 "A partir daqui contam 12 meses de vida útil. "
                 "Obrigatório também para projetos Extra DRE.")

        previsto = st.number_input(
            "Valor Previsto (R$) *",
            min_value=0.0, step=1000.0, format="%.2f",
            help="Valor estimado pela unidade. Distribuído em 12 meses a partir do 1º retorno. "
                 + ("Para Extra DRE, acumula no indicador Extra DRE mês a mês." if is_extra else
                    "Após validação de Custos, o valor calculado substituirá este nas projeções."))

        # ── Links e Evidências ────────────────────────────────────────────────
        st.markdown("#### Links e Evidências (SharePoint / OneDrive)")
        st.caption("Cole os links completos (https://...). Você pode adicionar mais depois.")
        c1,c2 = st.columns([2,4])
        with c1: link1_tit = st.text_input("Nome 1", placeholder="ex: A3 do Projeto")
        with c2: link1_url = st.text_input("URL 1", placeholder="https://...")
        c1,c2 = st.columns([2,4])
        with c1: link2_tit = st.text_input("Nome 2", placeholder="ex: Memória de Cálculo")
        with c2: link2_url = st.text_input("URL 2", placeholder="https://...")
        c1,c2 = st.columns([2,4])
        with c1: link3_tit = st.text_input("Nome 3", placeholder="ex: Planilha de Apoio")
        with c2: link3_url = st.text_input("URL 3", placeholder="https://...")

        # ── Acompanhamento ────────────────────────────────────────────────────
        st.markdown("#### Acompanhamento")
        status = st.selectbox("Status", STATUS_OPTS)
        st.caption("Os campos abaixo são opcionais — preenchidos nos acompanhamentos semanais.")
        c1,c2,c3 = st.columns(3)
        with c1: ativ     = st.text_input("Atual Atribuição", placeholder="Atividade em andamento...")
        with c2: resp_ativ = st.text_input("Responsável da Atribuição", placeholder="Nome...")
        with c3: dt_ativ   = st.text_input("Data Final da Atribuição", placeholder="ex: 08/2026")

        # ── Checklist ─────────────────────────────────────────────────────────
        st.markdown("#### Checklist")
        st.caption("Quando os 3 estiverem marcados, o projeto vai para validação de Custos.")
        c1,c2,c3 = st.columns(3)
        with c1: ck_a3  = st.checkbox("A3 e Plano de Projeto desenvolvido")
        with c2: ck_mem = st.checkbox("Memória de Cálculo desenvolvida")
        with c3: ck_for = st.checkbox("Formalizado com Custos")
        if ck_a3 and ck_mem and ck_for:
            st.success("✅ Checklist completo — será encaminhado para validação de Custos.")

        # ── Observações ───────────────────────────────────────────────────────
        st.markdown("#### Observações")
        obs = st.text_area("", height=80, label_visibility="collapsed",
                            placeholder="Observações gerais sobre o projeto...")

        st.markdown("---")
        salvar = st.form_submit_button("💾 Cadastrar Projeto",
                                       use_container_width=True, type="primary")

    if salvar:
        if not nome:
            st.error("Preencha o Nome do Projeto.")
        elif previsto <= 0:
            st.error("Preencha o Valor Previsto.")
        else:
            pid = criar_projeto(unidade_sel, {
                "nome": nome, "tipo": tipo, "va_ggf": va,
                "responsavel": resp, "descricao": desc, "obs": obs,
                "inicio": str(inicio), "termino": str(termino),
                "mes_primeiro_retorno": str(mpr),
                "previsto_unidade": previsto, "status": status,
                "atividade_atual": ativ,
                "data_conclusao_ativ": dt_ativ,
                "onde_parado": resp_ativ,
                "check_a3": ck_a3, "check_memoria": ck_mem,
                "check_formalizado": ck_for,
            }, user["id"])
            for tit, url in [(link1_tit,link1_url),(link2_tit,link2_url),(link3_tit,link3_url)]:
                if tit and url:
                    add_link(pid, tit, url)
            st.success(f"✅ Projeto **{nome}** cadastrado! ID #{pid}")
            st.rerun()
