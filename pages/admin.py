import streamlit as st
import pandas as pd
import io, unicodedata
from datetime import datetime
from database import (listar_usuarios, criar_usuario, editar_usuario,
                      alterar_senha, listar_unidades, criar_unidade,
                      get_todas_metas, set_meta, resetar_projetos_teste,
                      listar_projetos, deletar_usuario,
                      importar_projetos_lote, normalizar_valor_lista,
                      TIPOS_PROJETO, VA_GGF_OPTS, STATUS_OPTS, PERFIS_LBL)

def render(user, **colors):
    NAVY=colors.get("NAVY","#0B0F2B"); RED=colors.get("RED","#D93B3B")
    if user["perfil"] != "admin":
        st.error("⛔ Acesso restrito a administradores."); return

    st.markdown('<span class="st">Administração</span>', unsafe_allow_html=True)
    tab_users, tab_editar, tab_metas, tab_unid, tab_senha, tab_import, tab_reset = st.tabs([
        "👥 Usuários","✏️ Editar Usuário","🎯 Metas","🏭 Unidades","🔑 Senhas",
        "📥 Importar Excel","🗑️ Reset"])

    with tab_users:
        usuarios = listar_usuarios()
        rows = "".join(f"""<tr>
          <td style="font-size:11px;font-weight:600;">{u['nome']}</td>
          <td style="font-size:11px;">{u['email']}</td>
          <td style="font-size:11px;">{PERFIS_LBL.get(u['perfil'],u['perfil'])}</td>
          <td style="font-size:11px;">{u.get('unidade') or '— Global'}</td>
          <td style="font-size:11px;">{'✅' if u['ativo'] else '❌'}</td>
        </tr>""" for u in usuarios)
        st.markdown(f"""<table class="dt"><thead><tr>
          <th>Nome</th><th>E-mail</th><th>Perfil</th><th>Unidade</th><th>Ativo</th>
        </tr></thead><tbody>{rows}</tbody></table>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Criar novo usuário**")
        unidades = listar_unidades()
        nomes_u  = ["— Acesso Global"] + [u["nome"] for u in unidades]
        with st.form("form_user", clear_on_submit=True):
            c1,c2=st.columns(2)
            with c1:
                nome_u  = st.text_input("Nome completo *")
                email_u = st.text_input("E-mail *")
                senha_u = st.text_input("Senha inicial *", type="password")
            with c2:
                perfil_u  = st.selectbox("Perfil *", list(PERFIS_LBL.keys()),
                                          format_func=lambda x: PERFIS_LBL[x])
                unidade_u = st.selectbox(
                    "Unidade (Global para admin/cost_control/visualizador global)",
                    nomes_u)
            if st.form_submit_button("➕ Criar Usuário", use_container_width=True):
                if not nome_u or not email_u or not senha_u:
                    st.error("Preencha todos os campos.")
                else:
                    unid = None if unidade_u=="— Acesso Global" else unidade_u
                    try:
                        criar_usuario(nome_u,email_u,senha_u,perfil_u,unid)
                        st.success(f"✅ **{nome_u}** criado!"); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")

    with tab_editar:
        usuarios = listar_usuarios()
        unidades = listar_unidades()
        nomes_u2 = ["— Acesso Global"] + [u["nome"] for u in unidades]
        sel_u = st.selectbox("Selecionar:",[u["nome"] for u in usuarios],key="ed_user")
        u_sel = next(u for u in usuarios if u["nome"]==sel_u)
        with st.form("form_ed_user"):
            c1,c2=st.columns(2)
            with c1:
                novo_nome  = st.text_input("Nome", value=u_sel["nome"])
                novo_email = st.text_input("E-mail", value=u_sel["email"])
                ativo      = st.checkbox("Ativo", value=bool(u_sel["ativo"]))
            with c2:
                novo_perfil = st.selectbox("Perfil", list(PERFIS_LBL.keys()),
                    index=list(PERFIS_LBL.keys()).index(u_sel["perfil"])
                    if u_sel["perfil"] in PERFIS_LBL else 0,
                    format_func=lambda x: PERFIS_LBL[x])
                unid_atual = u_sel.get("unidade") or "— Acesso Global"
                idx_unid   = nomes_u2.index(unid_atual) if unid_atual in nomes_u2 else 0
                nova_unid  = st.selectbox("Unidade", nomes_u2, index=idx_unid)
            if st.form_submit_button("💾 Salvar", use_container_width=True):
                editar_usuario(u_sel["id"],{
                    "nome":novo_nome,"email":novo_email.lower(),
                    "perfil":novo_perfil,
                    "unidade":None if nova_unid=="— Acesso Global" else nova_unid,
                    "ativo":int(ativo)})
                st.success(f"✅ **{novo_nome}** atualizado!"); st.rerun()

        st.markdown("---")
        st.markdown("**🗑️ Excluir usuário**")
        admins_ativos = [u for u in usuarios if u["perfil"]=="admin" and u["ativo"]]
        if u_sel["id"] == user["id"]:
            st.info("Você não pode excluir seu próprio usuário logado.")
        elif u_sel["perfil"]=="admin" and u_sel["ativo"] and len(admins_ativos) <= 1:
            st.info("Esse é o único administrador ativo — não pode ser excluído.")
        else:
            conf_del = st.checkbox(
                f"Confirmo que quero excluir **{u_sel['nome']}** permanentemente.",
                key=f"confdel_{u_sel['id']}")
            if st.button("🗑️ Excluir Usuário", disabled=not conf_del,
                        key=f"btndel_{u_sel['id']}"):
                if deletar_usuario(u_sel["id"]):
                    st.success(f"✅ **{u_sel['nome']}** excluído."); st.rerun()
                else:
                    st.error(
                        f"Não foi possível excluir **{u_sel['nome']}**: existem projetos "
                        f"ou lançamentos no histórico vinculados a ele. Desative-o "
                        f"(campo Ativo acima) em vez de excluir.")

    with tab_metas:
        st.markdown("**Definir Meta Anual por Unidade / Área**")
        anos = list(range(2026,2031))
        ano_sel = st.selectbox("Ano:",anos,key="adm_ano")
        metas = get_todas_metas(ano_sel)
        with st.form("form_metas"):
            vals={}
            for m in metas:
                vals[m["nome"]] = st.number_input(
                    f"{m['nome']} ({m['tipo']})",
                    value=float(m["valor"]),step=10000.0,format="%.2f",
                    key=f"meta_{m['nome']}_{ano_sel}")
            if st.form_submit_button("💾 Salvar Metas", use_container_width=True):
                for nome,val in vals.items(): set_meta(nome,ano_sel,val)
                st.success("✅ Metas salvas!")

    with tab_unid:
        unidades = listar_unidades(so_ativas=False)
        rows_u="".join(f"""<tr>
          <td style="font-size:11px;font-weight:600;">{u['nome']}</td>
          <td style="font-size:11px;">{u['tipo']}</td>
          <td style="font-size:11px;">{'✅ Ativa' if u['ativo'] else '❌ Inativa'}</td>
        </tr>""" for u in unidades)
        st.markdown(f"""<table class="dt">
          <thead><tr><th>Nome</th><th>Tipo</th><th>Status</th></tr></thead>
          <tbody>{rows_u}</tbody></table>""", unsafe_allow_html=True)
        st.markdown("---")
        with st.form("form_unid", clear_on_submit=True):
            c1,c2=st.columns(2)
            with c1: nome_nu=st.text_input("Nome *")
            with c2: tipo_nu=st.selectbox("Tipo",["planta","area"])
            if st.form_submit_button("➕ Criar", use_container_width=True):
                if nome_nu: criar_unidade(nome_nu,tipo_nu); st.success(f"✅ **{nome_nu}** criada!"); st.rerun()

    with tab_senha:
        usuarios=listar_usuarios()
        sel_s=st.selectbox("Usuário:",[u["nome"] for u in usuarios],key="adm_senha")
        u_s=next(u for u in usuarios if u["nome"]==sel_s)
        with st.form("form_senha"):
            nova=st.text_input("Nova senha",type="password")
            conf=st.text_input("Confirmar",type="password")
            if st.form_submit_button("🔑 Alterar Senha"):
                if nova!=conf: st.error("Senhas não conferem.")
                elif len(nova)<6: st.error("Mínimo 6 caracteres.")
                else: alterar_senha(u_s["id"],nova); st.success(f"✅ Senha alterada!")

    with tab_import:
        st.markdown("**📥 Importação em Lote — Projetos e Metas (nível de arranque)**")
        st.caption(
            "Use isso pra subir de uma vez os projetos que já existem fora da plataforma "
            "(planilha de controle). O lançamento de real mês a mês continua manual, "
            "projeto por projeto, em Controle de Custos.")

        unidades_disp = [u["nome"] for u in listar_unidades()]

        # ── Gerar modelo ────────────────────────────────────────────────────
        def _gerar_modelo():
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill
            from openpyxl.worksheet.datavalidation import DataValidation
            wb = Workbook()
            ws1 = wb.active; ws1.title = "Projetos"
            cols1 = ["Unidade","Tipo","VA/GGF","Nome do Projeto","Descrição","Responsável",
                     "Data Início","Data Fim","Valor Previsto","Mês Primeiro Retorno",
                     "Validação","Valor Calculado Custos","Status"]
            ws1.append(cols1)
            for c in range(1,len(cols1)+1):
                cell = ws1.cell(row=1,column=c)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="0B0F2B")
            exemplo = ["Diadema","BSW","VA","Projeto Exemplo — apagar esta linha",
                       "Descrição do projeto","Fulano de Tal","2026-01-15","2026-06-30",
                       120000,"2026-09-01","OK",40000,"Em Execução"]
            ws1.append(exemplo)
            for c in range(1,len(cols1)+1):
                ws1.cell(row=2,column=c).font = Font(italic=True, color="8A9BB0")
            widths = [14,14,10,32,30,18,13,13,14,18,11,20,14]
            for i,w in enumerate(widths,start=1):
                ws1.column_dimensions[chr(64+i) if i<=26 else "A"].width = w

            def _add_dv(col_letter, opcoes, n_rows=200):
                dv = DataValidation(type="list", formula1=f'"{",".join(opcoes)}"', allow_blank=True)
                ws1.add_data_validation(dv)
                dv.add(f"{col_letter}2:{col_letter}{n_rows}")
            _add_dv("A", unidades_disp)
            _add_dv("B", TIPOS_PROJETO)
            _add_dv("C", VA_GGF_OPTS)
            _add_dv("J", ["OK","NOK","Pendente"])
            _add_dv("M", STATUS_OPTS)

            ws2 = wb.create_sheet("Metas")
            ws2.append(["Unidade","Ano","Valor da Meta"])
            for c in range(1,4):
                cell = ws2.cell(row=1,column=c)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="0B0F2B")
            ws2.append(["Diadema",2026,300000])
            ws2.cell(row=2,column=1).font = Font(italic=True, color="8A9BB0")
            ws2.column_dimensions["A"].width=14; ws2.column_dimensions["C"].width=16
            dv2 = DataValidation(type="list", formula1=f'"{",".join(unidades_disp)}"', allow_blank=True)
            ws2.add_data_validation(dv2); dv2.add("A2:A200")

            buf = io.BytesIO(); wb.save(buf); buf.seek(0)
            return buf

        c_dl, _ = st.columns([1,3])
        with c_dl:
            st.download_button("⬇️ Baixar modelo (.xlsx)", data=_gerar_modelo(),
                file_name="modelo_importacao_delga.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        st.caption("Apague a linha de exemplo antes de preencher. As colunas Unidade, Tipo, "
                   "VA/GGF, Validação e Status têm lista suspensa pra evitar erro de digitação.")

        st.markdown("---")
        arquivo = st.file_uploader("Enviar planilha preenchida (.xlsx)", type=["xlsx"])

        def _norm(s):
            s = str(s or "").strip().lower()
            return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

        def _parse_data(v):
            if pd.isna(v) or v in (None,""): return ""
            if isinstance(v,(pd.Timestamp,datetime)): return v.strftime("%Y-%m-%d")
            try: return datetime.strptime(str(v)[:10],"%Y-%m-%d").strftime("%Y-%m-%d")
            except: return ""

        def _parse_mes(v):
            if pd.isna(v) or v in (None,""): return None
            if isinstance(v,(pd.Timestamp,datetime)): return v.strftime("%Y-%m-01")
            try: return datetime.strptime(str(v)[:7],"%Y-%m").strftime("%Y-%m-01")
            except: return None

        if arquivo is not None:
            try:
                xls = pd.read_excel(arquivo, sheet_name=None)
            except Exception as e:
                st.error(f"Não consegui ler o arquivo: {e}"); xls = None

            if xls is not None:
                sheet_proj = next((v for k,v in xls.items() if "projeto" in _norm(k)), None)
                sheet_meta = next((v for k,v in xls.items() if "meta" in _norm(k)), None)

                linhas_ok, linhas_erro = [], []
                if sheet_proj is not None:
                    col_map = {_norm(c):c for c in sheet_proj.columns}
                    def _get(row,*chaves):
                        for ch in chaves:
                            if ch in col_map: return row[col_map[ch]]
                        return None

                    for idx,row in sheet_proj.iterrows():
                        nome = _get(row,"nome do projeto","nome")
                        if pd.isna(nome) or not str(nome).strip(): continue
                        motivo=[]
                        unid = normalizar_valor_lista(_get(row,"unidade"), unidades_disp)
                        if not unid: motivo.append("unidade não reconhecida")
                        tipo = normalizar_valor_lista(_get(row,"tipo"), TIPOS_PROJETO)
                        if not tipo: motivo.append("tipo não reconhecido")
                        va = normalizar_valor_lista(_get(row,"va/ggf","vaggf","va"), VA_GGF_OPTS)
                        if not va: va = "VA"
                        mpr = _parse_mes(_get(row,"mes primeiro retorno","mes do primeiro retorno"))
                        if not mpr: motivo.append("mês primeiro retorno inválido")
                        prev = _get(row,"valor previsto")
                        prev = float(prev) if not pd.isna(prev) else 0.0
                        if prev<=0: motivo.append("valor previsto zerado")
                        valid = normalizar_valor_lista(_get(row,"validacao","validação"), ["OK","NOK","Pendente"]) or "Pendente"
                        status = normalizar_valor_lista(_get(row,"status"), STATUS_OPTS)
                        linha = {
                            "linha_planilha": idx+2, "nome": str(nome).strip(),
                            "unidade": unid, "tipo": tipo, "va_ggf": va,
                            "descricao": str(_get(row,"descricao","descrição") or ""),
                            "responsavel": str(_get(row,"responsavel","responsável") or ""),
                            "inicio": _parse_data(_get(row,"data inicio","data início")),
                            "termino": _parse_data(_get(row,"data fim")),
                            "previsto_unidade": prev,
                            "mes_primeiro_retorno": mpr,
                            "validacao": valid,
                            "valor_custos_bruto": _get(row,"valor calculado custos","valor calculado por custos"),
                            "status": status,
                        }
                        if motivo: linha["_erro"] = ", ".join(motivo); linhas_erro.append(linha)
                        else: linhas_ok.append(linha)

                metas_linhas = []
                if sheet_meta is not None:
                    col_map2 = {_norm(c):c for c in sheet_meta.columns}
                    for idx,row in sheet_meta.iterrows():
                        u = row.get(col_map2.get("unidade",""))
                        if pd.isna(u) or not str(u).strip(): continue
                        unid = normalizar_valor_lista(u, unidades_disp)
                        ano  = row.get(col_map2.get("ano",""))
                        val  = row.get(col_map2.get("valor da meta",""))
                        if unid and not pd.isna(ano) and not pd.isna(val):
                            metas_linhas.append({"unidade":unid,"ano":int(ano),"valor":float(val)})

                st.markdown(f"**Prévia:** {len(linhas_ok)} projeto(s) prontos para importar · "
                           f"{len(linhas_erro)} com erro · {len(metas_linhas)} meta(s) na planilha")

                if linhas_ok:
                    prev_rows = "".join(f"""<tr>
                      <td style="font-size:11px;">{l['linha_planilha']}</td>
                      <td style="font-size:11px;font-weight:600;">{l['nome']}</td>
                      <td style="font-size:11px;">{l['unidade']}</td>
                      <td style="font-size:11px;">{l['tipo']}</td>
                      <td style="font-size:11px;text-align:right;">R$ {l['previsto_unidade']:,.0f}</td>
                      <td style="font-size:11px;">{l['mes_primeiro_retorno']}</td>
                      <td style="font-size:11px;">{l['validacao']}</td>
                    </tr>""" for l in linhas_ok)
                    st.markdown(f"""<table class="dt"><thead><tr>
                      <th>Linha</th><th>Nome</th><th>Unidade</th><th>Tipo</th>
                      <th style="text-align:right;">Previsto</th><th>1º Retorno</th><th>Validação</th>
                    </tr></thead><tbody>{prev_rows}</tbody></table>""", unsafe_allow_html=True)

                if linhas_erro:
                    with st.expander(f"⚠️ {len(linhas_erro)} linha(s) com erro — não serão importadas"):
                        err_rows = "".join(f"""<tr>
                          <td style="font-size:11px;">{l['linha_planilha']}</td>
                          <td style="font-size:11px;">{l['nome']}</td>
                          <td style="font-size:11px;color:#D93B3B;">{l['_erro']}</td>
                        </tr>""" for l in linhas_erro)
                        st.markdown(f"""<table class="dt"><thead><tr>
                          <th>Linha</th><th>Nome</th><th>Erro</th>
                        </tr></thead><tbody>{err_rows}</tbody></table>""", unsafe_allow_html=True)

                if linhas_ok or metas_linhas:
                    st.markdown("---")
                    confirmar_imp = st.checkbox(
                        f"Confirmo a importação de {len(linhas_ok)} projeto(s) e "
                        f"{len(metas_linhas)} meta(s).")
                    if st.button("📥 Confirmar Importação", disabled=not confirmar_imp,
                                type="primary", use_container_width=True):
                        sucesso, erros_imp = importar_projetos_lote(linhas_ok, user["id"])
                        for m in metas_linhas: set_meta(m["unidade"], m["ano"], m["valor"])
                        st.success(f"✅ {len(sucesso)} projeto(s) importado(s) e "
                                  f"{len(metas_linhas)} meta(s) atualizada(s).")
                        if erros_imp:
                            st.error(f"{len(erros_imp)} falharam na gravação: " +
                                    "; ".join(f"{e['nome']} ({e['erro']})" for e in erros_imp))
                        st.rerun()

    with tab_reset:
        n_proj = len(listar_projetos(incluir_campeao=True))
        st.markdown(f"**🗑️ Resetar Projetos de Teste**")
        st.warning(
            f"Isso apaga **todos os {n_proj} projeto(s)** cadastrados — junto com seus "
            f"links e lançamentos de real. **Usuários, unidades e metas são mantidos.**\n\n"
            f"Use isso para limpar os dados de teste antes de começar a operação real.")
        confirmar = st.checkbox("Entendo que essa ação é irreversível e quero apagar todos os projetos.")
        if st.button("🗑️ Apagar todos os projetos", disabled=not confirmar,
                     use_container_width=True, type="primary"):
            resetar_projetos_teste()
            st.success("✅ Todos os projetos, links e lançamentos foram apagados. Usuários, unidades e metas foram mantidos.")
            st.rerun()
