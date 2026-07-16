import streamlit as st
from datetime import datetime, date
from database import (listar_unidades, listar_projetos, lancar_real,
                      get_lancamentos, get_previsto_curva, get_links,
                      atualizar_projeto, MESES_PT)

def clean_html(html):
    lines = [line.strip() for line in html.strip().split("\n")]
    return "".join(lines)

def html_card(html):
    st.markdown(clean_html(html), unsafe_allow_html=True)

def render(user, **colors):
    NAVY=colors.get("NAVY","#1C2B4A"); GREEN=colors.get("GREEN","#1A7A3A")
    AMBER=colors.get("AMBER","#E8A838"); RED=colors.get("RED","#C8202E")
    TEAL=colors.get("TEAL","#20C997"); SILVER=colors.get("SILVER","#8A9BB0")

    ano_atual = datetime.now().year
    is_cc = user["perfil"] in ("admin","cost_control","gestor")

    tab_fila, tab_real = st.tabs(["📋 Fila de Aprovação", "💰 Controle de Custos"])

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    # ── Filtro de unidades por checkbox (compartilhado) ───────────────────────
    def filtro_unidades(key):
        st.markdown("**Filtrar por unidade/área:**")
        cols = st.columns(4)
        sel = []
        for i, u in enumerate(nomes_u):
            with cols[i % 4]:
                if st.checkbox(u, value=True, key=f"{key}_{u}"):
                    sel.append(u)
        return sel

    # ── Fila de Aprovação ─────────────────────────────────────────────────────
    with tab_fila:
        st.markdown('<span class="st">Fila de Aprovação — Cost Control</span>',
                    unsafe_allow_html=True)
        st.caption("Projetos com checklist completo aguardando validação de Custos.")

        if not is_cc:
            st.info("Acesso restrito ao time de Cost Control.")
        else:
            unis_fila = filtro_unidades("fila")

            todos = listar_projetos()
            # Fila: checklist completo + sem aprovação ainda
            fila = [p for p in todos
                    if p["check_a3"] and p["check_memoria"] and p["check_formalizado"]
                    and p.get("validador_ok","Pendente") == "Pendente"
                    and p["unidade_nome"] in unis_fila]

            st.markdown(f"**{len(fila)} projeto(s) aguardando aprovação**")

            if not fila:
                st.success("✅ Nenhum projeto aguardando aprovação.")
            else:
                for p in fila:
                    links = get_links(p["id"])
                    link_html = " ".join(
                        f'<a href="{lk["url"]}" target="_blank" style="'
                        f'display:inline-block;background:#EEF0F3;color:{NAVY};'
                        f'font-size:11px;padding:3px 10px;border-radius:8px;'
                        f'text-decoration:none;margin-right:4px;">🔗 {lk["titulo"]}</a>'
                        for lk in links) if links else \
                        f'<span style="color:#ccc;font-size:11px;">Sem links cadastrados</span>'

                    html_card(f"""
<div style="border-left:4px solid {NAVY};background:white;border-radius:0 8px 8px 0;
     padding:14px 18px;margin-bottom:6px;
     box-shadow:0 1px 4px rgba(28,43,74,.08);">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div style="flex:1;">
      <div style="font-size:10px;color:{SILVER};">{p['unidade_nome']} · {p['tipo']} · {p.get('va_ggf','—')}</div>
      <div style="font-size:13px;font-weight:700;color:{NAVY};margin-top:2px;">#{p['id']} — {p['nome']}</div>
      <div style="font-size:11px;color:#555;margin-top:4px;">{p.get('descricao','') or '—'}</div>
      <div style="margin-top:8px;">{link_html}</div>
    </div>
    <div style="text-align:right;flex-shrink:0;margin-left:20px;">
      <div style="font-size:9px;color:{SILVER};text-transform:uppercase;letter-spacing:.4px;">Previsto Unidade</div>
      <div style="font-size:18px;font-weight:700;color:{AMBER};">R$ {p['previsto_unidade']:,.0f}</div>
    </div>
  </div>
</div>""")

                    with st.expander(f"⚖️ Aprovar / Reprovar #{p['id']}",
                                     expanded=False):
                        with st.form(f"fap_{p['id']}"):
                            decisao = st.radio("Decisão:",
                                               ["✅ Aprovar","❌ Reprovar"],
                                               horizontal=True,
                                               key=f"dec_{p['id']}")
                            valor_c = 0.0
                            if decisao == "✅ Aprovar":
                                valor_c = st.number_input(
                                    "Valor Calculado por Custos (R$) *",
                                    min_value=0.0, step=500.0, format="%.2f",
                                    key=f"vc_{p['id']}",
                                    help="Será distribuído em 12 meses a partir "
                                         "do 1º retorno definido pela unidade.")
                                obs_ap = st.text_area("Observação (opcional)",
                                                       height=60, key=f"oa_{p['id']}")
                            else:
                                obs_ap = st.text_area(
                                    "Motivo da reprovação (opcional)",
                                    height=60, key=f"or_{p['id']}")

                            confirmar = st.form_submit_button(
                                "Confirmar", use_container_width=True)

                        if confirmar:
                            if decisao == "✅ Aprovar":
                                if valor_c <= 0:
                                    st.error("Informe o Valor Calculado por Custos.")
                                else:
                                    atualizar_projeto(p["id"], {
                                        "validador_ok": "OK",
                                        "previsto_custos": valor_c,
                                        "saving_validado": valor_c,
                                        "obs": (p.get("obs","") or "") + \
                                               (f"\n[Custos] {obs_ap}" if obs_ap else ""),
                                    }, user["id"])
                                    st.success(f"✅ Projeto #{p['id']} aprovado!")
                                    st.rerun()
                            else:
                                # Reprova: remove tick formalizado
                                atualizar_projeto(p["id"], {
                                    "validador_ok": "NOK",
                                    "check_formalizado": 0,
                                    "obs": (p.get("obs","") or "") + \
                                           (f"\n[Reprovado] {obs_ap}" if obs_ap else ""),
                                }, user["id"])
                                st.warning(f"⚠️ Projeto #{p['id']} reprovado. "
                                           f"Retorna para a unidade corrigir.")
                                st.rerun()

    # ── Controle de Custos ────────────────────────────────────────────────────
    with tab_real:
        st.markdown('<span class="st">Controle de Custos — Lançamento Real Mensal</span>',
                    unsafe_allow_html=True)
        st.info("📌 Lance o retorno do **mês anterior** na primeira semana do mês atual.")

        if not is_cc:
            st.info("Acesso restrito ao time de Cost Control.")
            return

        unis_real = filtro_unidades("real")

        c1,c2 = st.columns(2)
        with c1:
            anos = list(range(2025,2030))
            ano_sel = st.selectbox("Ano:", anos,
                index=anos.index(ano_atual) if ano_atual in anos else 0,
                key="cc_ano")
        with c2:
            mes_sel = st.selectbox("Mês de referência:", range(1,13),
                format_func=lambda m: MESES_PT[m-1], key="cc_mes")

        # Projetos aprovados com retorno previsto neste mês
        todos_ap = [p for p in listar_projetos()
                    if p.get("validador_ok")=="OK"
                    and p["unidade_nome"] in unis_real]

        proj_mes = []
        for p in todos_ap:
            curva = get_previsto_curva(p["id"])
            if (ano_sel, mes_sel) in curva:
                proj_mes.append((p, curva[(ano_sel, mes_sel)]))

        if not proj_mes:
            st.info(f"Nenhum projeto com retorno previsto em "
                    f"{MESES_PT[mes_sel-1]}/{ano_sel} "
                    f"nas unidades selecionadas.")
        else:
            lancs_exist = {
                l["projeto_id"]: l
                for l in get_lancamentos(ano=ano_sel)
                if l["mes"] == mes_sel
            }

            # Separa pendentes e lançados
            pendentes = [(p,frac) for p,frac in proj_mes
                         if p["id"] not in lancs_exist]
            lancados  = [(p,frac) for p,frac in proj_mes
                         if p["id"] in lancs_exist]

            st.markdown(f"**{len(pendentes)} pendente(s)** · {len(lancados)} já lançado(s) "
                        f"em {MESES_PT[mes_sel-1]}/{ano_sel}")

            if pendentes:
                st.markdown("---")
                st.markdown(f"**Lançar para {MESES_PT[mes_sel-1]}/{ano_sel}:**")
                with st.form("form_real"):
                    valores = {}; obs_map = {}
                    for p, frac in pendentes:
                        c1,c2,c3,c4 = st.columns([3,2,2,3])
                        with c1:
                            st.markdown(f"**#{p['id']} — {p['nome']}**")
                            st.caption(p["unidade_nome"])
                        with c2:
                            st.markdown("**Fração Prevista**")
                            st.markdown(f"R$ {frac:,.0f}")
                        with c3:
                            valores[p["id"]] = st.number_input(
                                "Real (R$)", value=0.0,
                                step=100.0, format="%.2f",
                                key=f"rv_{p['id']}",
                                label_visibility="collapsed")
                        with c4:
                            obs_map[p["id"]] = st.text_input(
                                "Obs", key=f"ro_{p['id']}",
                                label_visibility="collapsed",
                                placeholder="Observação...")
                        st.divider()

                    if st.form_submit_button(
                        f"💾 Salvar lançamentos de {MESES_PT[mes_sel-1]}/{ano_sel}",
                        use_container_width=True):
                        for pid, val in valores.items():
                            if val >= 0:
                                lancar_real(pid, ano_sel, mes_sel, val,
                                           obs_map.get(pid,""), user["id"])
                        st.success("✅ Lançamentos salvos!")
                        st.rerun()

            if lancados:
                st.markdown("---")
                st.markdown(f"✅ **Já lançados em {MESES_PT[mes_sel-1]}/{ano_sel}:**")
                for p, frac in lancados:
                    lc = lancs_exist[p["id"]]
                    real_v = lc["valor_real"]
                    diff   = real_v - frac
                    diff_c = GREEN if diff >= 0 else RED
                    html_card(f"""
<div style="display:flex;gap:16px;align-items:center;padding:8px 12px;
     background:#F9F9F9;border-radius:8px;margin-bottom:4px;">
  <div style="flex:1;font-size:11px;">
    <b>#{p['id']} — {p['nome']}</b>
    <span style="color:{SILVER};margin-left:8px;">{p['unidade_nome']}</span>
  </div>
  <div style="font-size:11px;color:{SILVER};">Previsto: R$ {frac:,.0f}</div>
  <div style="font-size:12px;font-weight:700;color:{GREEN};">Real: R$ {real_v:,.0f}</div>
  <div style="font-size:11px;color:{diff_c};">
    {'▲' if diff>=0 else '▼'} R$ {abs(diff):,.0f}</div>
</div>""")
