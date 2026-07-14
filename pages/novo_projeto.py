"""pages/novo_projeto.py — Cadastro, edição e links de projetos"""
import streamlit as st
from datetime import datetime
from database import (listar_unidades, listar_projetos, get_projeto,
                      criar_projeto, atualizar_projeto, deletar_projeto,
                      get_links, add_link, del_link,
                      TIPOS_PROJETO, VA_GGF_OPTS, STATUS_OPTS)

NAVY="#1C2B4A"; RED="#C8202E"; GREEN="#1A7A3A"; AMBER="#E8A838"; SILVER="#8A9BB0"

def render(user, **colors):
    st.markdown('<span class="st">Projetos — Cadastro e Manutenção</span>', unsafe_allow_html=True)

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    if user["perfil"] in ("admin","gestor") and not user.get("unidade"):
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np_uni")
    else:
        unidade_sel = user.get("unidade","")
        if unidade_sel not in nomes_u:
            st.warning("Unidade não encontrada."); return
        st.markdown(f"**Unidade:** {unidade_sel}")

    tab_novo, tab_editar, tab_links, tab_campeoes = st.tabs([
        "➕ Novo Projeto","✏️ Editar / Status","🔗 Links & Evidências","🏆 Campeões"
    ])

    # ── Novo Projeto ──────────────────────────────────────────────────────────
    with tab_novo:
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
                                              help="Mês em que o projeto começa a gerar ganho")

            c1,c2 = st.columns(2)
            with c1: previsto = st.number_input("Valor Previsto pela Unidade (R$) *",
                                                 min_value=0.0, step=1000.0, format="%.2f")
            with c2: status   = st.selectbox("Status", STATUS_OPTS)

            st.markdown("**Acompanhamento**")
            c1,c2 = st.columns(2)
            with c1: ativ   = st.text_input("Atividade em andamento (prevista no A3)")
            with c2: dt_ativ= st.date_input("Previsão conclusão desta atividade")

            obs = st.text_area("Observações", height=50)
            salvar = st.form_submit_button("💾 Cadastrar Projeto", use_container_width=True)

        if salvar:
            if not nome or previsto <= 0:
                st.error("Preencha Nome e Valor Previsto.")
            else:
                pid = criar_projeto(unidade_sel, {
                    "nome": nome, "tipo": tipo, "va_ggf": va,
                    "responsavel": resp, "descricao": desc, "obs": obs,
                    "inicio": str(inicio), "termino": str(termino),
                    "mes_primeiro_retorno": str(mpr),
                    "previsto_unidade": previsto,
                    "status": status,
                    "atividade_atual": ativ,
                    "data_conclusao_ativ": str(dt_ativ),
                }, user["id"])
                st.success(f"✅ Projeto **{nome}** cadastrado! ID #{pid}")
                st.rerun()

    # ── Editar ────────────────────────────────────────────────────────────────
    with tab_editar:
        projetos = listar_projetos(unidade_sel)
        if not projetos:
            st.info("Nenhum projeto cadastrado."); 
        else:
            opts = {f"#{p['id']} [{p['tipo'][:6]}] {p['nome']}": p for p in projetos}
            sel_nome = st.selectbox("Selecionar:", list(opts.keys()), key="ed_sel")
            p = opts[sel_nome]

            with st.form("form_editar"):
                st.markdown("**Dados do Projeto**")
                c1,c2,c3 = st.columns(3)
                with c1: tipo_e = st.selectbox("Tipo", TIPOS_PROJETO,
                    index=TIPOS_PROJETO.index(p["tipo"]) if p["tipo"] in TIPOS_PROJETO else 0)
                with c2: va_e   = st.selectbox("VA/GGF", VA_GGF_OPTS,
                    index=VA_GGF_OPTS.index(p["va_ggf"]) if p.get("va_ggf") in VA_GGF_OPTS else 0)
                with c3: resp_e = st.text_input("Responsável", value=p.get("responsavel",""))

                nome_e = st.text_input("Nome", value=p["nome"])
                desc_e = st.text_area("Descrição", value=p.get("descricao","") or "", height=60)

                st.markdown("**Datas e Valores**")
                c1,c2 = st.columns(2)
                with c1: prev_e = st.number_input("Previsto Unidade (R$)",
                    value=float(p["previsto_unidade"]), step=1000.0, format="%.2f")
                with c2: status_e = st.selectbox("Status", STATUS_OPTS,
                    index=STATUS_OPTS.index(p["status"]) if p["status"] in STATUS_OPTS else 0)

                c1,c2 = st.columns(2)
                with c1: onde_e = st.text_input("Onde Parado", value=p.get("onde_parado","") or "")
                with c2: dlib_e = st.text_input("Previsão Liberação", value=p.get("data_lib","") or "")

                st.markdown("**Acompanhamento**")
                c1,c2 = st.columns(2)
                with c1: ativ_e = st.text_input("Atividade em andamento",
                                                  value=p.get("atividade_atual","") or "")
                with c2: dt_e   = st.text_input("Previsão conclusão atividade",
                                                  value=p.get("data_conclusao_ativ","") or "")
                obs_e = st.text_area("Observações", value=p.get("obs","") or "", height=50)

                # Cost Control fields
                if user["perfil"] in ("admin","cost_control"):
                    st.markdown("---")
                    st.markdown("**🔵 Cost Control**")
                    c1,c2,c3 = st.columns(3)
                    with c1: ck_a3  = st.checkbox("✅ A3 e Plano desenvolvido", value=bool(p.get("check_a3")))
                    with c2: ck_mem = st.checkbox("✅ Memória de Cálculo desenvolvida", value=bool(p.get("check_memoria")))
                    with c3: ck_for = st.checkbox("✅ Formalizado com Custos", value=bool(p.get("check_formalizado")))
                    c1,c2 = st.columns(2)
                    with c1: val_ok = st.selectbox("Validador Custos", ["Pendente","OK","NOK"],
                        index=["Pendente","OK","NOK"].index(p.get("validador_ok","Pendente")))
                    with c2: saving = st.number_input("Saving Validado (R$)",
                        value=float(p.get("saving_validado",0)), step=1000.0, format="%.2f")
                    prev_custos = st.number_input("Valor Calculado por Custos (R$)",
                        value=float(p.get("previsto_custos",0)), step=1000.0, format="%.2f",
                        help="Este valor substitui o previsto da unidade na distribuição mensal")
                else:
                    ck_a3=p.get("check_a3",0); ck_mem=p.get("check_memoria",0)
                    ck_for=p.get("check_formalizado",0)
                    val_ok=p.get("validador_ok","Pendente")
                    saving=p.get("saving_validado",0)
                    prev_custos=p.get("previsto_custos",0)

                col_s, col_d = st.columns([4,1])
                with col_s: salvar_e  = st.form_submit_button("💾 Salvar", use_container_width=True)
                with col_d: excluir_e = st.form_submit_button("🗑️", use_container_width=True)

            if salvar_e:
                atualizar_projeto(p["id"], {
                    "nome":nome_e,"tipo":tipo_e,"va_ggf":va_e,"responsavel":resp_e,
                    "descricao":desc_e,"obs":obs_e,"status":status_e,
                    "previsto_unidade":prev_e,"previsto_custos":prev_custos,
                    "atividade_atual":ativ_e,"data_conclusao_ativ":dt_e,
                    "onde_parado":onde_e,"data_lib":dlib_e,
                    "check_a3":int(ck_a3),"check_memoria":int(ck_mem),
                    "check_formalizado":int(ck_for),
                    "validador_ok":val_ok,"saving_validado":saving,
                }, user["id"])
                st.success("✅ Projeto atualizado!"); st.rerun()

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
                        if st.button("✕", key=f"dl_{lk['id']}"): 
                            del_link(lk["id"]); st.rerun()
            else:
                st.info("Nenhum link cadastrado ainda.")

            st.markdown("---")
            with st.form("form_link", clear_on_submit=True):
                c1,c2 = st.columns([2,4])
                with c1: titulo_lk = st.text_input("Nome do link (ex: A3, Memória)")
                with c2: url_lk    = st.text_input("URL (SharePoint, OneDrive...)")
                if st.form_submit_button("➕ Adicionar Link", use_container_width=True):
                    if titulo_lk and url_lk:
                        add_link(p2["id"], titulo_lk, url_lk)
                        st.success("✅ Link adicionado!"); st.rerun()

    # ── Campeões ──────────────────────────────────────────────────────────────
    with tab_campeoes:
        from database import listar_projetos as lp
        camp = lp(unidade_sel, incluir_campeao=True)
        camp = [p for p in camp if p["campeao"]]
        if not camp:
            st.info("Nenhum projeto campeão ainda. Os projetos ganham o troféu após 12 meses de retorno.")
        else:
            for p in camp:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#FFD700,#FFA500);border-radius:10px;
                    padding:14px 18px;margin-bottom:10px;display:flex;align-items:center;gap:12px;">
                  <span style="font-size:28px;">🏆</span>
                  <div>
                    <div style="font-weight:700;font-size:13px;color:#1C2B4A;">{p['nome']}</div>
                    <div style="font-size:11px;color:#555;">{p['tipo']} · Campeão desde {p.get('campeao_em','')[:7]}</div>
                    <div style="font-size:11px;color:#555;">Saving validado: R$ {p['saving_validado']:,.0f}</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
