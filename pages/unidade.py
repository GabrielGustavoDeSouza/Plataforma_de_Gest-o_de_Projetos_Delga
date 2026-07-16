import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
from database import (listar_unidades, kpis_unidade, alertas_pendentes,
                      verificar_campeoes, listar_projetos, atualizar_projeto,
                      deletar_projeto, get_links, add_link, del_link,
                      get_todas_metas, TIPOS_PROJETO, VA_GGF_OPTS,
                      STATUS_OPTS, MESES_PT)


def clean_html(html: str) -> str:
    """Remove indentação e quebras de linha 'soltas' de blocos HTML para
    evitar que o parser Markdown do Streamlit escape as tags <div> quando
    a linha começa com 4+ espaços (regra do CommonMark)."""
    lines = [line.strip() for line in html.strip().split("\n")]
    return "".join(lines)


def html_card(html: str):
    """Wrapper único para renderizar HTML sem risco do bug de indentação."""
    st.markdown(clean_html(html), unsafe_allow_html=True)


def fmt_mi(v):
    if abs(v)>=1e6: return f"R$ {v/1e6:.2f} Mi"
    if abs(v)>=1e3: return f"R$ {v/1e3:.1f} k"
    return f"R$ {v:,.0f}"

def fmt_brl(v): return f"R$ {v:,.0f}" if v else "—"

def linha_atrasada(p):
    if "Concluído" in str(p.get("status","")): return False
    t = str(p.get("termino","") or "").strip()
    if not t or t in ("None","nan",""): return False
    try: return date(int(t[:4]),int(t[5:7]),28) < date.today()
    except: return False

def render(user, **colors):
    NAVY=colors.get("NAVY","#1C2B4A"); GREEN=colors.get("GREEN","#1A7A3A")
    AMBER=colors.get("AMBER","#E8A838"); RED=colors.get("RED","#C8202E")
    TEAL=colors.get("TEAL","#20C997"); SILVER=colors.get("SILVER","#8A9BB0")

    verificar_campeoes()
    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    if user["perfil"] in ("admin","gestor","cost_control") and not user.get("unidade"):
        sel = st.selectbox("Unidade / Área:", nomes_u, key="ud_sel")
    else:
        sel = user.get("unidade","")
        if sel not in nomes_u:
            st.warning("Unidade não configurada."); return
        st.markdown(f"**{sel}**")

    pode_ed = user["perfil"] in ("admin","cost_control") or (
        user["perfil"] in ("facilitador","gestor") and user.get("unidade")==sel)
    is_cc = user["perfil"] in ("admin","cost_control")

    # Anos com meta
    anos_com_meta=[]
    for a in range(2026,2031):
        if any(m["valor"]>0 for m in get_todas_metas(a)):
            anos_com_meta.append(a)
    if not anos_com_meta: anos_com_meta=[datetime.now().year]
    if "ano_uni" not in st.session_state or \
       st.session_state["ano_uni"] not in anos_com_meta:
        st.session_state["ano_uni"] = anos_com_meta[-1]
    ano_sel = st.session_state["ano_uni"]

    if len(anos_com_meta)>1:
        cols_a=st.columns(len(anos_com_meta))
        for i,a in enumerate(anos_com_meta):
            with cols_a[i]:
                if st.button(str(a),key=f"ano_{a}",
                             type="primary" if a==ano_sel else "secondary",
                             use_container_width=True):
                    st.session_state["ano_uni"]=a; st.rerun()
        ano_sel=st.session_state["ano_uni"]

    kpi  = kpis_unidade(sel,ano_sel)
    meta = kpi["meta"] or 1
    pct  = kpi["real"]/meta*100 if kpi["meta"]>0 else 0
    pct_c= GREEN if pct>=60 else (AMBER if pct>=30 else RED)

    # KPI Cards
    html_card(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-l">Meta {ano_sel}</div>
        <div class="kpi-v">{fmt_mi(kpi['meta'])}</div>
      </div>
      <div class="kpi-card amber">
        <div class="kpi-l">Previsto (curva 12M)</div>
        <div class="kpi-v">{fmt_mi(kpi['previsto'])}</div>
        <div class="kpi-d">{kpi['n_projetos']} projetos</div>
      </div>
      <div class="kpi-card" style="border-left-color:{TEAL};">
        <div class="kpi-l">Saving Validado</div>
        <div class="kpi-v" style="color:{TEAL};">{fmt_mi(kpi['validado'])}</div>
      </div>
      <div class="kpi-card green">
        <div class="kpi-l">Retorno Real {ano_sel}</div>
        <div class="kpi-v">{fmt_mi(kpi['real'])}</div>
      </div>
      <div class="kpi-card" style="border-left-color:{pct_c};">
        <div class="kpi-l">% Atingimento</div>
        <div class="kpi-v" style="color:{pct_c};">{pct:.1f}%</div>
        <div class="kpi-d">Real / Meta</div>
      </div>
      <div class="kpi-card" style="border-left-color:#9B59B6;">
        <div class="kpi-l">Extra DRE</div>
        <div class="kpi-v" style="color:#9B59B6;">{fmt_mi(kpi.get('extra_dre',0))}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-l">Iniciativas</div>
        <div class="kpi-v">{kpi['n_projetos']}</div>
      </div>
    </div>
    """)

    alerts=alertas_pendentes(sel)
    if alerts:
        st.warning(f"⚠️ {len(alerts)} lançamento(s) pendente(s).")

    # Gráfico
    fig=go.Figure()
    fig.add_trace(go.Bar(x=MESES_PT,y=kpi["prev_mensal"],name="Previsto Mensal",
                         marker_color="#7EB3D8",opacity=0.6))
    fig.add_trace(go.Bar(x=MESES_PT,y=kpi["real_mensal"],name="Real Mensal",
                         marker_color="#52A97C",opacity=0.8))
    ap=ar=0; acum_p=[]; acum_r=[]
    for p,r in zip(kpi["prev_mensal"],kpi["real_mensal"]):
        ap+=p; ar+=r; acum_p.append(ap); acum_r.append(ar)
    fig.add_trace(go.Scatter(x=MESES_PT,y=acum_p,name="Acum. Previsto",
                             mode="lines+markers",
                             line=dict(color=NAVY,width=2,dash="dot"),
                             marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=MESES_PT,y=acum_r,name="Acum. Real",
                             mode="lines+markers",
                             line=dict(color=GREEN,width=2.5),
                             marker=dict(size=6)))
    if kpi["meta"]>0:
        fig.add_hline(y=kpi["meta"],line_dash="dash",line_color=RED,
                      annotation_text=f"Meta {fmt_mi(kpi['meta'])}",
                      annotation_position="right")
    fig.update_layout(
        barmode="group",bargap=0.25,
        xaxis=dict(showgrid=True,gridcolor="#F0F4F8"),
        yaxis=dict(tickprefix="R$ ",tickformat=",.0f",
                   showgrid=True,gridcolor="#F0F4F8"),
        legend=dict(orientation="h",y=1.05,x=0.5,xanchor="center"),
        margin=dict(l=60,r=20,t=40,b=30),height=300,
        paper_bgcolor="white",plot_bgcolor="white",
        hovermode="x unified",font=dict(family="Inter"))
    html_card(f'<p style="font-size:11px;font-weight:700;color:{NAVY};'
              f'text-transform:uppercase;letter-spacing:.7px;'
              f'border-bottom:2px solid #C8202E;padding-bottom:6px;'
              f'margin-bottom:14px;display:inline-block;">'
              f'Evolução Mensal — {sel} {ano_sel}</p>')
    st.plotly_chart(fig,use_container_width=True,
                    config={"displayModeBar":False})

    # ── Lista de Projetos ─────────────────────────────────────────────────────
    html_card(f'<p style="font-size:11px;font-weight:700;color:{NAVY};'
              f'text-transform:uppercase;letter-spacing:.7px;'
              f'border-bottom:2px solid #C8202E;padding-bottom:6px;'
              f'margin:20px 0 14px;display:inline-block;">'
              f'Projetos da Unidade</p>')

    projetos=listar_projetos(sel)

    c1,c2,c3=st.columns([2,2,4])
    with c1:
        f_st=st.multiselect("Status:",list({p["status"] for p in projetos}),
                             default=[],placeholder="Todos",key="ud_fst")
    with c2:
        f_ti=st.multiselect("Tipo:",list({p["tipo"] for p in projetos}),
                             default=[],placeholder="Todos",key="ud_fti")
    with c3:
        f_nm=st.text_input("🔍 Buscar",placeholder="Nome...",key="ud_fn")

    pf=projetos[:]
    if f_st: pf=[p for p in pf if p["status"] in f_st]
    if f_ti: pf=[p for p in pf if p["tipo"] in f_ti]
    if f_nm: pf=[p for p in pf if f_nm.lower() in p["nome"].lower()]

    atrasados=sum(1 for p in pf if linha_atrasada(p))
    if atrasados:
        st.error(f"🔴 {atrasados} projeto(s) com término vencido.")
    st.caption(f"{len(pf)} de {len(projetos)} projetos")

    sc_map={"✓ Concluído":GREEN,"⏳ Em Execução":AMBER,
            "📝 Não iniciado":SILVER,"⚠️ Suspenso":RED}

    for p in pf:
        atrasado = linha_atrasada(p)
        concluido= "Concluído" in str(p.get("status",""))
        border_c = RED if atrasado else (GREEN if concluido else NAVY)
        sc       = sc_map.get(p["status"],SILVER)
        chk      = ("✅" if p["check_a3"] else "⬜")+\
                   ("✅" if p["check_memoria"] else "⬜")+\
                   ("✅" if p["check_formalizado"] else "⬜")
        links    = get_links(p["id"])
        link_html= " ".join(
            f'<a href="{lk["url"]}" target="_blank" style="'
            f'display:inline-block;background:#EEF0F3;color:{NAVY};'
            f'font-size:10px;padding:2px 8px;border-radius:8px;'
            f'text-decoration:none;margin-right:4px;">🔗 {lk["titulo"]}</a>'
            for lk in links) if links else ""
        prev_val = p["previsto_custos"] if p["previsto_custos"]>0 \
                   else p["previsto_unidade"]
        term_str = str(p.get("termino","") or "")[:7]
        txt_c    = f"color:{RED};" if atrasado else f"color:{NAVY};"

        # Card
        html_card(f"""
<div style="border-left:4px solid {border_c};background:white;
     border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:2px;
     box-shadow:0 1px 4px rgba(28,43,74,.06);">
  <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
    <div style="flex:1;min-width:200px;">
      <div style="font-size:10px;color:{SILVER};">
        {p['tipo']} · {p.get('va_ggf','—')}</div>
      <div style="font-size:13px;font-weight:700;{txt_c}margin-top:2px;">
        #{p['id']} — {p['nome']}
        {'<span style="font-size:10px;color:#C8202E;margin-left:8px;">⚠️ ATRASADO</span>' if atrasado else ''}
      </div>
      <div style="font-size:10px;color:{SILVER};margin-top:3px;">
        Resp: <b>{p.get('responsavel','—')}</b> ·
        Término: <b style="color:{'#C8202E' if atrasado else '#333'};">{term_str or '—'}</b> ·
        Custos: <b style="color:{'#1A7A3A' if p.get('validador_ok')=='OK' else '#E8A838'};">
          {p.get('validador_ok','Pendente')}</b>
      </div>
      {f'<div style="margin-top:5px;">{link_html}</div>' if link_html else ''}
    </div>
    <div style="display:flex;gap:20px;align-items:center;flex-shrink:0;">
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
  {f'<div style="margin-top:6px;font-size:10px;color:#555;background:#F9F9F9;padding:5px 10px;border-radius:6px;">📌 <b>Atribuição:</b> {p["atividade_atual"]}{(" — "+p["onde_parado"]) if p.get("onde_parado") else ""}</div>' if p.get('atividade_atual') else ''}
</div>""")

        # Expander edição
        if pode_ed:
            with st.expander(f"✏️ Editar #{p['id']} — {p['nome'][:35]}",
                             expanded=False):
                with st.form(f"fe_{p['id']}"):
                    c1,c2,c3=st.columns(3)
                    with c1:
                        tipo_e=st.selectbox("Tipo",TIPOS_PROJETO,
                            index=TIPOS_PROJETO.index(p["tipo"])
                            if p["tipo"] in TIPOS_PROJETO else 0,
                            key=f"ti_{p['id']}")
                    with c2:
                        va_e=st.selectbox("VA/GGF",VA_GGF_OPTS,
                            index=VA_GGF_OPTS.index(p["va_ggf"])
                            if p.get("va_ggf") in VA_GGF_OPTS else 0,
                            key=f"va_{p['id']}")
                    with c3:
                        resp_e=st.text_input("Responsável",
                            value=p.get("responsavel",""),key=f"re_{p['id']}")
                    nome_e=st.text_input("Nome",value=p["nome"],key=f"nm_{p['id']}")
                    desc_e=st.text_area("Descrição",
                        value=p.get("descricao","") or "",
                        height=60,key=f"ds_{p['id']}")

                    c1,c2=st.columns(2)
                    with c1:
                        prev_e=st.number_input("Previsto Unidade (R$)",
                            value=float(p["previsto_unidade"]),
                            step=1000.0,format="%.2f",key=f"pv_{p['id']}")
                    with c2:
                        status_e=st.selectbox("Status",STATUS_OPTS,
                            index=STATUS_OPTS.index(p["status"])
                            if p["status"] in STATUS_OPTS else 0,
                            key=f"st_{p['id']}")

                    st.markdown("**Acompanhamento** *(opcional)*")
                    c1,c2,c3=st.columns(3)
                    with c1:
                        ativ_e=st.text_input("Atual Atribuição",
                            value=p.get("atividade_atual","") or "",
                            key=f"at_{p['id']}")
                    with c2:
                        resp_ativ_e=st.text_input("Resp. Atribuição",
                            value=p.get("onde_parado","") or "",
                            key=f"ra_{p['id']}")
                    with c3:
                        dt_e=st.text_input("Data Final Atribuição",
                            value=p.get("data_conclusao_ativ","") or "",
                            placeholder="ex: 08/2026",
                            key=f"dc_{p['id']}")

                    st.markdown("**Checklist**")
                    c1,c2,c3=st.columns(3)
                    with c1:
                        ck_a3_e=st.checkbox("A3 e Plano",
                            value=bool(p.get("check_a3")),key=f"ca_{p['id']}")
                    with c2:
                        ck_mem_e=st.checkbox("Memória de Cálculo",
                            value=bool(p.get("check_memoria")),key=f"cm_{p['id']}")
                    with c3:
                        ck_for_e=st.checkbox("Formalizado com Custos",
                            value=bool(p.get("check_formalizado")),key=f"cf_{p['id']}")

                    obs_e=st.text_area("Observações",
                        value=p.get("obs","") or "",height=50,key=f"ob_{p['id']}")

                    if is_cc:
                        st.markdown("---")
                        st.markdown("**🔵 Cost Control**")
                        if links:
                            for lk in links:
                                st.markdown(f"🔗 [{lk['titulo']}]({lk['url']})")
                        c1,c2=st.columns(2)
                        with c1:
                            val_ok=st.selectbox("Validador",
                                ["Pendente","OK","NOK"],
                                index=["Pendente","OK","NOK"].index(
                                    p.get("validador_ok","Pendente")),
                                key=f"vk_{p['id']}")
                            saving=st.number_input("Saving Validado (R$)",
                                value=float(p.get("saving_validado",0)),
                                step=1000.0,format="%.2f",key=f"sv_{p['id']}")
                        with c2:
                            prev_c=st.number_input("Valor Calculado Custos (R$)",
                                value=float(p.get("previsto_custos",0)),
                                step=1000.0,format="%.2f",key=f"pc_{p['id']}")
                    else:
                        val_ok=p.get("validador_ok","Pendente")
                        saving=p.get("saving_validado",0)
                        prev_c=p.get("previsto_custos",0)

                    col_s,col_d=st.columns([4,1])
                    with col_s:
                        salvar_e=st.form_submit_button("💾 Salvar",
                                                        use_container_width=True)
                    with col_d:
                        excluir_e=st.form_submit_button("🗑️",
                                                         use_container_width=True)

                if salvar_e:
                    atualizar_projeto(p["id"],{
                        "nome":nome_e,"tipo":tipo_e,"va_ggf":va_e,
                        "responsavel":resp_e,"descricao":desc_e,"obs":obs_e,
                        "status":status_e,"previsto_unidade":prev_e,
                        "previsto_custos":prev_c,
                        "atividade_atual":ativ_e,
                        "onde_parado":resp_ativ_e,
                        "data_conclusao_ativ":dt_e,
                        "check_a3":int(ck_a3_e),
                        "check_memoria":int(ck_mem_e),
                        "check_formalizado":int(ck_for_e),
                        "validador_ok":val_ok,
                        "saving_validado":saving,
                    },user["id"])
                    st.success("✅ Atualizado!"); st.rerun()

                if excluir_e:
                    deletar_projeto(p["id"])
                    st.success("🗑️ Excluído."); st.rerun()

                st.markdown("**🔗 Links**")
                lks=get_links(p["id"])
                for lk in lks:
                    c1,c2=st.columns([8,1])
                    with c1: st.markdown(f"🔗 [{lk['titulo']}]({lk['url']})")
                    with c2:
                        if st.button("✕",key=f"dlk_{lk['id']}"):
                            del_link(lk["id"]); st.rerun()
                with st.form(f"flk_{p['id']}",clear_on_submit=True):
                    c1,c2=st.columns([2,4])
                    with c1: tit_lk=st.text_input("Nome",key=f"lt_{p['id']}")
                    with c2: url_lk=st.text_input("URL",key=f"lu_{p['id']}")
                    if st.form_submit_button("➕ Adicionar Link"):
                        if tit_lk and url_lk:
                            add_link(p["id"],tit_lk,url_lk)
                            st.success("✅"); st.rerun()

    # Campeões
    camp=[p for p in listar_projetos(sel,incluir_campeao=True) if p["campeao"]]
    if camp:
        with st.expander(f"🏆 {len(camp)} Projeto(s) Campeão(ões)",expanded=False):
            for p in camp:
                html_card(f"""
<div style="background:linear-gradient(135deg,#FFD700,#FFA500);
     border-radius:8px;padding:10px 16px;margin-bottom:6px;
     display:flex;align-items:center;gap:10px;">
  <span style="font-size:20px;">🏆</span>
  <div>
    <div style="font-weight:700;font-size:12px;color:#1C2B4A;">{p['nome']}</div>
    <div style="font-size:10px;color:#555;">
      {p['tipo']} · Campeão desde {str(p.get('campeao_em',''))[:7]} ·
      Saving: R$ {p['saving_validado']:,.0f}</div>
  </div>
</div>""")
