import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from database import listar_unidades, kpis_unidade, alertas_pendentes, verificar_campeoes, MESES_PT

def fmt_mi(v): return f"R$ {v/1e6:.2f} Mi" if abs(v)>=1e6 else f"R$ {v/1e3:.1f} k"

def render(user, **colors):
    NAVY=colors.get("NAVY","#1C2B4A"); GREEN=colors.get("GREEN","#1A7A3A")
    AMBER=colors.get("AMBER","#E8A838"); RED=colors.get("RED","#C8202E")
    TEAL=colors.get("TEAL","#20C997"); SILVER=colors.get("SILVER","#8A9BB0")

    verificar_campeoes()

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    if user["perfil"] in ("admin","gestor","cost_control") and not user.get("unidade"):
        sel = st.selectbox("Unidade:", nomes_u, key="ud_sel")
    else:
        sel = user.get("unidade","")
        if sel not in nomes_u:
            st.warning("Unidade não configurada."); return
        st.markdown(f"**Unidade:** {sel}")

    # Botões de ano
    anos = list(range(2025, 2030))
    if "ano_uni" not in st.session_state:
        st.session_state["ano_uni"] = datetime.now().year
    ano_sel = st.session_state["ano_uni"]

    cols = st.columns(len(anos))
    for i, a in enumerate(anos):
        with cols[i]:
            if st.button(str(a), key=f"ano_{a}",
                         type="primary" if a==ano_sel else "secondary",
                         use_container_width=True):
                st.session_state["ano_uni"] = a; st.rerun()

    kpi  = kpis_unidade(sel, ano_sel)
    meta = kpi["meta"] or 1
    pct  = kpi["real"] / meta * 100

    # KPI Cards
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-l">Meta {ano_sel}</div>
        <div class="kpi-v">{fmt_mi(meta)}</div>
      </div>
      <div class="kpi-card amber">
        <div class="kpi-l">Previsto (curva 12m)</div>
        <div class="kpi-v">{fmt_mi(kpi['previsto'])}</div>
        <div class="kpi-d">{kpi['n_projetos']} projetos ativos</div>
      </div>
      <div class="kpi-card" style="border-left-color:{TEAL};">
        <div class="kpi-l">Saving Validado</div>
        <div class="kpi-v" style="color:{TEAL};">{fmt_mi(kpi['validado'])}</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-l">Retorno Real {ano_sel}</div>
        <div class="kpi-v">{fmt_mi(kpi['real'])}</div>
        <div class="kpi-d">{pct:.1f}% da meta</div>
      </div>
      <div class="kpi-card red">
        <div class="kpi-l">GAP para Meta</div>
        <div class="kpi-v">{fmt_mi(max(meta-kpi['real'],0))}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Alertas
    alerts = alertas_pendentes(sel)
    if alerts:
        st.warning(f"⚠️ {len(alerts)} lançamento(s) de meses anteriores pendente(s).")

    # Gráfico
    fig = go.Figure()
    fig.add_trace(go.Bar(x=MESES_PT, y=kpi["prev_mensal"], name="Previsto Mensal",
                         marker_color="#7EB3D8", opacity=0.6))
    fig.add_trace(go.Bar(x=MESES_PT, y=kpi["real_mensal"], name="Real Mensal",
                         marker_color="#52A97C", opacity=0.8))
    acum_p=[]; acum_r=[]; ap=ar=0
    for p,r in zip(kpi["prev_mensal"], kpi["real_mensal"]):
        ap+=p; ar+=r; acum_p.append(ap); acum_r.append(ar)
    fig.add_trace(go.Scatter(x=MESES_PT, y=acum_p, name="Acum. Previsto",
                             mode="lines+markers",
                             line=dict(color=NAVY, width=2, dash="dot"),
                             marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=MESES_PT, y=acum_r, name="Acum. Real",
                             mode="lines+markers",
                             line=dict(color=GREEN, width=2.5),
                             marker=dict(size=6)))
    fig.add_hline(y=meta, line_dash="dash", line_color=RED,
                  annotation_text=f"Meta {fmt_mi(meta)}",
                  annotation_position="right")
    fig.update_layout(
        barmode="group", bargap=0.25,
        xaxis=dict(showgrid=True, gridcolor="#F0F4F8"),
        yaxis=dict(tickprefix="R$ ", tickformat=",.0f",
                   showgrid=True, gridcolor="#F0F4F8"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(l=60,r=20,t=40,b=30), height=320,
        paper_bgcolor="white", plot_bgcolor="white",
        hovermode="x unified", font=dict(family="Inter"),
    )
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown(f'<span class="st">Evolução Mensal — {sel} {ano_sel}</span>',
                unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

    # Projetos por tipo
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Projetos por Tipo</span>', unsafe_allow_html=True)

    from collections import defaultdict
    por_tipo = defaultdict(list)
    for p in kpi["projetos"]:
        por_tipo[p["tipo"]].append(p)

    for tipo, projs in por_tipo.items():
        tot_p = sum(p["previsto_custos"] if p["previsto_custos"]>0
                    else p["previsto_unidade"] for p in projs)
        tot_v = sum(p["saving_validado"] for p in projs)
        chk   = sum(1 for p in projs if p["check_formalizado"])
        st.markdown(f"""
        <div style="background:{NAVY};border-radius:8px;padding:10px 16px;
            display:flex;align-items:center;gap:16px;margin-top:10px;">
          <span style="color:white;font-weight:700;font-size:12px;">{tipo}</span>
          <span style="margin-left:auto;color:rgba(255,255,255,.6);font-size:11px;
              display:flex;gap:20px;">
            <span>{len(projs)} projetos</span>
            <span style="color:#C8D8EE;">Prev: <b>R$ {tot_p:,.0f}</b></span>
            <span style="color:#7BDD9A;">Val: <b>R$ {tot_v:,.0f}</b></span>
            <span style="color:#FFD700;">✅ {chk}/{len(projs)} validados</span>
          </span>
        </div>
        """, unsafe_allow_html=True)

        rows = ""
        for p in projs:
            sc_map = {"✓ Concluído":GREEN,"⏳ Em Execução":AMBER,
                      "📝 Não iniciado":SILVER,"⚠️ Suspenso":RED}
            sc = sc_map.get(p["status"], SILVER)
            chk_i = ("✅" if p["check_a3"] else "⬜") + \
                    ("✅" if p["check_memoria"] else "⬜") + \
                    ("✅" if p["check_formalizado"] else "⬜")
            alerta = "⚠️ " if any(a["proj_id"]==p["id"] for a in alerts) else ""
            rows += f"""<tr>
              <td style="font-size:11px;"><b>{alerta}{p['nome']}</b></td>
              <td style="font-size:10px;">{p.get('responsavel','—')}</td>
              <td style="font-size:10px;">{p.get('va_ggf','—')}</td>
              <td style="text-align:right;font-size:11px;">
                R$ {p['previsto_custos'] if p['previsto_custos']>0 else p['previsto_unidade']:,.0f}
              </td>
              <td style="text-align:right;font-size:11px;color:{TEAL};">
                R$ {p['saving_validado']:,.0f}
              </td>
              <td style="font-size:10px;"><span style="color:{sc};">{p['status']}</span></td>
              <td style="font-size:10px;">{chk_i}</td>
              <td style="font-size:10px;color:{SILVER};">
                {p.get('atividade_atual','') or '—'}
              </td>
            </tr>"""

        st.markdown(f"""
        <table class="dt" style="margin-bottom:6px;">
          <thead><tr>
            <th>Projeto</th><th>Resp.</th><th>VA/GGF</th>
            <th style="text-align:right;">Previsto</th>
            <th style="text-align:right;">Validado</th>
            <th>Status</th><th>A3/Mem/Form</th><th>Atividade Atual</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>
        """, unsafe_allow_html=True)

    # Campeões
    from database import listar_projetos
    camp = [p for p in listar_projetos(sel, incluir_campeao=True) if p["campeao"]]
    if camp:
        st.markdown("---")
        st.markdown('<span class="st">🏆 Projetos Campeões</span>', unsafe_allow_html=True)
        for p in camp:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#FFD700,#FFA500);
                border-radius:10px;padding:12px 18px;margin-bottom:8px;
                display:flex;align-items:center;gap:12px;">
              <span style="font-size:24px;">🏆</span>
              <div>
                <div style="font-weight:700;font-size:13px;color:#1C2B4A;">{p['nome']}</div>
                <div style="font-size:11px;color:#555;">
                  {p['tipo']} · Campeão desde {str(p.get('campeao_em',''))[:7]}
                  · Saving: R$ {p['saving_validado']:,.0f}
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
