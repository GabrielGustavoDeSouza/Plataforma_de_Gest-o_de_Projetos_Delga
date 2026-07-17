import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
from database import (listar_unidades, listar_projetos, get_lancamentos,
                      kpis_unidade, get_todas_metas, get_links, init_db,
                      is_extra_dre, get_curva_unidade, PERFIS_LBL)
from auth import login_page, sidebar_user, require_login

st.set_page_config(page_title="Plataforma Delga", page_icon="🏭",
                   layout="wide", initial_sidebar_state="expanded")

NAVY="#1C2B4A"; RED="#C8202E"; GREEN="#1A7A3A"
AMBER="#E8A838"; TEAL="#20C997"; SILVER="#8A9BB0"; LIGHT="#F4F6FB"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
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
.kpi-grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:12px;margin-bottom:16px;}}
.kpi-card{{background:white;border-radius:12px;padding:16px 18px;
  border-left:4px solid {NAVY};
  box-shadow:0 1px 4px rgba(28,43,74,.06),0 4px 16px rgba(28,43,74,.04);}}
.kpi-card.green{{border-left-color:{GREEN};}}
.kpi-card.amber{{border-left-color:{AMBER};}}
.kpi-card.red{{border-left-color:{RED};}}
.kpi-l{{font-size:9px;font-weight:600;color:{SILVER};text-transform:uppercase;
  letter-spacing:.8px;margin-bottom:6px;}}
.kpi-v{{font-size:20px;font-weight:700;color:{NAVY};line-height:1.1;}}
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

if "user" not in st.session_state:
    login_page(); st.stop()

require_login()
sidebar_user()

user     = st.session_state["user"]
perfil   = user["perfil"]
ano_atual= datetime.now().year

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
def fmt_card(v):
    """M para milhão, k para milhar — padrão brasileiro."""
    if v is None: return "—"
    v = float(v)
    if abs(v) >= 1_000_000:
        s = f"{v/1_000_000:.2f}".replace(".",",")
        return f"R$ {s}M"
    if abs(v) >= 1_000:
        s = f"{v/1_000:.1f}".replace(".",",")
        return f"R$ {s}k"
    return f"R$ {v:.0f}"

def fmt_brl(v):
    if not v and v != 0: return "—"
    return f"R$ {float(v):,.0f}".replace(",","X").replace(".",",").replace("X",".")

def clean_html(html):
    return "".join(l.strip() for l in html.strip().split("\n"))

def hc(html): st.markdown(clean_html(html), unsafe_allow_html=True)

def linha_atrasada(p):
    if "Concluído" in str(p.get("status","")): return False
    t = str(p.get("termino","") or "").strip()
    if not t or t in ("None","nan",""): return False
    try: return date(int(t[:4]),int(t[5:7]),28) < date.today()
    except: return False

# ── Dashboard Global ──────────────────────────────────────────────────────────
if pagina == "🏠 Dashboard Global":
    init_db()
    unidades   = listar_unidades()
    todos_proj = listar_projetos()
    metas_ano  = get_todas_metas(ano_atual)
    total_meta = sum(m["valor"] for m in metas_ano)
    hoje       = date.today()

    # Calcular KPIs globais
    total_prev_uni = 0.0
    total_validado = 0.0
    total_real     = 0.0
    total_extra    = 0.0

    for p in todos_proj:
        extra = is_extra_dre(p["tipo"])
        curva = get_curva_unidade(p["id"])
        if extra:
            # Extra DRE: soma frações dos meses já passados
            for (y,m),v in curva.items():
                if y==ano_atual and date(y,m,1) <= date(hoje.year,hoje.month,1):
                    total_extra += v
        else:
            # DRE: soma frações do ano
            prev_ano = sum(v for (y,m),v in curva.items() if y==ano_atual)
            total_prev_uni += prev_ano
            if any(y==ano_atual for (y,m) in curva):
                total_validado += p["saving_validado"]

    # Real: lançamentos DRE do ano
    for l in get_lancamentos(ano=ano_atual):
        p_tipo = next((p["tipo"] for p in todos_proj if p["id"]==l["projeto_id"]),"")
        if not is_extra_dre(p_tipo):
            total_real += l["valor_real"]

    n_proj = len(todos_proj)
    pct    = total_real/total_meta*100 if total_meta>0 else 0
    pct_c  = GREEN if pct>=60 else (AMBER if pct>=30 else RED)

    hc(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-l">Meta Anual {ano_atual}</div>
    <div class="kpi-v">{fmt_card(total_meta)}</div>
    <div class="kpi-d">Todas as unidades</div>
  </div>
  <div class="kpi-card amber">
    <div class="kpi-l">Previsto (Unidade)</div>
    <div class="kpi-v">{fmt_card(total_prev_uni)}</div>
    <div class="kpi-d">Soma DRE no ano</div>
  </div>
  <div class="kpi-card" style="border-left-color:{TEAL};">
    <div class="kpi-l">Validado por Custos</div>
    <div class="kpi-v" style="color:{TEAL};">{fmt_card(total_validado)}</div>
    <div class="kpi-d">Saving validado DRE</div>
  </div>
  <div class="kpi-card" style="border-left-color:{GREEN};background:linear-gradient(135deg,#F0FBF4 0%,white 60%);">
    <div class="kpi-l">Retorno Real {ano_atual}</div>
    <div class="kpi-v" style="color:{GREEN};">{fmt_card(total_real)}</div>
    <div class="kpi-d">Lançamentos DRE</div>
  </div>
  <div class="kpi-card" style="border-left-color:{pct_c};">
    <div class="kpi-l">% Atingimento</div>
    <div class="kpi-v" style="color:{pct_c};">{pct:.1f}%</div>
    <div class="kpi-d">Real / Meta</div>
  </div>
  <div class="kpi-card" style="border-left-color:#9B59B6;">
    <div class="kpi-l">Extra DRE</div>
    <div class="kpi-v" style="color:#9B59B6;">{fmt_card(total_extra)}</div>
    <div class="kpi-d">Acumulado até hoje</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-l">Iniciativas</div>
    <div class="kpi-v">{n_proj}</div>
    <div class="kpi-d">Projetos ativos</div>
  </div>
</div>""")

    # Nota metodológica
    hc(f"""
<div style="background:#FFFBF0;border-left:3px solid {AMBER};border-radius:0 6px 6px 0;
     padding:8px 14px;margin-bottom:16px;font-size:10px;color:#555;">
  <b>Metodologia:</b>
  <span style="color:{GREEN};">✓ DRE:</span> BSW · Kaizen · Kaizen GR · Redução de Custo · Você Resolve · Estratégia Comercial — impacto direto e mensurável no DRE. &nbsp;
  <span style="color:#9B59B6;">↷ Não DRE:</span> Kaizen Custo Evitado · Kaizen Capital de Giro · Meta Executiva — geram valor operacional mas não reduzem GGF no DRE.
</div>""")

    # Tabela performance por unidade
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Performance por Unidade</span>', unsafe_allow_html=True)
    rows_html=""
    for u in unidades:
        kpi   = kpis_unidade(u["nome"],ano_atual)
        meta  = kpi["meta"] or 1
        pct_u = kpi["real"]/meta*100 if kpi["meta"]>0 else 0
        bar_c = GREEN if pct_u>=60 else (AMBER if pct_u>=30 else RED)
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
          <td style="text-align:right;color:{AMBER};">{fmt_brl(kpi['previsto'])}</td>
          <td style="text-align:right;color:{TEAL};">{fmt_brl(kpi['validado'])}</td>
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
      <th style="text-align:right;color:{AMBER};">Previsto</th>
      <th style="text-align:right;color:{TEAL};">Validado</th>
      <th style="text-align:right;color:{GREEN};">Real</th>
      <th>% Meta</th><th>Status</th>
    </tr></thead><tbody>{rows_html}</tbody></table>""")
    st.markdown('</div>', unsafe_allow_html=True)

    # Lista global de projetos
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Todos os Projetos</span>', unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns([2,2,2,3])
    with c1: f_uni=st.multiselect("Unidade:",[u["nome"] for u in unidades],default=[],placeholder="Todas",key="gp_uni")
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
            f'<a href="{lk["url"]}" target="_blank" rel="noopener noreferrer" '
            f'style="display:inline-block;background:#EEF0F3;color:{NAVY};font-size:10px;'
            f'padding:2px 8px;border-radius:8px;text-decoration:none;margin-right:4px;">'
            f'🔗 {lk["titulo"]}</a>'
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
    render(user, NAVY=NAVY, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)

elif pagina == "➕ Novo Projeto":
    from pages.novo_projeto import render
    render(user, NAVY=NAVY, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)

elif pagina == "💰 Controle de Custos":
    from pages.lancamento import render
    render(user, NAVY=NAVY, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)

elif pagina == "👤 Minha Conta":
    from pages.minha_conta import render
    render(user, NAVY=NAVY, RED=RED, GREEN=GREEN, SILVER=SILVER)

elif pagina == "⚙️ Administração":
    from pages.admin import render
    render(user, NAVY=NAVY, RED=RED, GREEN=GREEN, AMBER=AMBER, TEAL=TEAL, SILVER=SILVER, LIGHT=LIGHT)
