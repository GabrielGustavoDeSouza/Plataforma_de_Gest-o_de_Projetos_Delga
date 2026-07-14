"""pages/unidade.py — Dashboard da Unidade / Área"""
import streamlit as st
import plotly.graph_objects as go
from database import listar_unidades, kpis_unidade, TIPOS_PROJETO

def render(user, ano, NAVY, RED, GREEN, AMBER, TEAL, SILVER, LIGHT):
    st.markdown(f'<span class="st">Minha Unidade — {ano}</span>', unsafe_allow_html=True)

    # Selecionar unidade (admin vê todas, operador só a sua)
    unidades = listar_unidades()
    nomes = [u["nome"] for u in unidades]

    if user.get("perfil") in ("admin", "gestor") and not user.get("unidade"):
        sel = st.selectbox("Selecionar unidade:", nomes)
    else:
        sel = user.get("unidade")
        if not sel or sel not in nomes:
            st.warning("Sua conta não está vinculada a uma unidade.")
            return
        st.markdown(f"**Unidade:** {sel}")

    kpi = kpis_unidade(sel, ano)
    meta = next((u["meta_anual"] for u in unidades if u["nome"]==sel), 0) or 1
    pct  = kpi["real"] / meta * 100

    def fmt_mi(v): return f"R$ {v/1e6:.2f} Mi" if v >= 1e6 else f"R$ {v/1e3:.0f} k"

    # KPI Cards
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div class="kpi-l">Meta {ano}</div>
        <div class="kpi-v">{fmt_mi(meta)}</div></div>
      <div class="kpi-card amber"><div class="kpi-l">Previsto Total</div>
        <div class="kpi-v">{fmt_mi(kpi['previsto'])}</div>
        <div class="kpi-d">{kpi['n_projetos']} projetos</div></div>
      <div class="kpi-card"><div class="kpi-l">Saving Validado</div>
        <div class="kpi-v">{fmt_mi(kpi['validado'])}</div></div>
      <div class="kpi-card green"><div class="kpi-l">Retorno Real (DRE)</div>
        <div class="kpi-v">{fmt_mi(kpi['real'])}</div>
        <div class="kpi-d">{pct:.1f}% da meta</div></div>
    </div>
    """, unsafe_allow_html=True)

    # Gráfico mensal
    meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    acum = []; acc = 0
    for v in kpi["real_mensal"]:
        acc += v; acum.append(acc)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=meses, y=kpi["real_mensal"], name="Real Mensal",
                         marker_color="#52A97C", opacity=0.7))
    fig.add_trace(go.Scatter(x=meses, y=acum, name="Acumulado Real",
                             line=dict(color=GREEN, width=2.5), mode="lines+markers",
                             marker=dict(size=6)))
    fig.update_layout(
        barmode="overlay",
        xaxis=dict(showgrid=True, gridcolor="#F0F4F8"),
        yaxis=dict(tickprefix="R$ ", tickformat=",.0f", showgrid=True, gridcolor="#F0F4F8"),
        legend=dict(orientation="h", y=1.05),
        margin=dict(l=60, r=20, t=40, b=30), height=280,
        paper_bgcolor="white", plot_bgcolor="white",
        hovermode="x unified", font=dict(family="Inter"),
    )
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Evolução Mensal</span>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    # Tabela de projetos por tipo
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Projetos por Tipo</span>', unsafe_allow_html=True)

    from collections import defaultdict
    por_tipo = defaultdict(list)
    for p in kpi["projetos"]:
        por_tipo[p["tipo"]].append(p)

    for tipo, projs in por_tipo.items():
        tot_prev = sum(p["previsto_rs"] for p in projs)
        tot_val  = sum(p["saving_valid"] for p in projs)
        st.markdown(f"""
        <div style="background:{NAVY};border-radius:8px;padding:10px 16px;
                    display:flex;align-items:center;gap:16px;margin-top:12px;">
          <span style="color:white;font-weight:700;font-size:12px;">{tipo}</span>
          <span style="margin-left:auto;color:rgba(255,255,255,.6);font-size:11px;">
            {len(projs)} projetos &nbsp;|&nbsp;
            Previsto: <b style="color:#C8D8EE;">R$ {tot_prev:,.0f}</b> &nbsp;|&nbsp;
            Validado: <b style="color:#7BDD9A;">R$ {tot_val:,.0f}</b>
          </span>
        </div>
        """, unsafe_allow_html=True)

        rows = ""
        for p in projs:
            status_color = {"✓ Concluído": GREEN, "⏳ Em Execução": AMBER,
                            "📝 Não iniciado": SILVER, "⚠️ Suspenso": RED}
            sc = status_color.get(p["status"], SILVER)
            rows += f"""<tr>
              <td style="font-size:11px;"><b>{p['nome']}</b></td>
              <td style="font-size:11px;">{p.get('responsavel','—')}</td>
              <td style="font-size:11px;text-align:right;">R$ {p['previsto_rs']:,.0f}</td>
              <td style="font-size:11px;text-align:right;color:{TEAL};">R$ {p['saving_valid']:,.0f}</td>
              <td style="font-size:11px;"><span style="color:{sc};">{p['status']}</span></td>
              <td style="font-size:10px;color:{SILVER};">{p.get('onde_parado','') or '—'}</td>
            </tr>"""

        st.markdown(f"""
        <table class="dt" style="margin-bottom:8px;">
          <thead><tr>
            <th>Projeto</th><th>Responsável</th>
            <th style="text-align:right;">Previsto (R$)</th>
            <th style="text-align:right;">Saving Validado</th>
            <th>Status</th><th>Onde Parado</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
