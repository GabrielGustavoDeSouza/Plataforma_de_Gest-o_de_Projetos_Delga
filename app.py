import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from database import listar_unidades, listar_projetos, get_lancamentos, kpis_unidade, init_db
from auth import login_page, sidebar_user, require_login

st.set_page_config(
    page_title="Plataforma Delga",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY="#1C2B4A"; RED="#C8202E"; GREEN="#1A7A3A"
AMBER="#E8A838"; TEAL="#20C997"; SILVER="#8A9BB0"; LIGHT="#F4F6FB"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html,body,[class*="css"]{{font-family:'Inter',sans-serif;}}
.block-container{{padding-top:0!important;padding-bottom:2rem;max-width:1400px;}}
#MainMenu{{visibility:hidden;}}footer{{visibility:hidden;}}
header[data-testid="stHeader"]{{display:none;}}
.plat-header{{background:linear-gradient(135deg,{NAVY} 0%,#243B55 100%);
  padding:16px 28px;border-radius:0 0 14px 14px;display:flex;align-items:center;
  gap:16px;margin-bottom:20px;box-shadow:0 2px 12px rgba(28,43,74,.18);}}
.plat-logo{{width:44px;height:44px;background:{RED};border-radius:10px;
  display:flex;align-items:center;justify-content:center;
  font-size:18px;font-weight:800;color:white;flex-shrink:0;}}
.plat-title{{color:white;font-size:18px;font-weight:700;margin:0;}}
.plat-sub{{color:rgba(255,255,255,.5);font-size:11px;margin:2px 0 0;}}
.plat-badge{{margin-left:auto;background:rgba(255,255,255,.12);color:rgba(255,255,255,.8);
  font-size:11px;font-weight:600;padding:5px 14px;border-radius:20px;
  white-space:nowrap;border:1px solid rgba(255,255,255,.18);}}
.kpi-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:20px;}}
.kpi-card{{background:white;border-radius:12px;padding:18px 20px;
  border-left:4px solid {NAVY};
  box-shadow:0 1px 4px rgba(28,43,74,.06),0 4px 16px rgba(28,43,74,.04);}}
.kpi-card.green{{border-left-color:{GREEN};}}
.kpi-card.amber{{border-left-color:{AMBER};}}
.kpi-card.red{{border-left-color:{RED};}}
.kpi-l{{font-size:9px;font-weight:600;color:{SILVER};text-transform:uppercase;
  letter-spacing:.8px;margin-bottom:6px;}}
.kpi-v{{font-size:22px;font-weight:700;color:{NAVY};}}
.kpi-d{{font-size:10px;color:{SILVER};margin-top:3px;}}
.sc{{background:white;border-radius:12px;padding:20px 22px;
  box-shadow:0 1px 4px rgba(28,43,74,.06),0 4px 16px rgba(28,43,74,.04);
  margin-bottom:16px;}}
.st{{font-size:11px;font-weight:700;color:{NAVY};text-transform:uppercase;
  letter-spacing:.7px;border-bottom:2px solid {RED};
  padding-bottom:6px;margin-bottom:14px;display:inline-block;}}
.dt{{width:100%;border-collapse:collapse;font-size:12px;}}
.dt thead th{{background:{NAVY};color:white;padding:9px 12px;
  text-align:left;font-size:11px;font-weight:600;}}
.dt tbody tr:nth-child(even){{background:#FAFBFC;}}
.dt tbody tr:hover{{background:#F0F4FA;}}
.dt tbody td{{padding:8px 12px;border-bottom:1px solid #EEF0F3;vertical-align:middle;}}
</style>
""", unsafe_allow_html=True)

# Login
if "user" not in st.session_state:
    login_page()
    st.stop()

require_login()
sidebar_user()

user = st.session_state["user"]
ano_atual = datetime.now().year

# Header
st.markdown(f"""
<div class="plat-header">
  <div class="plat-logo">GD</div>
  <div>
    <div class="plat-title">Plataforma de Gestão de Projetos</div>
    <div class="plat-sub">Grupo Delga · Redução de Custos {ano_atual}</div>
  </div>
  <div class="plat-badge">📅 {datetime.now().strftime('%d/%m/%Y')}</div>
</div>
""", unsafe_allow_html=True)

# Menu lateral
with st.sidebar:
    st.markdown(f'<span style="font-size:11px;font-weight:700;color:{NAVY};'
                f'text-transform:uppercase;letter-spacing:.5px;">Menu</span>',
                unsafe_allow_html=True)
    pagina = st.radio("", [
        "🏠 Dashboard Global",
        "🏭 Minha Unidade",
        "➕ Projetos",
        "💰 Lançar Real",
        "⚙️ Administração",
    ], label_visibility="collapsed")

def fmt_mi(v): return f"R$ {v/1e6:.2f} Mi" if abs(v)>=1e6 else f"R$ {v/1e3:.1f} k"

# Roteamento
if pagina == "🏠 Dashboard Global":
    init_db()
    unidades   = listar_unidades()
    todos_proj = listar_projetos()
    todos_lanc = get_lancamentos(ano=ano_atual)

    total_meta     = sum(0 for u in unidades)  # metas via banco
    total_previsto = sum(p["previsto_custos"] if p["previsto_custos"]>0
                         else p["previsto_unidade"] for p in todos_proj)
    total_validado = sum(p["saving_validado"] for p in todos_proj)
    total_real     = sum(l["valor_real"] for l in todos_lanc)
    n_proj         = len(todos_proj)

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-l">Total Projetos Ativos</div>
        <div class="kpi-v">{n_proj}</div>
        <div class="kpi-d">Todas as unidades</div>
      </div>
      <div class="kpi-card amber">
        <div class="kpi-l">Portfólio Previsto</div>
        <div class="kpi-v">{fmt_mi(total_previsto)}</div>
      </div>
      <div class="kpi-card" style="border-left-color:{TEAL};">
        <div class="kpi-l">Saving Validado</div>
        <div class="kpi-v" style="color:{TEAL};">{fmt_mi(total_validado)}</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-l">Retorno Real {ano_atual}</div>
        <div class="kpi-v">{fmt_mi(total_real)}</div>
      </div>
      <div class="kpi-card red">
        <div class="kpi-l">Unidades Ativas</div>
        <div class="kpi-v">{len(unidades)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Performance por Unidade</span>', unsafe_allow_html=True)

    rows_html = ""
    for u in unidades:
        kpi  = kpis_unidade(u["nome"], ano_atual)
        meta = kpi["meta"] or 1
        pct  = kpi["real"] / meta * 100 if meta else 0
        bar_c = GREEN if pct>=60 else (AMBER if pct>=30 else RED)
        bar_w = min(pct, 100)
        badge = (f'<span style="background:#E6F4EC;color:{GREEN};font-size:10px;'
                 f'padding:2px 8px;border-radius:10px;font-weight:600;">DESTAQUE ✓</span>'
                 if pct>=30 else
                 f'<span style="background:#FFF3E0;color:{AMBER};font-size:10px;'
                 f'padding:2px 8px;border-radius:10px;font-weight:600;">EM EXECUÇÃO</span>')
        rows_html += f"""<tr>
          <td style="font-weight:600;">{u['nome']}</td>
          <td style="font-size:11px;">{u['tipo'].title()}</td>
          <td style="text-align:right;">R$ {kpi['previsto']:,.0f}</td>
          <td style="text-align:right;color:{TEAL};">R$ {kpi['validado']:,.0f}</td>
          <td style="text-align:right;color:{GREEN};font-weight:600;">R$ {kpi['real']:,.0f}</td>
          <td>
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:70px;height:7px;background:#E2E8F0;border-radius:4px;overflow:hidden;">
                <div style="width:{bar_w:.0f}%;height:100%;background:{bar_c};border-radius:4px;"></div>
              </div>
              <span style="font-size:11px;">{pct:.1f}%</span>
            </div>
          </td>
          <td>{badge}</td>
        </tr>"""

    st.markdown(f"""
    <table class="dt">
      <thead><tr>
        <th>Unidade</th><th>Tipo</th>
        <th style="text-align:right;color:{AMBER};">Previsto</th>
        <th style="text-align:right;color:{TEAL};">Validado</th>
        <th style="text-align:right;color:{GREEN};">Retorno Real</th>
        <th>% Meta</th><th>Status</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Gráfico
    meses = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    fig = go.Figure()
    cores = [NAVY,"#2E86C1","#27AE60","#E67E22","#8E44AD","#C0392B","#16A085","#D35400"]
    for i, u in enumerate(unidades[:8]):
        kpi  = kpis_unidade(u["nome"], ano_atual)
        acum = []; acc = 0
        for v in kpi["real_mensal"]:
            acc += v; acum.append(acc)
        if any(v>0 for v in acum):
            fig.add_trace(go.Scatter(x=meses, y=acum, mode="lines+markers",
                name=u["nome"], line=dict(color=cores[i%len(cores)], width=2),
                marker=dict(size=5)))
    fig.update_layout(
        xaxis=dict(showgrid=True, gridcolor="#F0F4F8"),
        yaxis=dict(tickprefix="R$ ", tickformat=",.0f", showgrid=True, gridcolor="#F0F4F8"),
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center"),
        margin=dict(l=60,r=20,t=40,b=30), height=300,
        paper_bgcolor="white", plot_bgcolor="white",
        hovermode="x unified", font=dict(family="Inter"),
    )
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Evolução Real Acumulado por Unidade</span>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

elif pagina == "🏭 Minha Unidade":
    from pages.unidade import render
    render(user, NAVY=NAVY, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)

elif pagina == "➕ Projetos":
    from pages.novo_projeto import render
    render(user, NAVY=NAVY, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)

elif pagina == "💰 Lançar Real":
    from pages.lancamento import render
    render(user, NAVY=NAVY, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)

elif pagina == "⚙️ Administração":
    from pages.admin import render
    render(user, NAVY=NAVY, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)
