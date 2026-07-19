import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
import html as _html
from database import (listar_unidades, listar_projetos, get_lancamentos,
                      kpis_unidade, get_todas_metas, get_links, init_db,
                      is_extra_dre, get_curva_unidade, get_curva_saving,
                      normalizar_url, fmt_brl as _fmt_brl, fmt_card as _fmt_card,
                      funil_conversao, saving_por_unidade, distribuicao_por_tipo,
                      resumo_por_pilar, get_carry_over,
                      APP_VERSION, PERFIS_LBL, MESES_PT)
from auth import login_page, sidebar_user, require_login
from assets import LOGO_DATA_URI

st.set_page_config(page_title="Plataforma Delga", page_icon="🏭",
                   layout="wide", initial_sidebar_state="expanded")

# ── Paleta Grupo Delga ───────────────────────────────────────────────────────
NAVY="#0B0F2B"; BLUE="#1B2A9E"; BLUE2="#33459E"; GREEN="#1AA260"
AMBER="#E8A838"; RED="#D93B3B"; TEAL="#20C997"; SILVER="#8A9BB0"; LIGHT="#F4F6FB"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{{font-family:'Inter',sans-serif;}}
.block-container{{padding-top:0!important;padding-bottom:2rem;max-width:1400px;}}
#MainMenu{{visibility:hidden;}}footer{{visibility:hidden;}}
header[data-testid="stHeader"]{{display:none;}}
/* Sidebar sempre fixa e visível — impede que fique escondida/minimizada */
section[data-testid="stSidebar"]{{
  min-width:280px!important;width:280px!important;
  transform:none!important;visibility:visible!important;
}}
section[data-testid="stSidebar"][aria-expanded="false"]{{
  min-width:280px!important;width:280px!important;margin-left:0!important;
}}
button[data-testid="stSidebarCollapseButton"],
button[data-testid="stSidebarCollapsedControl"],
div[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"]{{display:none!important;}}
/* Esconde o menu automático de páginas do Streamlit (a pasta se chama
   "pages/" e ele tenta criar navegação nativa por cima da nossa) */
[data-testid="stSidebarNav"]{{display:none!important;}}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{{padding-top:8px!important;}}
/* Todo elemento nativo do Streamlit que usa a cor primária (botão
   selecionado, tags de multiselect, radio/checkbox) fica azul da marca —
   não depende do .streamlit/config.toml estar ativo. */
button[kind="primary"], button[kind="primaryFormSubmit"]{{
  background:linear-gradient(120deg,{BLUE} 0%,{BLUE2} 100%)!important;
  border:none!important;color:white!important;}}
button[kind="primary"] p, button[kind="primaryFormSubmit"] p{{color:white!important;}}
[data-baseweb="tag"]{{background-color:{BLUE}!important;border-color:{BLUE}!important;}}
[data-baseweb="tag"] span{{color:white!important;}}
[data-baseweb="tag"] svg{{fill:white!important;}}
input[type="radio"],input[type="checkbox"]{{accent-color:{BLUE}!important;}}
[data-baseweb="radio"] div[aria-checked="true"] svg,
[data-baseweb="checkbox"] svg{{fill:{BLUE}!important;}}
[data-testid="stRadio"] input[type="radio"]:checked + div,
[data-testid="stCheckbox"] input[type="checkbox"]:checked + div{{
  background-color:{BLUE}!important;border-color:{BLUE}!important;
  outline-color:{BLUE}!important;box-shadow:none!important;}}
[data-testid="stRadio"] input[type="radio"]:checked + div > div,
[data-testid="stCheckbox"] input[type="checkbox"]:checked + div > div{{
  background-color:{BLUE}!important;}}
label[data-testid="stRadioOption"][data-selected="true"] > div > div > div:first-child,
label[data-testid="stRadioOption"][data-selected="true"] > div > div > div:first-child:hover,
label[data-testid="stRadioOption"][data-selected="true"] > div > div > div:first-child:focus{{
  border-color:{BLUE}!important;background-color:{BLUE}!important;
  outline-color:{BLUE}!important;box-shadow:none!important;}}
label[data-testid="stRadioOption"][data-selected="true"] > div > div > div:first-child > div{{
  background-color:{BLUE}!important;border-color:{BLUE}!important;}}
/* Garante que só a bolinha é pintada — a linha/texto do item nunca ganha fundo */
label[data-testid="stRadioOption"],
label[data-testid="stRadioOption"] > div,
label[data-testid="stRadioOption"] > div > div,
label[data-testid="stRadioOption"] [data-testid="stMarkdownContainer"]{{
  background:transparent!important;box-shadow:none!important;}}
[data-testid="stSlider"] div[role="slider"]{{background-color:{BLUE}!important;}}
[data-testid="stSlider"] .stSliderTrackActive{{background-color:{BLUE}!important;}}
.plat-header{{background:linear-gradient(120deg,{NAVY} 0%,#151B45 55%,#1B1F5C 100%);
  padding:18px 30px;border-radius:0 0 16px 16px;display:flex;align-items:center;
  gap:18px;margin-bottom:20px;box-shadow:0 4px 20px rgba(11,15,43,.25);
  position:relative;overflow:hidden;}}
.plat-header::after{{content:"";position:absolute;top:-60%;right:-6%;width:260px;height:260px;
  background:radial-gradient(circle,{BLUE}55 0%,transparent 70%);pointer-events:none;}}
.plat-logo-box{{background:white;border-radius:10px;padding:7px 12px;
  display:flex;align-items:center;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,.12);}}
.plat-logo-box img{{height:26px;display:block;}}
.plat-title{{color:white;font-size:18px;font-weight:700;margin:0;letter-spacing:.2px;}}
.plat-sub{{color:rgba(255,255,255,.55);font-size:11px;margin:2px 0 0;}}
.plat-badge{{margin-left:auto;background:rgba(255,255,255,.10);color:rgba(255,255,255,.85);
  font-size:11px;font-weight:600;padding:5px 14px;border-radius:20px;
  white-space:nowrap;border:1px solid rgba(255,255,255,.16);position:relative;z-index:1;}}
.kpi-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:12px;margin-bottom:16px;}}
.kpi-card{{background:white;border-radius:12px;padding:16px 18px;
  border-left:4px solid {BLUE};
  box-shadow:0 1px 4px rgba(11,15,43,.06),0 4px 16px rgba(11,15,43,.04);}}
.kpi-card.green{{border-left-color:{GREEN};}}
.kpi-card.amber{{border-left-color:{AMBER};}}
.kpi-card.red{{border-left-color:{RED};}}
.kpi-l{{font-size:9px;font-weight:600;color:{SILVER};text-transform:uppercase;
  letter-spacing:.8px;margin-bottom:6px;}}
.kpi-v{{font-size:20px;font-weight:700;color:{NAVY};line-height:1.1;}}
.kpi-d{{font-size:10px;color:{SILVER};margin-top:3px;}}
.sc{{background:white;border-radius:12px;padding:20px 22px;
  box-shadow:0 1px 4px rgba(11,15,43,.06),0 4px 16px rgba(11,15,43,.04);
  margin-bottom:16px;}}
.st{{font-size:11px;font-weight:700;color:{NAVY};text-transform:uppercase;
  letter-spacing:.7px;border-bottom:2px solid {BLUE};
  padding-bottom:6px;margin-bottom:14px;display:inline-block;}}
.dt{{width:100%;border-collapse:collapse;font-size:12px;}}
.dt thead th{{background:{NAVY};color:white;padding:9px 12px;
  text-align:left;font-size:11px;font-weight:600;}}
.dt tbody tr:nth-child(even){{background:#FAFBFC;}}
.dt tbody tr:hover{{background:#F0F4FA;}}
.dt tbody td{{padding:8px 12px;border-bottom:1px solid #EEF0F3;vertical-align:middle;}}
</style>
""", unsafe_allow_html=True)

if "user" not in st.session_state:
    login_page(); st.stop()

require_login()
sidebar_user()

user     = st.session_state["user"]
perfil   = user["perfil"]
ano_atual= datetime.now().year

st.markdown(f"""
<div class="plat-header">
  <div class="plat-logo-box"><img src="{LOGO_DATA_URI}"></div>
  <div>
    <div class="plat-title">Plataforma de Gestão de Projetos</div>
    <div class="plat-sub">Grupo Delga · Redução de Custos {ano_atual}</div>
  </div>
  <div class="plat-badge">📅 {datetime.now().strftime('%d/%m/%Y')}</div>
  <div style="position:absolute;top:5px;right:14px;font-size:8px;
       color:rgba(255,255,255,.28);letter-spacing:.4px;z-index:1;">{APP_VERSION}</div>
</div>
""", unsafe_allow_html=True)

# ── Menu por perfil ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f'<span style="font-size:11px;font-weight:700;color:{NAVY};'
                f'text-transform:uppercase;letter-spacing:.5px;">Menu</span>',
                unsafe_allow_html=True)
    if perfil == "admin":
        opcoes = ["🏠 Dashboard Global","🏭 Minha Unidade",
                  "➕ Novo Projeto","💰 Controle de Custos",
                  "👤 Minha Conta","⚙️ Administração"]
    elif perfil == "cost_control":
        opcoes = ["🏠 Dashboard Global","🏭 Minha Unidade",
                  "💰 Controle de Custos","👤 Minha Conta"]
    elif perfil in ("facilitador","gestor"):
        opcoes = ["🏭 Minha Unidade","➕ Novo Projeto","👤 Minha Conta"]
    elif perfil == "visualizador":
        opcoes = ["🏠 Dashboard Global","🏭 Minha Unidade","👤 Minha Conta"]
    else:
        opcoes = ["🏠 Dashboard Global","👤 Minha Conta"]
    pagina = st.radio("", opcoes, label_visibility="collapsed")

# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_card(v): return _fmt_card(v)

def fmt_brl(v):
    if not v and v != 0: return "—"
    return _fmt_brl(v, 0)

def clean_html(html):
    return "".join(l.strip() for l in html.strip().split("\n"))

def hc(html): st.markdown(clean_html(html), unsafe_allow_html=True)

def linha_atrasada(p):
    if "Concluído" in str(p.get("status","")): return False
    t = str(p.get("termino","") or "").strip()
    if not t or t in ("None","nan",""): return False
    try: return date(int(t[:4]),int(t[5:7]),28) < date.today()
    except: return False

# ── Componentes do dashboard estratégico (funil, gauge, donut, distribuição) ──
def year_nav(key, help_txt=""):
    """Navegador discreto ‹ ano › — nasce sempre no ano corrente, mas deixa
    andar livremente pra qualquer ano (mesmo zerado)."""
    if key not in st.session_state:
        st.session_state[key] = datetime.now().year
    c1,c2,c3 = st.columns([1,2,1])
    with c1:
        if st.button("‹", key=f"{key}_prev", use_container_width=True):
            st.session_state[key] -= 1; st.rerun()
    with c2:
        hc(f'<div style="text-align:center;font-size:13px;font-weight:700;'
           f'color:{NAVY};padding-top:6px;">{st.session_state[key]}</div>')
    with c3:
        if st.button("›", key=f"{key}_next", use_container_width=True):
            st.session_state[key] += 1; st.rerun()
    return st.session_state[key]

def render_carry_over(ano_ref, unidade_nome=None):
    """Botão discreto que só aparece quando há valor de retorno previsto
    saindo do ano vigente pro ano seguinte (Ganho a partir de fora de jan)."""
    fora = get_carry_over(ano_ref, unidade_nome)
    seguinte = [f for f in fora if f["direcao"]=="seguinte"]
    if not seguinte: return
    total = sum(f["valor"] for f in seguinte)
    with st.expander(f"↷ Carry Over — {fmt_brl(total)} de {ano_ref} com retorno "
                     f"previsto em {ano_ref+1}", expanded=False):
        rows = "".join(f"""<tr>
          <td style="font-size:11px;font-weight:600;">{f['projeto']}</td>
          <td style="font-size:11px;">{f['unidade']}</td>
          <td style="font-size:11px;text-align:center;">{MESES_PT[f['mes']-1]}/{f['ano']}</td>
          <td style="font-size:11px;text-align:right;color:{BLUE};">{fmt_brl(f['valor'])}</td>
        </tr>""" for f in seguinte)
        hc(f"""<table class="dt"><thead><tr><th>Projeto</th><th>Unidade</th>
          <th>Mês</th><th style="text-align:right;">Valor</th></tr></thead>
          <tbody>{rows}</tbody></table>""")

def build_funnel(dados):
    labels  = ["Meta do Grupo","Previsto (Unidade)","Validado por Custos","Real Lançado"]
    valores = [dados["meta"], dados["previsto"], dados["validado"], dados["real"]]
    fig = go.Figure(go.Funnel(
        y=labels, x=valores, textposition="inside",
        texttemplate="%{value:,.0f}<br>(%{percentInitial})",
        marker=dict(color=[NAVY, BLUE, BLUE2, GREEN]),
        connector=dict(line=dict(color="#E2E8F0", width=1))))
    fig.update_layout(separators=",.", margin=dict(l=10,r=10,t=10,b=10), height=320,
                       paper_bgcolor="white", plot_bgcolor="white",
                       font=dict(family="Inter", size=12))
    return fig

def build_gauge(pct):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=min(pct,100) if pct<999 else 100,
        number={"suffix":"%","font":{"size":32,"color":NAVY},
                "valueformat":".1f"},
        gauge={"axis":{"range":[0,100],"tickcolor":SILVER,"tickfont":{"size":9}},
               "bar":{"color":BLUE,"thickness":0.28},
               "bgcolor":"white","borderwidth":0,
               "steps":[{"range":[0,40],"color":"#EAF0FB"},
                        {"range":[40,70],"color":"#FFF6E5"},
                        {"range":[70,100],"color":"#E6F4EC"}]}))
    fig.update_layout(margin=dict(l=24,r=24,t=20,b=10), height=320,
                       paper_bgcolor="white", font=dict(family="Inter"))
    return fig

def build_donut(dados):
    labels  = [d["unidade"] for d in dados]
    valores = [d["valor"] for d in dados]
    paleta  = [NAVY, BLUE, BLUE2, TEAL, "#6B7FD7", "#8A9BB0", "#B8C4E0", "#4A5FC1"]
    fig = go.Figure(go.Pie(
        labels=labels, values=valores, hole=0.62, sort=False,
        marker=dict(colors=paleta[:len(labels)], line=dict(color="white", width=2)),
        textinfo="none",
        hovertemplate="%{label}: R$ %{value:,.0f} (%{percent})<extra></extra>"))
    fig.update_layout(margin=dict(l=10,r=10,t=10,b=10), height=300,
                       paper_bgcolor="white", separators=",.",
                       legend=dict(orientation="v", font=dict(size=11)),
                       annotations=[dict(text=fmt_card(sum(valores)), x=0.5, y=0.5,
                                          font=dict(size=15, color=NAVY), showarrow=False)])
    return fig

def build_distribuicao(dist, series_sel):
    tipos = sorted(dist.keys(), key=lambda t: -dist[t]["previsto"])
    cor = {"Previsto":SILVER, "Validado":BLUE, "Real":GREEN}
    fig = go.Figure()
    for serie in ["Previsto","Validado","Real"]:
        if serie not in series_sel: continue
        vals = [dist[t][serie.lower()] for t in tipos]
        fig.add_trace(go.Bar(y=tipos, x=vals, name=serie, orientation="h",
                              marker_color=cor[serie],
                              hovertemplate="%{y}: R$ %{x:,.0f}<extra>"+serie+"</extra>"))
    fig.update_layout(barmode="group", separators=",.",
                       height=max(280, 46*len(tipos)),
                       margin=dict(l=10,r=10,t=10,b=10),
                       paper_bgcolor="white", plot_bgcolor="white",
                       xaxis=dict(tickprefix="R$ ", tickformat=",.0f", showgrid=True, gridcolor="#F0F4F8"),
                       legend=dict(orientation="h", y=1.08),
                       font=dict(family="Inter", size=11))
    return fig

def render_pilar_table(pilares):
    rows=""; tq=tp=tv=tr=0
    for tipo, d in sorted(pilares.items(), key=lambda x:-x[1]["previsto"]):
        badge = ('<span style="color:#9B59B6;">↷ N/DRE</span>' if d["extra"]
                  else f'<span style="color:{GREEN};">✓ DRE</span>')
        rows += f"""<tr>
          <td style="font-weight:600;">{tipo}<br><span style="font-size:9px;">{badge}</span></td>
          <td style="text-align:center;">{d['qtd']}</td>
          <td style="text-align:right;">{fmt_brl(d['previsto'])}</td>
          <td style="text-align:right;color:{BLUE};">{fmt_brl(d['validado'])}</td>
          <td style="text-align:right;color:{GREEN};font-weight:600;">{fmt_brl(d['real_total'])}</td>
        </tr>"""
        tq+=d['qtd']; tp+=d['previsto']; tv+=d['validado']; tr+=d['real_total']
    rows += f"""<tr style="background:#F4F6FB;font-weight:700;">
      <td>TOTAL</td><td style="text-align:center;">{tq}</td>
      <td style="text-align:right;">{fmt_brl(tp)}</td>
      <td style="text-align:right;color:{BLUE};">{fmt_brl(tv)}</td>
      <td style="text-align:right;color:{GREEN};">{fmt_brl(tr)}</td></tr>"""
    hc(f"""<table class="dt"><thead><tr>
      <th>Pilar</th><th>Qtd</th><th style="text-align:right;">Saving Previsto</th>
      <th style="text-align:right;">Saving Validado</th>
      <th style="text-align:right;">Até o Momento</th>
    </tr></thead><tbody>{rows}</tbody></table>""")

# ── Dashboard Global ──────────────────────────────────────────────────────────
if pagina == "🏠 Dashboard Global":
    init_db()
    unidades   = listar_unidades()
    todos_proj = listar_projetos()

    c_tit, c_uni, c_nav = st.columns([3,2,1])
    with c_tit:
        st.markdown('<span class="st">Visão Estratégica do Grupo</span>', unsafe_allow_html=True)
    with c_uni:
        VISAO_GERAL = "— Visão Geral (Grupo) —"
        uni_opcoes = [VISAO_GERAL] + [u["nome"] for u in unidades]
        uni_pick = st.selectbox("Unidade:", uni_opcoes, index=0,
                                 key="dash_uni_filtro", label_visibility="collapsed")
        unidade_filtro = None if uni_pick == VISAO_GERAL else uni_pick
    with c_nav:
        ano_dash = year_nav("dash_ano")

    render_carry_over(ano_dash, unidade_filtro)

    funil = funil_conversao(ano_dash, unidade_filtro)
    n_proj = len(todos_proj if not unidade_filtro else
                 [p for p in todos_proj if p["unidade_nome"]==unidade_filtro])

    titulo_escopo = unidade_filtro if unidade_filtro else "Grupo"

    c1, c2 = st.columns([3,2])
    with c1:
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown(f'<span class="st">Funil de Conversão — Portfólio → DRE ({titulo_escopo}, {ano_dash})</span>', unsafe_allow_html=True)
        st.caption("Quanto do portfólio mapeado converte em resultado no DRE?")
        st.plotly_chart(build_funnel(funil), use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        st.markdown(f'<span class="st">Atingimento da Meta — {titulo_escopo}</span>', unsafe_allow_html=True)
        st.plotly_chart(build_gauge(funil["pct_meta"]), use_container_width=True, config={"displayModeBar":False})
        cg1, cg2 = st.columns(2)
        with cg1:
            hc(f"""<div style="background:#F4F6FB;border-radius:8px;padding:8px 12px;">
                <div style="font-size:9px;color:{SILVER};text-transform:uppercase;">Gap para Meta</div>
                <div style="font-size:15px;font-weight:700;color:{NAVY};">{fmt_brl(max(funil['meta']-funil['real'],0))}</div>
                </div>""")
        with cg2:
            hc(f"""<div style="background:#F4F6FB;border-radius:8px;padding:8px 12px;">
                <div style="font-size:9px;color:{SILVER};text-transform:uppercase;">Validado / Meta</div>
                <div style="font-size:15px;font-weight:700;color:{NAVY};">{(funil['validado']/funil['meta']*100 if funil['meta']>0 else 0):.1f}%</div>
                </div>""")
        st.markdown('</div>', unsafe_allow_html=True)

    # Nota metodológica
    hc(f"""
<div style="background:#FFFBF0;border-left:3px solid {AMBER};border-radius:0 6px 6px 0;
     padding:8px 14px;margin-bottom:16px;font-size:10px;color:#555;">
  <b>Metodologia:</b>
  <span style="color:{GREEN};">✓ DRE:</span> BSW · Kaizen · Kaizen GR · Redução de Custo · Você Resolve · Estratégia Comercial — impacto direto e mensurável no DRE. &nbsp;
  <span style="color:#9B59B6;">↷ Não DRE:</span> Kaizen Custo Evitado · Kaizen Capital de Giro · Meta Executiva — geram valor operacional mas não reduzem GGF no DRE.
</div>""")

    if not unidade_filtro:
        d1, d2 = st.columns(2)
        with d1:
            st.markdown('<div class="sc">', unsafe_allow_html=True)
            st.markdown('<span class="st">Representatividade — Plantas</span>', unsafe_allow_html=True)
            dados_planta = saving_por_unidade(ano_dash, "planta")
            if dados_planta:
                st.plotly_chart(build_donut(dados_planta), use_container_width=True, config={"displayModeBar":False})
            else:
                st.caption("Sem saving validado em plantas neste ano ainda.")
            st.markdown('</div>', unsafe_allow_html=True)
        with d2:
            st.markdown('<div class="sc">', unsafe_allow_html=True)
            st.markdown('<span class="st">Representatividade — Áreas Funcionais</span>', unsafe_allow_html=True)
            dados_area = saving_por_unidade(ano_dash, "area")
            if dados_area:
                st.plotly_chart(build_donut(dados_area), use_container_width=True, config={"displayModeBar":False})
            else:
                st.caption("Sem saving validado em áreas neste ano ainda.")
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown(f'<span class="st">Distribuição por Tipo de Iniciativa — {titulo_escopo}</span>', unsafe_allow_html=True)
    series_sel = st.multiselect("Séries:", ["Previsto","Validado","Real"],
                                 default=["Previsto","Validado"], key="dist_series")
    dist = distribuicao_por_tipo(ano_dash, unidade_filtro)
    if dist and series_sel:
        st.plotly_chart(build_distribuicao(dist, series_sel), use_container_width=True, config={"displayModeBar":False})
    else:
        st.caption("Sem dados suficientes para este ano.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown(f'<span class="st">Resumo por Pilar — {titulo_escopo}</span>', unsafe_allow_html=True)
    pilares = resumo_por_pilar(unidade_filtro)
    if pilares:
        render_pilar_table(pilares)
    else:
        st.caption("Nenhum projeto cadastrado ainda.")
    st.markdown(f'<div style="font-size:10px;color:{SILVER};margin-top:6px;">'
               f'"Até o Momento" é o acumulado histórico de real lançado, considerando todos os anos.</div>',
               unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Tabela performance por unidade
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Performance por Unidade</span>', unsafe_allow_html=True)
    rows_html=""
    unidades_tab = [u for u in unidades if not unidade_filtro or u["nome"]==unidade_filtro]
    for u in unidades_tab:
        kpi   = kpis_unidade(u["nome"],ano_dash)
        meta  = kpi["meta"] or 1
        pct_u = kpi["real"]/meta*100 if kpi["meta"]>0 else 0
        bar_c = GREEN if pct_u>=60 else (AMBER if pct_u>=30 else SILVER)
        bar_w = min(pct_u,100)
        badge = (f'<span style="background:#E6F4EC;color:{GREEN};font-size:10px;'
                 f'padding:2px 8px;border-radius:10px;font-weight:600;">DESTAQUE ✓</span>'
                 if pct_u>=30 else
                 f'<span style="background:#FFF3E0;color:{AMBER};font-size:10px;'
                 f'padding:2px 8px;border-radius:10px;font-weight:600;">EM EXECUÇÃO</span>')
        rows_html += f"""<tr>
          <td style="font-weight:600;">{u['nome']}</td>
          <td style="font-size:11px;">{u['tipo'].title()}</td>
          <td style="text-align:right;">{fmt_brl(kpi['meta'])}</td>
          <td style="text-align:right;color:{SILVER};">{fmt_brl(kpi['previsto'])}</td>
          <td style="text-align:right;color:{BLUE};">{fmt_brl(kpi['validado'])}</td>
          <td style="text-align:right;color:{GREEN};font-weight:600;">{fmt_brl(kpi['real'])}</td>
          <td><div style="display:flex;align-items:center;gap:8px;">
            <div style="width:70px;height:7px;background:#E2E8F0;border-radius:4px;overflow:hidden;">
              <div style="width:{bar_w:.0f}%;height:100%;background:{bar_c};border-radius:4px;"></div>
            </div>
            <span style="font-size:11px;">{pct_u:.1f}%</span></div></td>
          <td>{badge}</td></tr>"""
    hc(f"""<table class="dt"><thead><tr>
      <th>Unidade</th><th>Tipo</th>
      <th style="text-align:right;">Meta</th>
      <th style="text-align:right;color:{SILVER};">Previsto</th>
      <th style="text-align:right;color:{BLUE};">Validado</th>
      <th style="text-align:right;color:{GREEN};">Real</th>
      <th>% Meta</th><th>Status</th>
    </tr></thead><tbody>{rows_html}</tbody></table>""")
    st.markdown('</div>', unsafe_allow_html=True)

    # Lista global de projetos
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Todos os Projetos</span>', unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns([2,2,2,3])
    with c1: f_uni=st.multiselect("Unidade:",[u["nome"] for u in unidades],default=([unidade_filtro] if unidade_filtro else []),placeholder="Todas",key="gp_uni")
    with c2: f_st=st.multiselect("Status:",list({p["status"] for p in todos_proj}),default=[],placeholder="Todos",key="gp_st")
    with c3: f_ord=st.selectbox("Ordenar:",["Unidade","Maior Previsto","Atrasados primeiro"],key="gp_ord")
    with c4: f_nm=st.text_input("🔍 Buscar",placeholder="Nome...",key="gp_nm")

    pf=todos_proj[:]
    if f_uni: pf=[p for p in pf if p["unidade_nome"] in f_uni]
    if f_st:  pf=[p for p in pf if p["status"] in f_st]
    if f_nm:  pf=[p for p in pf if f_nm.lower() in p["nome"].lower()]
    ord_map={"Unidade":lambda p:p["unidade_nome"],
             "Maior Previsto":lambda p:-(p["previsto_custos"] if p["previsto_custos"]>0 else p["previsto_unidade"]),
             "Atrasados primeiro":lambda p:(0 if linha_atrasada(p) else 1)}
    pf=sorted(pf,key=ord_map.get(f_ord,lambda p:p["unidade_nome"]))

    atrasados=sum(1 for p in pf if linha_atrasada(p))
    st.caption(f"{len(pf)} projetos" + (f" · ⚠️ {atrasados} atrasado(s)" if atrasados else ""))

    sc_map={"✓ Concluído":GREEN,"⏳ Em Execução":AMBER,"📝 Não iniciado":SILVER,"⚠️ Suspenso":RED}
    for p in pf:
        atrasado=linha_atrasada(p); extra=is_extra_dre(p["tipo"])
        border_c=RED if atrasado else (GREEN if "Concluído" in str(p.get("status","")) else NAVY)
        sc=sc_map.get(p["status"],SILVER)
        chk=("✅" if p["check_a3"] else "⬜")+("✅" if p["check_memoria"] else "⬜")+("✅" if p["check_formalizado"] else "⬜")
        links=get_links(p["id"])
        link_html=" ".join(
            f'<a href="{_html.escape(normalizar_url(lk["url"]), quote=True)}" target="_blank" '
            f'rel="noopener noreferrer" style="display:inline-block;background:#EEF0F3;'
            f'color:{NAVY};font-size:10px;padding:2px 8px;border-radius:8px;'
            f'text-decoration:none;margin-right:4px;">'
            f'🔗 {_html.escape(lk["titulo"])}</a>'
            for lk in links) if links else ""
        prev_val=p["previsto_unidade"]
        dre_b=(f'<span style="background:#F3E8FF;color:#9B59B6;font-size:9px;'
               f'padding:1px 6px;border-radius:6px;font-weight:600;margin-left:4px;">↷ N/DRE</span>'
               if extra else
               f'<span style="background:#E6F4EC;color:{GREEN};font-size:9px;'
               f'padding:1px 6px;border-radius:6px;font-weight:600;margin-left:4px;">✓ DRE</span>')
        vok_c=GREEN if p.get("validador_ok")=="OK" else (RED if p.get("validador_ok")=="NOK" else AMBER)
        hc(f"""
<div style="border-left:4px solid {border_c};background:white;border-radius:0 8px 8px 0;
     padding:10px 16px;margin-bottom:4px;box-shadow:0 1px 4px rgba(28,43,74,.06);">
  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
    <div style="flex:1;min-width:200px;">
      <div style="font-size:10px;color:{SILVER};">{p['unidade_nome']} · {p['tipo']}{dre_b}</div>
      <div style="font-size:12px;font-weight:700;color:{'#C8202E' if atrasado else NAVY};margin-top:2px;">
        #{p['id']} — {p['nome']}{'<span style="font-size:10px;color:#C8202E;margin-left:8px;">⚠️ ATRASADO</span>' if atrasado else ''}
      </div>
      <div style="font-size:10px;color:{SILVER};margin-top:2px;">
        Resp: <b>{p.get('responsavel','—')}</b> ·
        Término: <b>{str(p.get('termino','—') or '—')[:7]}</b> ·
        Custos: <b style="color:{vok_c};">{p.get('validador_ok','Pendente')}</b>
      </div>
      {f'<div style="margin-top:4px;">{link_html}</div>' if link_html else ''}
    </div>
    <div style="display:flex;gap:14px;align-items:center;flex-shrink:0;">
      <div style="text-align:center;">
        <div style="font-size:9px;color:{SILVER};text-transform:uppercase;letter-spacing:.4px;">Previsto</div>
        <div style="font-size:12px;font-weight:700;color:{AMBER};">{fmt_brl(prev_val)}</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:9px;color:{SILVER};text-transform:uppercase;letter-spacing:.4px;">Validado</div>
        <div style="font-size:12px;font-weight:700;color:{TEAL};">{fmt_brl(p['saving_validado'])}</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:9px;color:{SILVER};text-transform:uppercase;letter-spacing:.4px;">Status</div>
        <div style="font-size:11px;font-weight:600;color:{sc};">{p['status']}</div>
      </div>
      <div style="text-align:center;">
        <div style="font-size:9px;color:{SILVER};text-transform:uppercase;letter-spacing:.4px;">A3·Mem·Form</div>
        <div style="font-size:13px;">{chk}</div>
      </div>
    </div>
  </div>
</div>""")
    st.markdown('</div>', unsafe_allow_html=True)

elif pagina == "🏭 Minha Unidade":
    from pages.unidade import render
    render(user, NAVY=NAVY, BLUE=BLUE, BLUE2=BLUE2, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)

elif pagina == "➕ Novo Projeto":
    from pages.novo_projeto import render
    render(user, NAVY=NAVY, BLUE=BLUE, BLUE2=BLUE2, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)

elif pagina == "💰 Controle de Custos":
    from pages.lancamento import render
    render(user, NAVY=NAVY, BLUE=BLUE, BLUE2=BLUE2, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)

elif pagina == "👤 Minha Conta":
    from pages.minha_conta import render
    render(user, NAVY=NAVY, BLUE=BLUE, BLUE2=BLUE2, RED=RED, GREEN=GREEN, SILVER=SILVER)

elif pagina == "⚙️ Administração":
    from pages.admin import render
    render(user, NAVY=NAVY, BLUE=BLUE, BLUE2=BLUE2, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)
