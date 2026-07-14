"""pages/lancamento.py — Lançamento de Real Mensal"""
import streamlit as st
from database import listar_unidades, listar_projetos, lancar_real, get_lancamentos

MESES = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
         "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]

def render(user, ano, NAVY, GREEN, AMBER, LIGHT):
    st.markdown(f'<span class="st">Lançamento de Retorno Real Mensal — {ano}</span>', unsafe_allow_html=True)

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    if user.get("perfil") in ("admin","gestor") and not user.get("unidade"):
        unidade_sel = st.selectbox("Unidade:", nomes_u)
    else:
        unidade_sel = user.get("unidade")
        if not unidade_sel:
            st.warning("Sem unidade vinculada.")
            return

    projetos = listar_projetos(unidade_sel)
    if not projetos:
        st.info("Nenhum projeto cadastrado nesta unidade.")
        return

    mes_sel = st.selectbox("Mês de referência:", range(1,13),
                           format_func=lambda m: MESES[m-1])

    # Carrega lançamentos existentes
    lanc_existentes = {l["projeto_id"]: l for l in get_lancamentos(unidade_sel, ano) if l["mes"]==mes_sel}

    st.markdown(f"**Lançando para: {MESES[mes_sel-1]} / {ano}**")
    st.markdown("---")

    with st.form("form_lancamento"):
        valores = {}
        observs = {}
        for p in projetos:
            lanc_ant = lanc_existentes.get(p["id"])
            val_ant  = float(lanc_ant["valor_real"]) if lanc_ant else 0.0
            obs_ant  = lanc_ant["observacao"] if lanc_ant else ""

            st.markdown(f"**[{p['tipo'][:10]}] {p['nome']}** — Previsto: R$ {p['previsto_rs']:,.0f}")
            c1, c2 = st.columns([2,3])
            with c1:
                valores[p["id"]] = st.number_input(
                    f"Valor Real (R$)", value=val_ant, step=100.0, format="%.2f",
                    key=f"val_{p['id']}", label_visibility="collapsed"
                )
            with c2:
                observs[p["id"]] = st.text_input(
                    "Observação", value=obs_ant, key=f"obs_{p['id']}",
                    label_visibility="collapsed", placeholder="Observação (opcional)"
                )
            st.markdown("---")

        salvar = st.form_submit_button("💾 Salvar Lançamentos", use_container_width=True)

    if salvar:
        for proj_id, valor in valores.items():
            if valor >= 0:
                lancar_real(proj_id, ano, mes_sel, valor, observs.get(proj_id,""), user["id"])
        st.success(f"✅ Lançamentos de {MESES[mes_sel-1]}/{ano} salvos com sucesso!")
        st.rerun()
