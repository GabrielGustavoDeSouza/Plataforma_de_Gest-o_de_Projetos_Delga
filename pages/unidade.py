import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
from database import (listar_unidades, kpis_unidade, alertas_pendentes,
                      verificar_campeoes, listar_projetos, atualizar_projeto,
                      deletar_projeto, get_links, add_link, del_link,
                      TIPOS_PROJETO, VA_GGF_OPTS, STATUS_OPTS, MESES_PT)

def fmt_mi(v): return f"R$ {v/1e6:.2f} Mi" if abs(v)>=1e6 else f"R$ {v/1e3:.1f} k"
def fmt_brl(v): return f"R$ {v:,.0f}" if v else "—"

def linha_atrasada(p):
    concluido = "Concluído" in str(p.get("status",""))
    if concluido: return False
    termino = str(p.get("termino","") or "").strip()
    if not termino or termino in ("None","nan",""): return False
    try:
        ano, mes = int(termino[:4]), int(termino[5:7])
        return date(ano, mes, 28) < date.today()
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

    pode_editar = user["perfil"] in ("admin","cost_control") or (
        user["perfil"] in ("facilitador","gestor") and user.get("unidade") == sel)
    is_cc = user["perfil"] in ("admin","cost_control")

    # Botões de ano
    anos = list(range(2025, 2030))
    if "ano_uni" not in st.session_state:
        st.session_state["ano_uni"] = datetime.now().year
    ano_sel = st.session_state["ano_uni"]
    cols_a  = st.columns(len(anos))
    for i,a in enumerate(anos):
        with cols_a[i]:
            if st.button(str(a), key=f"ano_{a}",
                         type="primary" if a==ano_sel else "secondary",
                         use_container_width=True):
                st.session_state["ano_uni"] = a; st.rerun()
    ano_sel = st.session_state["ano_uni"]

    kpi  = kpis_unidade(sel, ano_sel)
    meta = kpi["meta"] or 1
    pct  = kpi["real"] / meta * 100

    # ── KPI Cards ─────────────────────────────────────────────────────────────
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
      <div class="kpi-card" style="border-left-color:#9B59B6;">
        <div class="kpi-l">Extra DRE</div>
        <div class="kpi-v" style="color:#9B59B6;">{fmt_mi(kpi.get('extra_dre',0))}</div>
      </div>
      <div class="kpi-card red">
        <div class="kpi-l">GAP para Meta</div>
        <div class="kpi-v">{fmt_mi(max(meta-kpi['real'],0))}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-l">Iniciativas</div>
        <div class="kpi-v">{kpi['n_projetos']}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Alertas
    alerts = alertas_pendentes(sel)
    if alerts:
        st.warning(f"⚠️ {len(alerts)} lançamento(s) de meses anteriores pendente(s).")

    # ── Gráfico ───────────────────────────────────────────────────────────────
    fig = go.Figure()
    fig.add_trace(go.Bar(x=MESES_PT, y=kpi["prev_mensal"], name="Previsto Mensal",
                         marker_color="#7EB3D8", opacity=0.6))
    fig.add_trace(go.Bar(x=MESES_PT, y=kpi["real_mensal"], name="Real Mensal",
                         marker_color="#52A97C", opacity=0.8))
    acum_p=[]; acum_r=[]; ap=ar=0
    for p,r in zip(kpi["prev_mensal"],kpi["real_mensal"]):
        ap+=p; ar+=r; acum_p.append(ap); acum_r.append(ar)
    fig.add_trace(go.Scatter(x=MESES_PT, y=acum_p, name="Acum. Previsto",
                             mode="lines+markers",
                             line=dict(color=NAVY,width=2,dash="dot"),
                             marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=MESES_PT, y=acum_r, name="Acum. Real",
                             mode="lines+markers",
                             line=dict(color=GREEN,width=2.5),
                             marker=dict(size=6)))
    fig.add_hline(y=meta, line_dash="dash", line_color=RED,
                  annotation_text=f"Meta {fmt_mi(meta)}",
                  annotation_position="right")
    fig.update_layout(
        barmode="group", bargap=0.25,
        xaxis=dict(showgrid=True,gridcolor="#F0F4F8"),
        yaxis=dict(tickprefix="R$ ",tickformat=",.0f",
                   showgrid=True,gridcolor="#F0F4F8"),
        legend=dict(orientation="h",y=1.05,x=0.5,xanchor="center"),
        margin=dict(l=60,r=20,t=40,b=30),height=300,
        paper_bgcolor="white",plot_bgcolor="white",
        hovermode="x unified",font=dict(family="Inter"),
    )
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown(f'<span class="st">Evolução Mensal — {sel} {ano_sel}</span>',
                unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Lista de Projetos ─────────────────────────────────────────────────────
    st.markdown('<div class="sc">', unsafe_allow_html=True)
    st.markdown('<span class="st">Projetos da Unidade</span>',
                unsafe_allow_html=True)

    projetos = listar_projetos(sel)

    # Filtros
    c1,c2,c3 = st.columns([2,2,4])
    with c1:
        f_status = st.multiselect("Status:",
                                   list({p["status"] for p in projetos}),
                                   default=[], placeholder="Todos",
                                   key="ud_fst")
    with c2:
        f_tipo = st.multiselect("Tipo:",
                                 list({p["tipo"] for p in projetos}),
                                 default=[], placeholder="Todos",
                                 key="ud_fti")
    with c3:
        f_nome = st.text_input("🔍 Buscar projeto",
                                placeholder="Nome do projeto...",
                                key="ud_fn")

    pf = projetos[:]
    if f_status: pf = [p for p in pf if p["status"] in f_status]
    if f_tipo:   pf = [p for p in pf if p["tipo"] in f_tipo]
    if f_nome:   pf = [p for p in pf if f_nome.lower() in p["nome"].lower()]

    atrasados = sum(1 for p in pf if linha_atrasada(p))
    if atrasados:
        st.error(f"🔴 {atrasados} projeto(s) com término vencido e não concluído.")

    st.markdown(f"<p style='font-size:11px;color:{SILVER};margin:4px 0 10px;'>"
                f"<b>{len(pf)}</b> de {len(projetos)} projetos</p>",
                unsafe_allow_html=True)

    # Projetos em cards expansíveis
    for p in pf:
        atrasado  = linha_atrasada(p)
        concluido = "Concluído" in str(p.get("status",""))
        border_c  = RED if atrasado else (GREEN if concluido else NAVY)
        txt_c     = RED if atrasado else NAVY
        sc_map    = {"✓ Concluído": GREEN, "⏳ Em Execução": AMBER,
                     "📝 Não iniciado": SILVER, "⚠️ Suspenso": RED}
        sc        = sc_map.get(p["status"], SILVER)
        chk       = ("✅" if p["check_a3"] else "⬜") + \
                    ("✅" if p["check_memoria"] else "⬜") + \
                    ("✅" if p["check_formalizado"] else "⬜")
        links     = get_links(p["id"])
        link_html = " ".join(
            f'<a href="{lk["url"]}" target="_blank" style="'
            f'display:inline-block;background:#EEF0F3;color:{NAVY};'
            f'font-size:10px;padding:2px 8px;border-radius:8px;'
            f'text-decoration:none;margin-right:4px;">🔗 {lk["titulo"]}</a>'
            for lk in links) if links else \
            f'<span style="color:#ccc;font-size:10px;">Sem links</span>'

        prev_val = p["previsto_custos"] if p["previsto_custos"]>0 \
                   else p["previsto_unidade"]

        # Card resumo
        st.markdown(f"""
        <div style="border-left:4px solid {border_c};background:white;
             border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:4px;
             box-shadow:0 1px 4px rgba(28,43,74,.06);">
          <div style="display:flex;align-items:flex-start;gap:12px;">
            <div style="flex:1;">
              <div style="font-size:12px;font-weight:700;color:{txt_c};">
                #{p['id']} — {p['nome']}
                {'<span style="color:#C8202E;font-size:10px;margin-left:6px;">⚠️ ATRASADO</span>' if atrasado else ''}
              </div>
              <div style="font-size:10px;color:{SILVER};margin-top:3px;">
                {p['tipo']} &nbsp;·&nbsp; {p.get('va_ggf','—')} &nbsp;·&nbsp;
                Resp: <b>{p.get('responsavel','—')}</b> &nbsp;·&nbsp;
                Término: <b style="color:{RED if atrasado else '#333'};">
                  {str(p.get('termino','—') or '—')[:7]}</b>
              </div>
              <div style="margin-top:6px;">{link_html}</div>
            </div>
            <div style="display:flex;gap:16px;align-items:center;flex-shrink:0;">
              <div style="text-align:center;">
                <div style="font-size:9px;color:{SILVER};text-transform:uppercase;
                     letter-spacing:.4px;">Previsto</div>
                <div style="font-size:12px;font-weight:700;color:{AMBER};">
                  {fmt_brl(prev_val)}</div>
              </div>
              <div style="text-align:center;">
                <div style="font-size:9px;color:{SILVER};text-transform:uppercase;
                     letter-spacing:.4px;">Validado</div>
                <div style="font-size:12px;font-weight:700;color:{TEAL};">
                  {fmt_brl(p['saving_validado'])}</div>
              </div>
              <div style="text-align:center;">
                <div style="font-size:9px;color:{SILVER};text-transform:uppercase;
                     letter-spacing:.4px;">Status</div>
                <div style="font-size:11px;font-weight:600;color:{sc};">
                  {p['status']}</div>
              </div>
              <div style="text-align:center;">
                <div style="font-size:9px;color:{SILVER};text-transform:uppercase;
                     letter-spacing:.4px;">A3/Mem/Form</div>
                <div style="font-size:13px;">{chk}</div>
              </div>
            </div>
          </div>
          {f'<div style="margin-top:8px;font-size:10px;color:#555;background:#F9F9F9;padding:6px 10px;border-radius:6px;">📌 <b>Atividade:</b> {p["atividade_atual"]}</div>' if p.get('atividade_atual') else ''}
        </div>
        """, unsafe_allow_html=True)

        # Painel de edição expansível
        if pode_editar:
            with st.expander(f"✏️ Editar #{p['id']} — {p['nome'][:40]}",
                             expanded=False):
                with st.form(f"form_ed_{p['id']}"):
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        tipo_e = st.selectbox("Tipo", TIPOS_PROJETO,
                            index=TIPOS_PROJETO.index(p["tipo"])
                            if p["tipo"] in TIPOS_PROJETO else 0,
                            key=f"ti_{p['id']}")
                    with c2:
                        va_e = st.selectbox("VA/GGF", VA_GGF_OPTS,
                            index=VA_GGF_OPTS.index(p["va_ggf"])
                            if p.get("va_ggf") in VA_GGF_OPTS else 0,
                            key=f"va_{p['id']}")
                    with c3:
                        resp_e = st.text_input("Responsável",
                            value=p.get("responsavel",""),
                            key=f"re_{p['id']}")

                    nome_e = st.text_input("Nome", value=p["nome"],
                                            key=f"nm_{p['id']}")

                    c1,c2 = st.columns(2)
                    with c1:
                        prev_e = st.number_input("Previsto Unidade (R$)",
                            value=float(p["previsto_unidade"]),
                            step=1000.0, format="%.2f",
                            key=f"pv_{p['id']}")
                    with c2:
                        status_e = st.selectbox("Status", STATUS_OPTS,
                            index=STATUS_OPTS.index(p["status"])
                            if p["status"] in STATUS_OPTS else 0,
                            key=f"st_{p['id']}")

                    c1,c2 = st.columns(2)
                    with c1:
                        ativ_e = st.text_input("Atividade em andamento",
                            value=p.get("atividade_atual","") or "",
                            key=f"at_{p['id']}")
                    with c2:
                        dt_e = st.text_input("Previsão conclusão atividade",
                            value=p.get("data_conclusao_ativ","") or "",
                            key=f"dc_{p['id']}")

                    c1,c2 = st.columns(2)
                    with c1:
                        onde_e = st.text_input("Onde Parado",
                            value=p.get("onde_parado","") or "",
                            key=f"on_{p['id']}")
                    with c2:
                        dlib_e = st.text_input("Previsão Liberação",
                            value=p.get("data_lib","") or "",
                            key=f"dl_{p['id']}")

                    st.markdown("**Checklist**")
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        ck_a3_e = st.checkbox("A3 e Plano",
                            value=bool(p.get("check_a3")),
                            key=f"ca_{p['id']}")
                    with c2:
                        ck_mem_e = st.checkbox("Memória de Cálculo",
                            value=bool(p.get("check_memoria")),
                            key=f"cm_{p['id']}")
                    with c3:
                        ck_for_e = st.checkbox("Formalizado com Custos",
                            value=bool(p.get("check_formalizado")),
                            key=f"cf_{p['id']}")

                    obs_e = st.text_area("Observações",
                        value=p.get("obs","") or "", height=50,
                        key=f"ob_{p['id']}")

                    # Cost Control
                    if is_cc:
                        st.markdown("---")
                        st.markdown("**🔵 Cost Control**")
                        # Links para Cost Control estudar
                        if links:
                            st.markdown("**Evidências do projeto:**")
                            for lk in links:
                                st.markdown(
                                    f"🔗 [{lk['titulo']}]({lk['url']})")
                        c1,c2 = st.columns(2)
                        with c1:
                            val_ok = st.selectbox("Validador Custos",
                                ["Pendente","OK","NOK"],
                                index=["Pendente","OK","NOK"].index(
                                    p.get("validador_ok","Pendente")),
                                key=f"vk_{p['id']}")
                            saving = st.number_input("Saving Validado (R$)",
                                value=float(p.get("saving_validado",0)),
                                step=1000.0, format="%.2f",
                                key=f"sv_{p['id']}")
                        with c2:
                            prev_c = st.number_input(
                                "Valor Calculado por Custos (R$)",
                                value=float(p.get("previsto_custos",0)),
                                step=1000.0, format="%.2f",
                                help="Substitui o previsto na curva de 12 meses",
                                key=f"pc_{p['id']}")
                    else:
                        val_ok = p.get("validador_ok","Pendente")
                        saving = p.get("saving_validado",0)
                        prev_c = p.get("previsto_custos",0)

                    col_s,col_d = st.columns([4,1])
                    with col_s:
                        salvar_e = st.form_submit_button("💾 Salvar",
                            use_container_width=True)
                    with col_d:
                        excluir_e = st.form_submit_button("🗑️",
                            use_container_width=True)

                if salvar_e:
                    atualizar_projeto(p["id"], {
                        "nome":nome_e,"tipo":tipo_e,"va_ggf":va_e,
                        "responsavel":resp_e,"obs":obs_e,
                        "status":status_e,"previsto_unidade":prev_e,
                        "previsto_custos":prev_c,
                        "atividade_atual":ativ_e,
                        "data_conclusao_ativ":dt_e,
                        "onde_parado":onde_e,"data_lib":dlib_e,
                        "check_a3":int(ck_a3_e),
                        "check_memoria":int(ck_mem_e),
                        "check_formalizado":int(ck_for_e),
                        "validador_ok":val_ok,
                        "saving_validado":saving,
                    }, user["id"])
                    st.success("✅ Atualizado!"); st.rerun()

                if excluir_e:
                    deletar_projeto(p["id"])
                    st.success("🗑️ Excluído."); st.rerun()

                # Links dentro do expander
                st.markdown("**🔗 Links do projeto**")
                lks = get_links(p["id"])
                for lk in lks:
                    c1,c2 = st.columns([8,1])
                    with c1:
                        st.markdown(f"🔗 [{lk['titulo']}]({lk['url']})")
                    with c2:
                        if st.button("✕", key=f"dlk_{lk['id']}"):
                            del_link(lk["id"]); st.rerun()
                with st.form(f"form_lk_{p['id']}", clear_on_submit=True):
                    c1,c2 = st.columns([2,4])
                    with c1:
                        tit_lk = st.text_input("Nome",
                            key=f"lt_{p['id']}")
                    with c2:
                        url_lk = st.text_input("URL",
                            key=f"lu_{p['id']}")
                    if st.form_submit_button("➕ Adicionar Link"):
                        if tit_lk and url_lk:
                            add_link(p["id"], tit_lk, url_lk)
                            st.success("✅ Link adicionado!"); st.rerun()

    # ── Campeões (discreto) ───────────────────────────────────────────────────
    camp = [p for p in listar_projetos(sel, incluir_campeao=True)
            if p["campeao"]]
    if camp:
        with st.expander(f"🏆 {len(camp)} Projeto(s) Campeão(ões)",
                         expanded=False):
            for p in camp:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#FFD700,#FFA500);
                    border-radius:8px;padding:10px 16px;margin-bottom:6px;
                    display:flex;align-items:center;gap:10px;">
                  <span style="font-size:20px;">🏆</span>
                  <div>
                    <div style="font-weight:700;font-size:12px;color:#1C2B4A;">
                      {p['nome']}</div>
                    <div style="font-size:10px;color:#555;">
                      {p['tipo']} · Campeão desde
                      {str(p.get('campeao_em',''))[:7]} ·
                      Saving: R$ {p['saving_validado']:,.0f}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
