import streamlit as st
from datetime import date
from database import (listar_unidades, listar_projetos, criar_projeto,
                      get_links, add_link, del_link,
                      TIPOS_PROJETO, VA_GGF_OPTS, STATUS_OPTS)

def pode_editar(user, unidade_nome):
    if user["perfil"] == "admin": return True
    if user["perfil"] in ("facilitador","gestor"):
        return user.get("unidade") == unidade_nome
    return False

def render(user, **colors):
    NAVY=colors.get("NAVY","#1C2B4A"); TEAL=colors.get("TEAL","#20C997")
    GREEN=colors.get("GREEN","#1A7A3A"); AMBER=colors.get("AMBER","#E8A838")
    SILVER=colors.get("SILVER","#8A9BB0"); RED=colors.get("RED","#C8202E")

    st.markdown('<span class="st">Novo Projeto</span>', unsafe_allow_html=True)

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    if user["perfil"] == "admin":
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np_uni")
    elif user["perfil"] in ("facilitador","gestor","cost_control"):
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np_uni")
        if user.get("unidade") and unidade_sel != user.get("unidade"):
            st.info(f"👁️ Leitura — você cria projetos apenas em "
                    f"**{user.get('unidade')}**")
    else:
        unidade_sel = user.get("unidade","")
        if unidade_sel not in nomes_u:
            st.warning("Unidade não configurada."); return

    pode = pode_editar(user, unidade_sel)

    tab_novo, tab_links = st.tabs(["➕ Cadastrar Projeto", "🔗 Links de Projetos"])

    # ── Novo Projeto ──────────────────────────────────────────────────────────
    with tab_novo:
        if not pode:
            st.warning(f"⛔ Você só pode criar projetos em "
                       f"**{user.get('unidade','')}**.")
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
                with c3: mpr     = st.date_input(
                    "Mês do 1º Retorno *",
                    help="A partir daqui contam 12 meses de vigência.")

                c1,c2 = st.columns(2)
                with c1:
                    previsto = st.number_input(
                        "Valor Previsto pela Unidade (R$) *",
                        min_value=0.0, step=1000.0, format="%.2f",
                        help="Distribuído em 12 meses a partir do 1º retorno.")
                with c2:
                    status = st.selectbox("Status", STATUS_OPTS)

                st.markdown("**Acompanhamento**")
                c1,c2 = st.columns(2)
                with c1:
                    ativ = st.text_input(
                        "Atividade em andamento (prevista no A3)")
                with c2:
                    dt_ativ = st.date_input(
                        "Previsão de conclusão desta atividade")

                st.markdown("**Links e Evidências (SharePoint / OneDrive)**")
                st.caption("Cole os links das evidências do projeto. "
                           "Você pode adicionar mais na aba 🔗 Links.")
                c1,c2 = st.columns([2,4])
                with c1: link1_titulo = st.text_input("Nome do link 1",
                                                       placeholder="ex: A3 do Projeto")
                with c2: link1_url    = st.text_input("URL 1",
                                                       placeholder="https://...")
                c1,c2 = st.columns([2,4])
                with c1: link2_titulo = st.text_input("Nome do link 2",
                                                       placeholder="ex: Memória de Cálculo")
                with c2: link2_url    = st.text_input("URL 2",
                                                       placeholder="https://...")

                st.markdown("**Checklist**")
                c1,c2,c3 = st.columns(3)
                with c1: ck_a3  = st.checkbox("A3 e Plano desenvolvido")
                with c2: ck_mem = st.checkbox("Memória de Cálculo desenvolvida")
                with c3: ck_for = st.checkbox("Formalizado com Custos")

                obs = st.text_area("Observações", height=50)

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
                    # Salva links se preenchidos
                    if link1_titulo and link1_url:
                        add_link(pid, link1_titulo, link1_url)
                    if link2_titulo and link2_url:
                        add_link(pid, link2_titulo, link2_url)
                    st.success(f"✅ Projeto **{nome}** cadastrado! ID #{pid}")
                    st.rerun()

    # ── Links de projetos existentes ──────────────────────────────────────────
    with tab_links:
        projetos = listar_projetos(unidade_sel)
        if not projetos:
            st.info("Nenhum projeto cadastrado ainda.")
        else:
            opts = {f"#{p['id']} {p['nome']}": p for p in projetos}
            sel2 = st.selectbox("Projeto:", list(opts.keys()), key="lk_sel")
            p2   = opts[sel2]
            links = get_links(p2["id"])

            if links:
                for lk in links:
                    c1,c2 = st.columns([8,1])
                    with c1:
                        st.markdown(f"🔗 [{lk['titulo']}]({lk['url']})")
                    with c2:
                        if pode and st.button("✕", key=f"dl_{lk['id']}"):
                            del_link(lk["id"]); st.rerun()
            else:
                st.info("Nenhum link cadastrado para este projeto.")

            if pode:
                st.markdown("---")
                with st.form("form_link", clear_on_submit=True):
                    c1,c2 = st.columns([2,4])
                    with c1:
                        titulo_lk = st.text_input(
                            "Nome (ex: A3, Memória, Planilha)")
                    with c2:
                        url_lk = st.text_input(
                            "URL (SharePoint / OneDrive...)")
                    if st.form_submit_button("➕ Adicionar Link",
                                              use_container_width=True):
                        if titulo_lk and url_lk:
                            add_link(p2["id"], titulo_lk, url_lk)
                            st.success("✅ Link adicionado!")
                            st.rerun()
