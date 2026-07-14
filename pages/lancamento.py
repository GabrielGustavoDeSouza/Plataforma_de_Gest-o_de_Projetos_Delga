"""pages/lancamento.py — Fila Cost Control + Lançamento Real"""
import streamlit as st
from datetime import datetime, date
from database import (listar_unidades, listar_projetos, lancar_real,
                      get_lancamentos, alertas_pendentes, get_previsto_curva,
                      atualizar_projeto, MESES_PT)

def render(user, **colors):
    NAVY=colors.get("NAVY","#1C2B4A"); GREEN=colors.get("GREEN","#1A7A3A")
    AMBER=colors.get("AMBER","#E8A838"); RED=colors.get("RED","#C8202E")
    SILVER=colors.get("SILVER","#8A9BB0")

    ano_atual = datetime.now().year

    # Cost Control vê todas as unidades; operador só a sua
    is_cc = user["perfil"] in ("admin","cost_control","gestor")

    if is_cc:
        tab_fila, tab_lanc, tab_alertas = st.tabs([
            "📋 Fila Cost Control","💰 Lançar Real Mensal","⚠️ Alertas"
        ])
    else:
        tab_lanc, tab_alertas = st.tabs(["💰 Lançar Real Mensal","⚠️ Alertas"])
        tab_fila = None

    # ── Fila Cost Control ─────────────────────────────────────────────────────
    if tab_fila:
        with tab_fila:
            st.markdown('<span class="st">Fila de Validação — Cost Control</span>', unsafe_allow_html=True)
            st.markdown("Projetos aguardando validação de custos. Após validar, o projeto vai ao final da fila.")

            todos = listar_projetos()  # todos, ordenados por check_formalizado ASC
            pendentes = [p for p in todos if not p["check_formalizado"]]
            validados = [p for p in todos if p["check_formalizado"]]

            st.markdown(f"**{len(pendentes)} aguardando validação** · {len(validados)} validados")

            for p in pendentes:
                with st.expander(f"#{p['id']} [{p['tipo'][:8]}] {p['nome']} — {p['unidade_nome']}", expanded=False):
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        ck_a3  = st.checkbox("A3 e Plano desenvolvido",  value=bool(p["check_a3"]),  key=f"a3_{p['id']}")
                        ck_mem = st.checkbox("Memória de Cálculo",        value=bool(p["check_memoria"]), key=f"mem_{p['id']}")
                        ck_for = st.checkbox("Formalizado com Custos",    value=bool(p["check_formalizado"]), key=f"for_{p['id']}")
                    with c2:
                        val_ok = st.selectbox("Validador", ["Pendente","OK","NOK"],
                            index=["Pendente","OK","NOK"].index(p.get("validador_ok","Pendente")),
                            key=f"vok_{p['id']}")
                        saving = st.number_input("Saving Validado (R$)",
                            value=float(p["saving_validado"]), step=500.0, key=f"sav_{p['id']}")
                    with c3:
                        prev_c = st.number_input("Valor Calculado Custos (R$)",
                            value=float(p["previsto_custos"]),step=500.0,key=f"pc_{p['id']}",
                            help="Substitui o previsto da unidade na distribuição dos 12 meses")

                    st.markdown(f"Previsto Unidade: **R$ {p['previsto_unidade']:,.0f}**")

                    if st.button(f"💾 Salvar validação #{p['id']}", key=f"sv_{p['id']}"):
                        atualizar_projeto(p["id"], {
                            "check_a3": int(ck_a3), "check_memoria": int(ck_mem),
                            "check_formalizado": int(ck_for),
                            "validador_ok": val_ok, "saving_validado": saving,
                            "previsto_custos": prev_c,
                        }, user["id"])
                        st.success("✅ Salvo! Projeto vai ao final da fila."); st.rerun()

    # ── Lançamento Real ───────────────────────────────────────────────────────
    with tab_lanc:
        st.markdown('<span class="st">Lançar Retorno Real Mensal</span>', unsafe_allow_html=True)
        st.info("📌 Lançar o retorno do **mês anterior** na primeira semana do mês atual.")

        unidades = listar_unidades()
        nomes_u  = [u["nome"] for u in unidades]

        if is_cc:
            unidade_sel = st.selectbox("Unidade:", nomes_u, key="lc_uni")
        else:
            unidade_sel = user.get("unidade","")

        c1,c2 = st.columns(2)
        with c1: ano_sel = st.selectbox("Ano:", list(range(2025, 2030)), index=list(range(2025,2030)).index(ano_atual) if ano_atual in range(2025,2030) else 0)
        with c2: mes_sel = st.selectbox("Mês de referência:", range(1,13), format_func=lambda m: MESES_PT[m-1])

        projetos = listar_projetos(unidade_sel)
        # Só mostrar projetos que já deveriam ter retorno neste mês
        proj_ativos = []
        for p in projetos:
            curva = get_previsto_curva(p["id"])
            if (ano_sel, mes_sel) in curva:
                proj_ativos.append(p)

        if not proj_ativos:
            st.info(f"Nenhum projeto com retorno previsto em {MESES_PT[mes_sel-1]}/{ano_sel}.")
        else:
            lancs_exist = {l["projeto_id"]: l for l in get_lancamentos(unidade_nome=unidade_sel, ano=ano_sel) if l["mes"]==mes_sel}

            with st.form("form_lanc"):
                valores = {}; obs_map = {}
                for p in proj_ativos:
                    curva  = get_previsto_curva(p["id"])
                    prev_m = curva.get((ano_sel, mes_sel), 0)
                    ant    = lancs_exist.get(p["id"])
                    val_ant= float(ant["valor_real"]) if ant else 0.0
                    obs_ant= ant["observacao"] if ant else ""

                    ja_lanc = p["id"] in lancs_exist
                    badge   = "✅" if ja_lanc else "⚠️"
                    st.markdown(f"**{badge} #{p['id']} — {p['nome']}** · Previsto mês: R$ {prev_m:,.0f}")
                    c1,c2 = st.columns([2,4])
                    with c1: valores[p["id"]]  = st.number_input("Real (R$)", value=val_ant, step=100.0, format="%.2f", key=f"rv_{p['id']}", label_visibility="collapsed")
                    with c2: obs_map[p["id"]]  = st.text_input("Obs", value=obs_ant, key=f"ro_{p['id']}", label_visibility="collapsed", placeholder="Observação")
                    st.markdown("---")

                if st.form_submit_button(f"💾 Salvar lançamentos de {MESES_PT[mes_sel-1]}/{ano_sel}", use_container_width=True):
                    for pid,val in valores.items():
                        if val >= 0:
                            lancar_real(pid, ano_sel, mes_sel, val, obs_map.get(pid,""), user["id"])
                    st.success("✅ Lançamentos salvos!"); st.rerun()

    # ── Alertas ───────────────────────────────────────────────────────────────
    with tab_alertas:
        st.markdown('<span class="st">⚠️ Meses com Retorno Esperado Sem Lançamento</span>', unsafe_allow_html=True)

        unidade_alerta = None if is_cc else user.get("unidade")
        alerts = alertas_pendentes(unidade_alerta)

        if not alerts:
            st.success("✅ Todos os lançamentos estão em dia!")
        else:
            st.warning(f"{len(alerts)} lançamento(s) pendente(s)")
            rows = "".join(f"""<tr>
              <td style="font-size:11px;">{a['unidade']}</td>
              <td style="font-size:11px;"><b>{a['projeto']}</b></td>
              <td style="font-size:11px;text-align:center;">{MESES_PT[a['mes']-1]}/{a['ano']}</td>
            </tr>""" for a in alerts)
            st.markdown(f"""
            <table class="dt">
              <thead><tr><th>Unidade</th><th>Projeto</th><th>Mês Pendente</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>""", unsafe_allow_html=True)
