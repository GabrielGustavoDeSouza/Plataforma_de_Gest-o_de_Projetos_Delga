import streamlit as st
from datetime import date
from database import (listar_unidades, listar_projetos, get_projeto,
                      criar_projeto, atualizar_projeto, deletar_projeto,
                      get_links, add_link, del_link,
                      TIPOS_PROJETO, VA_GGF_OPTS, STATUS_OPTS)

def pode_editar(user, unidade_nome):
    if user["perfil"] == "admin": return True
    if user["perfil"] in ("facilitador","gestor"):
        return user.get("unidade") == unidade_nome
    return False

def linha_atrasada(p):
    """True se término passou e não está concluído."""
    concluido = "Concluído" in str(p.get("status",""))
    if concluido: return False
    termino = str(p.get("termino","")).strip()
    if not termino or termino in ("None","nan",""): return False
    try:
        ano, mes = int(termino[:4]), int(termino[5:7])
        hoje = date.today()
        return date(ano, mes, 28) < hoje
    except: return False

def render(user, **colors):
    NAVY=colors.get("NAVY","#1C2B4A"); TEAL=colors.get("TEAL","#20C997")
    GREEN=colors.get("GREEN","#1A7A3A"); AMBER=colors.get("AMBER","#E8A838")
    SILVER=colors.get("SILVER","#8A9BB0"); RED=colors.get("RED","#C8202E")

    st.markdown('<span class="st">Projetos</span>', unsafe_allow_html=True)

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    if user["perfil"] == "admin":
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np_uni")
    elif user["perfil"] in ("facilitador","gestor","cost_control"):
        unidade_sel = st.selectbox("Visualizando:", nomes_u, key="np_uni")
        if user.get("unidade") and unidade_sel != user.get("unidade"):
            st.info(f"👁️ Leitura — você edita apenas **{user.get('unidade')}**")
    else:
        unidade_sel = user.get("unidade","")
        if unidade_sel not in nomes_u:
            st.warning("Unidade não configurada."); return

    pode = pode_editar(user, unidade_sel)

    tab_novo, tab_lista, tab_links, tab_camp = st.tabs([
        "➕ Novo Projeto","📋 Lista & Edição","🔗 Links","🏆 Campeões"
    ])

    # ── Novo Projeto ──────────────────────────────────────────────────────────
    with tab_novo:
        if not pode:
            st.warning(f"⛔ Você só pode criar projetos em **{user.get('unidade','')}**.")
        else:
            with st.form("form_novo", clear_on_submit=True):
                st.markdown("**Identificação**")
                c1,c2,c3 = st.columns(3)
                with c1: tipo = st.selectbox("Tipo *", TIPOS_PROJETO)
                with c2: va   = st.selectbox("VA / GGF / Mat. Aux. *", VA_GGF_OPTS)
                with c3: resp = st.text_input("Responsável")

                nome = st.text_input("Nome do Projeto *")
                desc = st.text_area("Descrição / Objetivo", height=70)

                st.markdown("**Datas e Valores**")
                c1,c2,c3 = st.columns(3)
                with c1: inicio  = st.date_input("Início")
                with c2: termino = st.date_input("Término")
                with c3: mpr     = st.date_input("Mês do 1º Retorno *",
                    help="A partir daqui contam 12 meses de vigência do projeto.")

                c1,c2 = st.columns(2)
                with c1:
                    previsto = st.number_input("Valor Previsto (R$) *",
                        min_value=0.0, step=1000.0, format="%.2f",
                        help="Será distribuído em 12 meses a partir do 1º retorno.")
                with c2:
                    status = st.selectbox("Status", STATUS_OPTS)

                st.markdown("**Acompanhamento**")
                c1,c2 = st.columns(2)
                with c1: ativ    = st.text_input("Atividade em andamento (prevista no A3)")
                with c2: dt_ativ = st.date_input("Previsão de conclusão desta atividade")

                st.markdown("**Checklist**")
                c1,c2,c3 = st.columns(3)
                with c1: ck_a3  = st.checkbox("A3 e Plano desenvolvido")
                with c2: ck_mem = st.checkbox("Memória de Cálculo desenvolvida")
                with c3: ck_for = st.checkbox("Formalizado com Custos")

                obs = st.text_area("Observações", height=50)

                st.markdown("**Links (SharePoint / OneDrive)**")
                st.caption("Adicione links após salvar o projeto na aba 🔗 Links.")

                salvar = st.form_submit_button("💾 Cadastrar Projeto",
                                               use_container_width=True)

            if salvar:
                if not nome or previsto <= 0:
                    st.error("Preencha Nome e Valor Previsto.")
                else:
                    pid = criar_projeto(unidade_sel, {
                        "nome": nome, "tipo": tipo, "va_ggf": va,
                        "responsavel": resp, "descricao": desc, "obs": obs,
                        "inicio": str(inicio), "termino": str(termino),
                        "mes_primeiro_retorno": str(mpr),
                        "previsto_unidade": previsto, "status": status,
                        "atividade_atual": ativ,
                        "data_conclusao_ativ": str(dt_ativ),
                        "check_a3": ck_a3, "check_memoria": ck_mem,
                        "check_formalizado": ck_for,
                    }, user["id"])
                    st.success(f"✅ Projeto **{nome}** cadastrado! ID #{pid}")
                    st.rerun()

    # ── Lista & Edição ────────────────────────────────────────────────────────
    with tab_lista:
        projetos = listar_projetos(unidade_sel)
        if not projetos:
            st.info("Nenhum projeto cadastrado nesta unidade.")
        else:
            # Filtros
            c1,c2,c3 = st.columns([2,2,4])
            with c1:
                f_status = st.multiselect("Status:", list({p["status"] for p in projetos}),
                                          default=[], placeholder="Todos", key="ls_fst")
            with c2:
                f_tipo = st.multiselect("Tipo:", list({p["tipo"] for p in projetos}),
                                         default=[], placeholder="Todos", key="ls_fti")
            with c3:
                f_nome = st.text_input("🔍 Buscar", placeholder="Nome do projeto...",
                                        key="ls_fn")

            pf = projetos[:]
            if f_status: pf = [p for p in pf if p["status"] in f_status]
            if f_tipo:   pf = [p for p in pf if p["tipo"] in f_tipo]
            if f_nome:   pf = [p for p in pf if f_nome.lower() in p["nome"].lower()]

            hoje = date.today()

            # Tabela com cor vermelha para atrasados
            rows_html = ""
            for p in pf:
                atrasado = linha_atrasada(p)
                bg   = "background:#FFF5F5;" if atrasado else ""
                tc   = "color:#C8202E;" if atrasado else ""
                chk  = ("✅" if p["check_a3"] else "⬜") + \
                       ("✅" if p["check_memoria"] else "⬜") + \
                       ("✅" if p["check_formalizado"] else "⬜")
                sc_map = {"✓ Concluído":GREEN,"⏳ Em Execução":AMBER,
                          "📝 Não iniciado":SILVER,"⚠️ Suspenso":RED}
                sc = sc_map.get(p["status"], SILVER)
                rows_html += f"""<tr style="border-bottom:1px solid #EEF0F3;{bg}">
                  <td style="padding:8px 12px;font-size:11px;{tc}"><b>#{p['id']} {p['nome']}</b></td>
                  <td style="padding:8px 12px;font-size:10px;{tc}">{p['tipo']}</td>
                  <td style="padding:8px 12px;font-size:10px;{tc}">{p.get('va_ggf','—')}</td>
                  <td style="padding:8px 12px;font-size:10px;{tc}">{p.get('responsavel','—')}</td>
                  <td style="padding:8px 12px;text-align:right;font-size:11px;{tc}">
                    R$ {p['previsto_unidade']:,.0f}</td>
                  <td style="padding:8px 12px;font-size:10px;">
                    <span style="color:{sc};">{p['status']}</span></td>
                  <td style="padding:8px 12px;font-size:10px;">{chk}</td>
                  <td style="padding:8px 12px;font-size:10px;{tc}">
                    {p.get('atividade_atual','—') or '—'}</td>
                </tr>"""

            st.markdown(f"""
            <table style="width:100%;border-collapse:collapse;">
              <thead><tr style="background:{NAVY};">
                <th style="padding:9px 12px;color:white;font-size:11px;text-align:left;">Projeto</th>
                <th style="padding:9px 12px;color:white;font-size:11px;text-align:left;">Tipo</th>
                <th style="padding:9px 12px;color:white;font-size:11px;text-align:left;">VA/GGF</th>
                <th style="padding:9px 12px;color:white;font-size:11px;text-align:left;">Resp.</th>
                <th style="padding:9px 12px;color:white;font-size:11px;text-align:right;">Previsto</th>
                <th style="padding:9px 12px;color:white;font-size:11px;text-align:left;">Status</th>
                <th style="padding:9px 12px;color:white;font-size:11px;text-align:left;">A3/Mem/Form</th>
                <th style="padding:9px 12px;color:white;font-size:11px;text-align:left;">Atividade Atual</th>
              </tr></thead>
              <tbody>{rows_html}</tbody>
            </table>
            """, unsafe_allow_html=True)

            if atrasado_count := sum(1 for p in pf if linha_atrasada(p)):
                st.warning(f"⚠️ {atrasado_count} projeto(s) com término vencido e não concluído(s).")

            # Edição
            if pode:
                st.markdown("---")
                st.markdown("**✏️ Editar projeto**")
                opts = {f"#{p['id']} {p['nome']}": p for p in pf}
                if opts:
                    sel_p = st.selectbox("Selecionar:", list(opts.keys()), key="ed_sel")
                    p = opts[sel_p]

                    with st.form("form_editar"):
                        c1,c2,c3 = st.columns(3)
                        with c1:
                            tipo_e = st.selectbox("Tipo", TIPOS_PROJETO,
                                index=TIPOS_PROJETO.index(p["tipo"])
                                if p["tipo"] in TIPOS_PROJETO else 0)
                        with c2:
                            va_e = st.selectbox("VA/GGF", VA_GGF_OPTS,
                                index=VA_GGF_OPTS.index(p["va_ggf"])
                                if p.get("va_ggf") in VA_GGF_OPTS else 0)
                        with c3:
                            resp_e = st.text_input("Responsável",
                                                    value=p.get("responsavel",""))

                        nome_e = st.text_input("Nome", value=p["nome"])
                        desc_e = st.text_area("Descrição",
                                               value=p.get("descricao","") or "",
                                               height=60)

                        c1,c2 = st.columns(2)
                        with c1:
                            prev_e = st.number_input("Previsto Unidade (R$)",
                                value=float(p["previsto_unidade"]),
                                step=1000.0, format="%.2f")
                        with c2:
                            status_e = st.selectbox("Status", STATUS_OPTS,
                                index=STATUS_OPTS.index(p["status"])
                                if p["status"] in STATUS_OPTS else 0)

                        c1,c2 = st.columns(2)
                        with c1:
                            ativ_e = st.text_input("Atividade em andamento",
                                                    value=p.get("atividade_atual","") or "")
                        with c2:
                            dt_e = st.text_input("Previsão conclusão atividade",
                                                  value=p.get("data_conclusao_ativ","") or "")

                        st.markdown("**Checklist**")
                        c1,c2,c3 = st.columns(3)
                        with c1:
                            ck_a3_e  = st.checkbox("A3 e Plano",
                                                    value=bool(p.get("check_a3")))
                        with c2:
                            ck_mem_e = st.checkbox("Memória de Cálculo",
                                                    value=bool(p.get("check_memoria")))
                        with c3:
                            ck_for_e = st.checkbox("Formalizado com Custos",
                                                    value=bool(p.get("check_formalizado")))

                        obs_e = st.text_area("Observações",
                                              value=p.get("obs","") or "", height=50)

                        if user["perfil"] in ("admin","cost_control"):
                            st.markdown("---")
                            st.markdown("**🔵 Cost Control**")
                            c1,c2 = st.columns(2)
                            with c1:
                                val_ok = st.selectbox("Validador",
                                    ["Pendente","OK","NOK"],
                                    index=["Pendente","OK","NOK"].index(
                                        p.get("validador_ok","Pendente")))
                                saving = st.number_input("Saving Validado (R$)",
                                    value=float(p.get("saving_validado",0)),
                                    step=1000.0, format="%.2f")
                            with c2:
                                prev_c = st.number_input(
                                    "Valor Calculado por Custos (R$)",
                                    value=float(p.get("previsto_custos",0)),
                                    step=1000.0, format="%.2f",
                                    help="Substitui o previsto da unidade "
                                         "na curva de 12 meses")
                        else:
                            val_ok=p.get("validador_ok","Pendente")
                            saving=p.get("saving_validado",0)
                            prev_c=p.get("previsto_custos",0)

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
                            "responsavel":resp_e,"descricao":desc_e,"obs":obs_e,
                            "status":status_e,"previsto_unidade":prev_e,
                            "previsto_custos":prev_c,"atividade_atual":ativ_e,
                            "data_conclusao_ativ":dt_e,
                            "check_a3":int(ck_a3_e),"check_memoria":int(ck_mem_e),
                            "check_formalizado":int(ck_for_e),
                            "validador_ok":val_ok,"saving_validado":saving,
                        }, user["id"])
                        st.success("✅ Atualizado!"); st.rerun()

                    if excluir_e:
                        deletar_projeto(p["id"])
                        st.success("🗑️ Excluído."); st.rerun()

    # ── Links ─────────────────────────────────────────────────────────────────
    with tab_links:
        projetos = listar_projetos(unidade_sel)
        if not projetos:
            st.info("Nenhum projeto ainda.")
        else:
            opts2 = {f"#{p['id']} {p['nome']}": p for p in projetos}
            sel2  = st.selectbox("Projeto:", list(opts2.keys()), key="lk_sel")
            p2    = opts2[sel2]
            links = get_links(p2["id"])

            if links:
                for lk in links:
                    c1,c2 = st.columns([8,1])
                    with c1: st.markdown(f"🔗 [{lk['titulo']}]({lk['url']})")
                    with c2:
                        if pode and st.button("✕", key=f"dl_{lk['id']}"):
                            del_link(lk["id"]); st.rerun()
            else:
                st.info("Nenhum link ainda.")

            if pode:
                st.markdown("---")
                with st.form("form_link", clear_on_submit=True):
                    c1,c2 = st.columns([2,4])
                    with c1: titulo_lk = st.text_input("Nome (ex: A3, Memória)")
                    with c2: url_lk    = st.text_input("URL (SharePoint / OneDrive...)")
                    if st.form_submit_button("➕ Adicionar Link",
                                              use_container_width=True):
                        if titulo_lk and url_lk:
                            add_link(p2["id"], titulo_lk, url_lk)
                            st.success("✅ Link adicionado!"); st.rerun()

    # ── Campeões ──────────────────────────────────────────────────────────────
    with tab_camp:
        camp = [p for p in listar_projetos(unidade_sel, incluir_campeao=True)
                if p["campeao"]]
        if not camp:
            st.info("Nenhum campeão ainda. Troféu concedido após 12 meses de retorno.")
        else:
            for p in camp:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#FFD700,#FFA500);
                    border-radius:10px;padding:14px 18px;margin-bottom:10px;
                    display:flex;align-items:center;gap:12px;">
                  <span style="font-size:28px;">🏆</span>
                  <div>
                    <div style="font-weight:700;font-size:13px;color:#1C2B4A;">
                      {p['nome']}</div>
                    <div style="font-size:11px;color:#555;">
                      {p['tipo']} · Campeão desde
                      {str(p.get('campeao_em',''))[:7]} ·
                      Saving: R$ {p['saving_validado']:,.0f}
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
