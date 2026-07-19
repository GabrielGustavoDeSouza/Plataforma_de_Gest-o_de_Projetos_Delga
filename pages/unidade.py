import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
import html as _html
from database import (listar_unidades, kpis_unidade, alertas_validacao,
                      alertas_lancamento, verificar_campeoes, listar_projetos,
                      atualizar_projeto, deletar_projeto, get_links, add_link,
                      del_link, get_todas_metas, get_lancamentos, get_curva_unidade,
                      get_curva_custos, is_extra_dre, get_ultima_obs_custos,
                      normalizar_url, fmt_brl as _fmt_brl, fmt_card,
                      funil_conversao, get_carry_over,
                      TIPOS_PROJETO, VA_GGF_OPTS, STATUS_OPTS, MESES_PT)

def clean_html(html):
    return "".join(l.strip() for l in html.strip().split("\n"))

def hc(html): st.markdown(clean_html(html), unsafe_allow_html=True)

def fmt_brl(v):
    if not v and v != 0: return "—"
    return _fmt_brl(v, 0)

def _parse_date(s, default=None):
    default = default or date.today()
    s = str(s or "").strip()
    if not s or s in ("None","nan"): return default
    try: return datetime.strptime(s[:10],"%Y-%m-%d").date()
    except Exception: return default

def linha_atrasada(p):
    if "Concluído" in str(p.get("status","")): return False
    t = str(p.get("termino","") or "").strip()
    if not t or t in ("None","nan",""): return False
    try: return date(int(t[:4]),int(t[5:7]),28) < date.today()
    except: return False

def render(user, **colors):
    NAVY=colors.get("NAVY","#0B0F2B"); GREEN=colors.get("GREEN","#1AA260")
    AMBER=colors.get("AMBER","#E8A838"); RED=colors.get("RED","#D93B3B")
    BLUE=colors.get("BLUE","#1B2A9E"); BLUE2=colors.get("BLUE2","#33459E")
    TEAL=colors.get("TEAL","#20C997"); SILVER=colors.get("SILVER","#8A9BB0")

    verificar_campeoes()
    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    # Seleção persistente por blocos
    pode_ver_todas = user["perfil"] in ("admin","gestor","cost_control","visualizador") \
                     and not user.get("unidade")
    if pode_ver_todas:
        if "ud_sel_nome" not in st.session_state:
            st.session_state["ud_sel_nome"] = nomes_u[0]
        hc(f'<p style="font-size:10px;font-weight:600;color:{SILVER};'
           f'text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px;">Unidade / Área</p>')
        n_cols = 4
        rows_u = [nomes_u[i:i+n_cols] for i in range(0,len(nomes_u),n_cols)]
        for row_u in rows_u:
            cols_u = st.columns(len(row_u))
            for i,nome in enumerate(row_u):
                with cols_u[i]:
                    ativo = st.session_state["ud_sel_nome"]==nome
                    if st.button(nome, key=f"usel_{nome}",
                                 type="primary" if ativo else "secondary",
                                 use_container_width=True):
                        st.session_state["ud_sel_nome"]=nome; st.rerun()
        sel = st.session_state["ud_sel_nome"]
    else:
        sel = user.get("unidade","")
        if sel not in nomes_u:
            st.warning("Unidade não configurada."); return
        hc(f'<p style="font-size:14px;font-weight:700;color:{NAVY};">{sel}</p>')

    pode_ed = user["perfil"] in ("admin","cost_control") or (
        user["perfil"] in ("facilitador","gestor") and user.get("unidade")==sel)
    is_cc = user["perfil"] in ("admin","cost_control")

    # Navegador de ano — discreto, nasce no ano corrente, anda livre pra
    # qualquer ano mesmo zerado (regra: quando virar o ano, nasce no novo
    # ano automaticamente, sem travar a navegação pro ano anterior/seguinte)
    if "ano_uni" not in st.session_state:
        st.session_state["ano_uni"] = datetime.now().year
    c_tit, c_prev, c_ano, c_next = st.columns([6,1,1,1])
    with c_tit:
        hc(f'<p style="font-size:10px;font-weight:600;color:{SILVER};'
           f'text-transform:uppercase;letter-spacing:.6px;margin-top:8px;">Ano de referência</p>')
    with c_prev:
        if st.button("‹", key="ano_uni_prev", use_container_width=True):
            st.session_state["ano_uni"] -= 1; st.rerun()
    with c_ano:
        hc(f'<div style="text-align:center;font-size:13px;font-weight:700;'
           f'color:{NAVY};padding-top:6px;">{st.session_state["ano_uni"]}</div>')
    with c_next:
        if st.button("›", key="ano_uni_next", use_container_width=True):
            st.session_state["ano_uni"] += 1; st.rerun()
    ano_sel = st.session_state["ano_uni"]

    # Carry Over — só aparece se houver valor saindo deste ano pro seguinte
    fora = get_carry_over(ano_sel, sel)
    seguinte = [f for f in fora if f["direcao"]=="seguinte"]
    if seguinte:
        total_co = sum(f["valor"] for f in seguinte)
        with st.expander(f"↷ Carry Over — {fmt_brl(total_co)} de {ano_sel} com "
                         f"retorno previsto em {ano_sel+1}", expanded=False):
            rows_co = "".join(f"""<tr>
              <td style="font-size:11px;font-weight:600;">{f['projeto']}</td>
              <td style="font-size:11px;text-align:center;">{MESES_PT[f['mes']-1]}/{f['ano']}</td>
              <td style="font-size:11px;text-align:right;color:{BLUE};">{fmt_brl(f['valor'])}</td>
            </tr>""" for f in seguinte)
            hc(f"""<table class="dt"><thead><tr><th>Projeto</th><th>Mês</th>
              <th style="text-align:right;">Valor</th></tr></thead>
              <tbody>{rows_co}</tbody></table>""")

    # Funil + Gauge enxutos, só da unidade selecionada
    funil_u = funil_conversao(ano_sel, sel)
    c_f, c_g = st.columns([3,2])
    with c_f:
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        hc(f'<p style="font-size:11px;font-weight:700;color:{NAVY};text-transform:uppercase;'
           f'letter-spacing:.7px;border-bottom:2px solid {BLUE};padding-bottom:6px;'
           f'margin-bottom:8px;display:inline-block;">Funil de Conversão — {sel} {ano_sel}</p>')
        fig_f = go.Figure(go.Funnel(
            y=["Meta","Previsto","Validado","Real"],
            x=[funil_u["meta"], funil_u["previsto"], funil_u["validado"], funil_u["real"]],
            textposition="inside", texttemplate="%{value:,.0f}<br>(%{percentInitial})",
            marker=dict(color=[NAVY, BLUE, BLUE2, GREEN]),
            connector=dict(line=dict(color="#E2E8F0", width=1))))
        fig_f.update_layout(separators=",.", margin=dict(l=10,r=10,t=10,b=10), height=260,
                             paper_bgcolor="white", plot_bgcolor="white", font=dict(family="Inter", size=11))
        st.plotly_chart(fig_f, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)
    with c_g:
        st.markdown('<div class="sc">', unsafe_allow_html=True)
        hc(f'<p style="font-size:11px;font-weight:700;color:{NAVY};text-transform:uppercase;'
           f'letter-spacing:.7px;border-bottom:2px solid {BLUE};padding-bottom:6px;'
           f'margin-bottom:8px;display:inline-block;">Atingimento da Meta</p>')
        pct_gauge = min(funil_u["pct_meta"],100) if funil_u["pct_meta"]<999 else 100
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number", value=pct_gauge,
            number={"suffix":"%","font":{"size":26,"color":NAVY},"valueformat":".1f"},
            gauge={"axis":{"range":[0,100],"tickcolor":SILVER,"tickfont":{"size":8}},
                   "bar":{"color":BLUE,"thickness":0.28},"bgcolor":"white","borderwidth":0,
                   "steps":[{"range":[0,40],"color":"#EAF0FB"},
                            {"range":[40,70],"color":"#FFF6E5"},
                            {"range":[70,100],"color":"#E6F4EC"}]}))
        fig_g.update_layout(margin=dict(l=16,r=16,t=10,b=0), height=260,
                             paper_bgcolor="white", font=dict(family="Inter"))
        st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    kpi  = kpis_unidade(sel,ano_sel)
    meta = kpi["meta"] or 1
    pct  = kpi["real"]/meta*100 if kpi["meta"]>0 else 0
    pct_c= GREEN if pct>=60 else (AMBER if pct>=30 else RED)

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    hc(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-l">Meta {ano_sel}</div>
    <div class="kpi-v">{fmt_card(kpi['meta'])}</div>
  </div>
  <div class="kpi-card amber">
    <div class="kpi-l">Previsto (Unidade)</div>
    <div class="kpi-v">{fmt_card(kpi['previsto'])}</div>
    <div class="kpi-d">{kpi['n_projetos']} projetos DRE</div>
  </div>
  <div class="kpi-card" style="border-left-color:{TEAL};">
    <div class="kpi-l">Validado por Custos</div>
    <div class="kpi-v" style="color:{TEAL};">{fmt_card(kpi['validado'])}</div>
  </div>
  <div class="kpi-card" style="border-left-color:{GREEN};background:linear-gradient(135deg,#F0FBF4 0%,white 60%);">
    <div class="kpi-l">Retorno Real {ano_sel}</div>
    <div class="kpi-v" style="color:{GREEN};">{fmt_card(kpi['real'])}</div>
  </div>
  <div class="kpi-card" style="border-left-color:{pct_c};">
    <div class="kpi-l">% Atingimento</div>
    <div class="kpi-v" style="color:{pct_c};">{pct:.1f}%</div>
    <div class="kpi-d">Real / Meta</div>
  </div>
  <div class="kpi-card" style="border-left-color:#9B59B6;">
    <div class="kpi-l">Extra DRE</div>
    <div class="kpi-v" style="color:#9B59B6;">{fmt_card(kpi['extra_dre'])}</div>
    <div class="kpi-d">Acumulado até hoje</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-l">Iniciativas</div>
    <div class="kpi-v">{kpi['n_projetos']}</div>
  </div>
</div>""")

    # Nota metodológica
    hc(f"""
<div style="background:#FFFBF0;border-left:3px solid {AMBER};border-radius:0 6px 6px 0;
     padding:8px 14px;margin:8px 0 16px;font-size:10px;color:#555;">
  <b>Metodologia:</b>
  <span style="color:{GREEN};">✓ DRE:</span> BSW · Kaizen · Kaizen GR · Redução de Custo · Você Resolve · Estratégia Comercial — impacto direto e mensurável no DRE. &nbsp;
  <span style="color:#9B59B6;">↷ Não DRE:</span> Kaizen Custo Evitado · Kaizen Capital de Giro · Meta Executiva — geram valor operacional mas não reduzem GGF no DRE.
</div>""")

    # ── Alertas colapsáveis (dois blocos independentes) ─────────────────────────
    projetos_uni = listar_projetos(sel)
    pend_valid   = alertas_validacao(sel)
    pend_lanc    = alertas_lancamento(sel)

    if pend_valid:
        with st.expander(f"🔔 {len(pend_valid)} projeto(s) aguardando validação de Custos", expanded=False):
            for p in pend_valid:
                hc(f'<div style="padding:6px 12px;background:#FFF9E6;border-radius:6px;'
                   f'margin-bottom:4px;font-size:11px;"><b>#{p["id"]} — {p["nome"]}</b> · '
                   f'Previsto: {fmt_brl(p["previsto_unidade"])}</div>')

    if pend_lanc:
        with st.expander(f"📅 {len(pend_lanc)} mês(es) aprovado(s) aguardando lançamento de real", expanded=False):
            rows_a = "".join(
                f'<tr><td style="font-size:11px;font-weight:600;">{a["projeto"]}</td>'
                f'<td style="font-size:11px;text-align:center;">{MESES_PT[a["mes"]-1]}/{a["ano"]}</td>'
                f'<td style="font-size:11px;text-align:right;color:{AMBER};">{fmt_brl(a["valor_previsto"])}</td>'
                f'<td style="font-size:11px;text-align:center;color:{SILVER};">?</td></tr>'
                for a in pend_lanc)
            hc(f'<table class="dt"><thead><tr><th>Projeto</th><th>Mês</th>'
               f'<th style="text-align:right;">Valor Previsto</th><th>Real</th>'
               f'</tr></thead><tbody>{rows_a}</tbody></table>')

    # ── Gráfico com 4 séries ──────────────────────────────────────────────────
    nomes_proj = [f"#{p['id']} — {p['nome'][:28]}" for p in projetos_uni]
    proj_map   = {f"#{p['id']} — {p['nome'][:28]}": p for p in projetos_uni}

    c1,c2=st.columns([3,4])
    with c1:
        series_opts=["Previsto Unidade","Calculado Custos","Real Mensal",
                     "Acum. Previsto Uni","Acum. Calculado","Acum. Real","Projeção Meta"]
        series_sel=st.multiselect("Séries:",series_opts,
                                   default=["Previsto Unidade","Real Mensal",
                                            "Acum. Previsto Uni","Acum. Real","Projeção Meta"],
                                   key="gr_series")
    with c2:
        proj_sel=st.multiselect("Projetos (vazio=todos):",nomes_proj,
                                 default=[],key="gr_projs",
                                 placeholder="Todos os projetos")

    # Calcular dados
    if proj_sel:
        pu_m=[0.0]*12; pc_m=[0.0]*12; re_m=[0.0]*12
        for np in proj_sel:
            p=proj_map[np]
            cu=get_curva_unidade(p["id"]); cc=get_curva_custos(p["id"])
            lancs={l["mes"]:l["valor_real"] for l in get_lancamentos(proj_id=p["id"],ano=ano_sel)}
            for mes in range(1,13):
                pu_m[mes-1]+=cu.get((ano_sel,mes),0)
                pc_m[mes-1]+=cc.get((ano_sel,mes),0)
                re_m[mes-1]+=lancs.get(mes,0)
        titulo_g=", ".join(proj_sel[:2])+("..." if len(proj_sel)>2 else "")
    else:
        pu_m=kpi["prev_mensal_uni"]
        pc_m=kpi["prev_mensal_custos"]
        re_m=kpi["real_mensal"]
        titulo_g=sel

    # Acumulados
    apu=[]; apc=[]; are=[]; s1=s2=s3=0
    for a,b,c in zip(pu_m,pc_m,re_m):
        s1+=a; s2+=b; s3+=c
        apu.append(s1); apc.append(s2); are.append(s3)

    # Projeção da meta: (meta - real_acum) / meses_restantes
    hoje=date.today()
    mes_atual=hoje.month if hoje.year==ano_sel else (12 if hoje.year>ano_sel else 0)
    proj_meta_m=[None]*12
    real_acum_ate_agora=are[mes_atual-1] if mes_atual>0 else 0
    meses_restantes=12-mes_atual
    if meses_restantes>0 and kpi["meta"]>0:
        necessario=(kpi["meta"]-real_acum_ate_agora)/meses_restantes
        for m in range(mes_atual,12):
            proj_meta_m[m]=necessario

    fig=go.Figure()
    cores={
        "Previsto Unidade":  ("#7EB3D8","bar"),
        "Calculado Custos":  ("#F39C12","bar"),
        "Real Mensal":       ("#52A97C","bar"),
        "Acum. Previsto Uni":(NAVY,"line_dot"),
        "Acum. Calculado":   ("#F39C12","line_dot"),
        "Acum. Real":        (GREEN,"line"),
        "Projeção Meta":     (BLUE2,"line_dash"),
    }
    dados={
        "Previsto Unidade":  pu_m,
        "Calculado Custos":  pc_m,
        "Real Mensal":       re_m,
        "Acum. Previsto Uni":apu,
        "Acum. Calculado":   apc,
        "Acum. Real":        are,
        "Projeção Meta":     proj_meta_m,
    }
    for s in series_sel:
        cor,tp=cores[s]; d=dados[s]
        if tp=="bar":
            fig.add_trace(go.Bar(x=MESES_PT,y=d,name=s,marker_color=cor,opacity=0.75))
        elif tp=="line_dot":
            fig.add_trace(go.Scatter(x=MESES_PT,y=d,name=s,mode="lines+markers",
                line=dict(color=cor,width=2,dash="dot"),marker=dict(size=5)))
        elif tp=="line_dash":
            # Projeção: só meses futuros
            x_d=[MESES_PT[i] for i,v in enumerate(d) if v is not None]
            y_d=[v for v in d if v is not None]
            if x_d:
                fig.add_trace(go.Scatter(x=x_d,y=y_d,name=s,mode="lines+markers",
                    line=dict(color=cor,width=3,dash="dash"),marker=dict(size=7),
                    hovertemplate="<b>Ritmo necessário</b><br>%{x}: R$ %{y:,.0f}/mês<extra></extra>"))
        else:
            fig.add_trace(go.Scatter(x=MESES_PT,y=d,name=s,mode="lines+markers",
                line=dict(color=cor,width=2.5),marker=dict(size=6)))

    if kpi["meta"]>0 and not proj_sel:
        fig.add_hline(y=kpi["meta"],line_dash="dash",line_color=BLUE2,
                      annotation_text=f"Meta {fmt_card(kpi['meta'])}",
                      annotation_position="right")

    fig.update_layout(
        separators=",.",  # padrão BR: vírgula decimal, ponto milhar
        barmode="group",bargap=0.2,
        xaxis=dict(showgrid=True,gridcolor="#F0F4F8"),
        yaxis=dict(tickprefix="R$ ",tickformat=",.0f",showgrid=True,gridcolor="#F0F4F8"),
        legend=dict(orientation="h",y=1.05,x=0.5,xanchor="center"),
        margin=dict(l=60,r=20,t=40,b=30),height=340,
        paper_bgcolor="white",plot_bgcolor="white",
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white",font_size=12,namelength=-1),
        font=dict(family="Inter"))

    hc(f'<p style="font-size:11px;font-weight:700;color:{NAVY};text-transform:uppercase;'
       f'letter-spacing:.7px;border-bottom:2px solid {BLUE};padding-bottom:6px;'
       f'margin-bottom:8px;display:inline-block;">Evolução Mensal — {titulo_g} {ano_sel}</p>')
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})

    # ── Lista de Projetos ─────────────────────────────────────────────────────
    hc(f'<p style="font-size:11px;font-weight:700;color:{NAVY};text-transform:uppercase;'
       f'letter-spacing:.7px;border-bottom:2px solid {BLUE};padding-bottom:6px;'
       f'margin:20px 0 14px;display:inline-block;">Projetos da Unidade</p>')

    c1,c2,c3=st.columns([2,2,4])
    with c1: f_st=st.multiselect("Status:",list({p["status"] for p in projetos_uni}),default=[],placeholder="Todos",key="ud_fst")
    with c2: f_ti=st.multiselect("Tipo:",list({p["tipo"] for p in projetos_uni}),default=[],placeholder="Todos",key="ud_fti")
    with c3: f_nm=st.text_input("🔍 Buscar",placeholder="Nome...",key="ud_fn")

    pf=projetos_uni[:]
    if f_st: pf=[p for p in pf if p["status"] in f_st]
    if f_ti: pf=[p for p in pf if p["tipo"] in f_ti]
    if f_nm: pf=[p for p in pf if f_nm.lower() in p["nome"].lower()]

    atrasados=sum(1 for p in pf if linha_atrasada(p))
    if atrasados: st.error(f"🔴 {atrasados} projeto(s) com término vencido.")
    st.caption(f"{len(pf)} de {len(projetos_uni)} projetos")

    sc_map={"✓ Concluído":GREEN,"⏳ Em Execução":AMBER,"📝 Não iniciado":SILVER,"⚠️ Suspenso":RED}

    for p in pf:
        atrasado =linha_atrasada(p)
        concluido="Concluído" in str(p.get("status",""))
        extra    =is_extra_dre(p["tipo"])
        border_c =RED if atrasado else (GREEN if concluido else NAVY)
        sc       =sc_map.get(p["status"],SILVER)
        chk      =("✅" if p["check_a3"] else "⬜")+("✅" if p["check_memoria"] else "⬜")+("✅" if p["check_formalizado"] else "⬜")
        links    =get_links(p["id"])
        link_html=" ".join(
            f'<a href="{_html.escape(normalizar_url(lk["url"]), quote=True)}" target="_blank" '
            f'rel="noopener noreferrer" style="display:inline-block;background:#EEF0F3;color:{NAVY};'
            f'font-size:10px;padding:2px 8px;border-radius:8px;text-decoration:none;margin-right:4px;">'
            f'🔗 {_html.escape(lk["titulo"])}</a>' for lk in links) if links else ""
        prev_val =p["previsto_unidade"]
        cust_val =p["previsto_custos"]
        real_acum=sum(l["valor_real"] for l in get_lancamentos(proj_id=p["id"],ano=ano_sel)) if not extra else 0
        term_str =str(p.get("termino","") or "")[:7]
        txt_c    =f"color:{RED};" if atrasado else f"color:{NAVY};"
        vok_c    =GREEN if p.get("validador_ok")=="OK" else (RED if p.get("validador_ok")=="NOK" else AMBER)
        dre_b    =f'<span style="background:#F3E8FF;color:#9B59B6;font-size:9px;padding:1px 6px;border-radius:6px;font-weight:600;margin-left:6px;">↷ N/DRE</span>' if extra else f'<span style="background:#E6F4EC;color:{GREEN};font-size:9px;padding:1px 6px;border-radius:6px;font-weight:600;margin-left:6px;">✓ DRE</span>'
        ult_obs  = get_ultima_obs_custos(p["id"])
        ult_obs_html = (f'<div style="margin-top:5px;font-size:10px;color:#7A8394;">'
                         f'💬 {_html.escape(ult_obs["texto"])}</div>') if ult_obs else ""

        hc(f"""
<div style="border-left:4px solid {border_c};background:white;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:2px;box-shadow:0 1px 4px rgba(28,43,74,.06);">
<div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
<div style="flex:1;min-width:180px;">
<div style="font-size:10px;color:{SILVER};">{p['tipo']}{dre_b} · {p.get('va_ggf','—')}</div>
<div style="font-size:13px;font-weight:700;{txt_c}margin-top:2px;">#{p['id']} — {p['nome']}{'<span style="font-size:10px;color:#C8202E;margin-left:8px;">⚠️ ATRASADO</span>' if atrasado else ''}</div>
<div style="font-size:10px;color:{SILVER};margin-top:3px;">Resp: <b>{p.get('responsavel','—')}</b> · Término: <b style="color:{'#C8202E' if atrasado else '#333'};">{term_str or '—'}</b> · Custos: <b style="color:{vok_c};">{p.get('validador_ok','Pendente')}</b></div>
{f'<div style="margin-top:4px;">{link_html}</div>' if link_html else ''}
{ult_obs_html}
</div>
<div style="display:flex;gap:16px;align-items:center;flex-shrink:0;">
<div style="text-align:center;"><div style="font-size:9px;color:{SILVER};text-transform:uppercase;letter-spacing:.4px;">Prev. Unidade</div><div style="font-size:12px;font-weight:700;color:{AMBER};">{fmt_brl(prev_val)}</div></div>
{'<div style="text-align:center;"><div style="font-size:9px;color:'+SILVER+';text-transform:uppercase;letter-spacing:.4px;">Calc. Custos</div><div style="font-size:12px;font-weight:700;color:#F39C12;">'+fmt_brl(cust_val)+'</div></div>' if not extra else '<div style="text-align:center;"><div style="font-size:9px;color:#9B59B6;text-transform:uppercase;letter-spacing:.4px;">Extra DRE</div><div style="font-size:12px;font-weight:700;color:#9B59B6;">'+fmt_brl(prev_val)+'</div></div>'}
{'<div style="text-align:center;"><div style="font-size:9px;color:'+SILVER+';text-transform:uppercase;letter-spacing:.4px;">Real Acum.</div><div style="font-size:12px;font-weight:700;color:'+GREEN+';">'+fmt_brl(real_acum)+'</div></div>' if not extra else ''}
<div style="text-align:center;"><div style="font-size:9px;color:{SILVER};text-transform:uppercase;letter-spacing:.4px;">Status</div><div style="font-size:11px;font-weight:600;color:{sc};">{p['status']}</div></div>
<div style="text-align:center;"><div style="font-size:9px;color:{SILVER};text-transform:uppercase;letter-spacing:.4px;">A3·Mem·Form</div><div style="font-size:13px;">{chk}</div></div>
</div>
</div>
{f'<div style="margin-top:6px;font-size:10px;color:#555;background:#F9F9F9;padding:5px 10px;border-radius:6px;">📌 <b>Atribuição:</b> {p["atividade_atual"]}{(" — "+p["onde_parado"]) if p.get("onde_parado") else ""}</div>' if p.get('atividade_atual') else ''}
</div>""")

        if pode_ed:
            col_esp,col_edit=st.columns([10,2])
            with col_edit:
                if st.button(f"✏️ Editar #{p['id']}",key=f"btn_ed_{p['id']}",use_container_width=True):
                    st.session_state[f"edit_open_{p['id']}"]=not st.session_state.get(f"edit_open_{p['id']}",False)

            if st.session_state.get(f"edit_open_{p['id']}",False):
                with st.form(f"fe_{p['id']}"):
                    c1,c2,c3=st.columns(3)
                    with c1: tipo_e=st.selectbox("Tipo",TIPOS_PROJETO,index=TIPOS_PROJETO.index(p["tipo"]) if p["tipo"] in TIPOS_PROJETO else 0,key=f"ti_{p['id']}")
                    with c2: va_e=st.selectbox("VA/GGF",VA_GGF_OPTS,index=VA_GGF_OPTS.index(p["va_ggf"]) if p.get("va_ggf") in VA_GGF_OPTS else 0,key=f"va_{p['id']}")
                    with c3: resp_e=st.text_input("Responsável",value=p.get("responsavel",""),key=f"re_{p['id']}")
                    nome_e=st.text_input("Nome",value=p["nome"],key=f"nm_{p['id']}")
                    desc_e=st.text_area("Descrição",value=p.get("descricao","") or "",height=60,key=f"ds_{p['id']}")
                    st.markdown("**Datas e Valores**")
                    c1,c2,c3=st.columns(3)
                    with c1: inicio_e=st.date_input("Data de Início do Projeto",value=_parse_date(p.get("inicio")),key=f"ini_{p['id']}")
                    with c2: termino_e=st.date_input("Data de Fim do Projeto",value=_parse_date(p.get("termino")),key=f"trm_{p['id']}")
                    with c3: mpr_e=st.date_input("Ganho a partir de",value=_parse_date(p.get("mes_primeiro_retorno")),key=f"mpr_{p['id']}",help="Mês em que o projeto começa a gerar ganho financeiro — base do rateio em 12 meses.")
                    c1,c2=st.columns(2)
                    with c1: prev_e=st.number_input("Previsto Unidade (R$)",value=float(p["previsto_unidade"]),step=1000.0,format="%.2f",key=f"pv_{p['id']}")
                    with c2: status_e=st.selectbox("Status",STATUS_OPTS,index=STATUS_OPTS.index(p["status"]) if p["status"] in STATUS_OPTS else 0,key=f"st_{p['id']}")
                    st.markdown("**Acompanhamento** *(opcional)*")
                    c1,c2,c3=st.columns(3)
                    with c1: ativ_e=st.text_input("Atual Atribuição",value=p.get("atividade_atual","") or "",key=f"at_{p['id']}")
                    with c2: resp_ativ_e=st.text_input("Resp. Atribuição",value=p.get("onde_parado","") or "",key=f"ra_{p['id']}")
                    with c3: dt_e=st.text_input("Data Final",value=p.get("data_conclusao_ativ","") or "",placeholder="ex: 08/2026",key=f"dc_{p['id']}")
                    st.markdown("**Checklist**")
                    c1,c2,c3=st.columns(3)
                    with c1: ck_a3_e=st.checkbox("A3 e Plano",value=bool(p.get("check_a3")),key=f"ca_{p['id']}")
                    with c2: ck_mem_e=st.checkbox("Memória de Cálculo",value=bool(p.get("check_memoria")),key=f"cm_{p['id']}")
                    with c3: ck_for_e=st.checkbox("Formalizado com Custos",value=bool(p.get("check_formalizado")),key=f"cf_{p['id']}")
                    obs_e=st.text_area("Observações",value=p.get("obs","") or "",height=50,key=f"ob_{p['id']}")
                    st.markdown("---")
                    st.markdown("**🔵 Cost Control**")
                    if is_cc:
                        if links:
                            for lk in links: st.markdown(f"🔗 [{lk['titulo']}]({normalizar_url(lk['url'])})")
                        c1,c2=st.columns(2)
                        with c1:
                            val_ok=st.selectbox("Validador",["Pendente","OK","NOK"],index=["Pendente","OK","NOK"].index(p.get("validador_ok","Pendente")),key=f"vk_{p['id']}")
                            saving=st.number_input("Saving Validado (R$)",value=float(p.get("saving_validado",0)),step=1000.0,format="%.2f",key=f"sv_{p['id']}")
                        with c2:
                            prev_c=st.number_input("Valor Calculado Custos (R$)",value=float(p.get("previsto_custos",0)),step=1000.0,format="%.2f",key=f"pc_{p['id']}")
                    else:
                        val_ok=p.get("validador_ok","Pendente"); saving=p.get("saving_validado",0); prev_c=p.get("previsto_custos",0)
                        vok_color=GREEN if val_ok=="OK" else (RED if val_ok=="NOK" else AMBER)
                        hc(f'<div style="background:#F4F6FB;border-radius:8px;padding:10px 14px;font-size:11px;display:flex;gap:24px;"><div><span style="color:#8A9BB0;font-size:9px;text-transform:uppercase;">Validador</span><br><b style="color:{vok_color};">{val_ok}</b></div><div><span style="color:#8A9BB0;font-size:9px;text-transform:uppercase;">Calc. Custos</span><br><b>{fmt_brl(prev_c)}</b></div><div><span style="color:#8A9BB0;font-size:9px;text-transform:uppercase;">Saving</span><br><b style="color:#20C997;">{fmt_brl(saving)}</b></div></div>')
                    col_s,col_d=st.columns([4,1])
                    with col_s: salvar_e=st.form_submit_button("💾 Salvar",use_container_width=True)
                    with col_d: excluir_e=st.form_submit_button("🗑️",use_container_width=True)

                if salvar_e:
                    atualizar_projeto(p["id"],{"nome":nome_e,"tipo":tipo_e,"va_ggf":va_e,"responsavel":resp_e,"descricao":desc_e,"obs":obs_e,"status":status_e,"inicio":str(inicio_e),"termino":str(termino_e),"mes_primeiro_retorno":str(mpr_e),"previsto_unidade":prev_e,"previsto_custos":prev_c,"atividade_atual":ativ_e,"onde_parado":resp_ativ_e,"data_conclusao_ativ":dt_e,"check_a3":int(ck_a3_e),"check_memoria":int(ck_mem_e),"check_formalizado":int(ck_for_e),"validador_ok":val_ok,"saving_validado":saving},user["id"])
                    st.success("✅ Atualizado!"); st.session_state[f"edit_open_{p['id']}"]=False; st.rerun()
                if excluir_e:
                    deletar_projeto(p["id"]); st.success("🗑️ Excluído."); st.rerun()

                st.markdown("**🔗 Links**")
                lks=get_links(p["id"])
                for lk in lks:
                    c1,c2=st.columns([8,1])
                    with c1: st.markdown(f"🔗 [{lk['titulo']}]({normalizar_url(lk['url'])})")
                    with c2:
                        if st.button("✕",key=f"dlk_{lk['id']}"): del_link(lk["id"]); st.rerun()
                with st.form(f"flk_{p['id']}",clear_on_submit=True):
                    c1,c2=st.columns([2,4])
                    with c1: tit_lk=st.text_input("Nome",key=f"lt_{p['id']}")
                    with c2: url_lk=st.text_input("URL",key=f"lu_{p['id']}")
                    if st.form_submit_button("➕ Link"):
                        if tit_lk and url_lk: add_link(p["id"],tit_lk,url_lk); st.success("✅"); st.rerun()

        st.markdown("<hr style='margin:4px 0;border-color:#EEF0F3;'>",unsafe_allow_html=True)

    # Campeões
    camp=[p for p in listar_projetos(sel,incluir_campeao=True) if p["campeao"]]
    if camp:
        with st.expander(f"🏆 {len(camp)} Projeto(s) Campeão(ões)",expanded=False):
            for p in camp:
                st.markdown(f"🏆 **{p['nome']}** · {p['tipo']} · Campeão desde {str(p.get('campeao_em',''))[:7]} · Saving: {fmt_brl(p['saving_validado'])}")
