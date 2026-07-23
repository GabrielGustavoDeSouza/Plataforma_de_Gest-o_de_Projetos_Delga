import streamlit as st
import base64
from datetime import date, datetime
import plotly.graph_objects as go
from database import (listar_unidades, criar_projeto, add_link,
                      TIPOS_PROJETO, VA_GGF_OPTS, STATUS_OPTS,
                      EXTRA_DRE_TIPOS, CAMPOS_A3, get_a3, salvar_a3,
                      add_a3_midia, get_a3_midias, del_a3_midia,
                      add_evidencia, get_evidencias, del_evidencia,
                      listar_atividades, add_atividade, atualizar_atividade,
                      del_atividade, progresso_plan_atividade, atividade_atual,
                      get_projeto, atualizar_projeto)

DATA_FIM_PROJETOS_APLICADOS = date(2027, 1, 1)

def pode_editar(user, unidade_nome):
    if user["perfil"] == "admin": return True
    if user["perfil"] in ("facilitador","gestor"):
        return user.get("unidade") == unidade_nome
    return False

def _parse_date(v):
    if not v: return None
    try: return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()
    except Exception: return None

def _arquivo_para_b64(uploaded_file, limite_mb=8):
    if not uploaded_file: return None, None
    dados = uploaded_file.read()
    if len(dados) > limite_mb * 1024 * 1024:
        return None, f"Arquivo maior que {limite_mb}MB — deixa o backup muito pesado, escolhe um menor."
    return base64.b64encode(dados).decode("utf-8"), None

# =====================================================================
# GANTT — calculado em cima da Estrutura, não é preenchido à parte
# =====================================================================
def build_gantt(atividades, colors):
    NAVY=colors.get("NAVY","#0B0F2B"); GREEN=colors.get("GREEN","#1AA260")
    AMBER=colors.get("AMBER","#E8A838"); RED=colors.get("RED","#D93B3B")
    SILVER=colors.get("SILVER","#8A9BB0")
    fig = go.Figure()
    labels = []
    for a in atividades:
        ini = _parse_date(a.get("inicio_previsto")); fim = _parse_date(a.get("termino_previsto"))
        if not ini or not fim or fim < ini: continue
        nome = a.get("nome") or "(sem nome)"
        labels.append(nome)
        prog = max(0.0, min(1.0, (a.get("progresso_real") or 0)/100))
        total_dias = (fim-ini).days + 1
        atrasada_flag = prog < 1 and fim < date.today()
        # trilho de fundo — tamanho do planejado
        fig.add_trace(go.Bar(
            x=[total_dias], y=[nome], base=[ini], orientation="h",
            marker=dict(color="#E8ECF4", line=dict(color=SILVER, width=1)),
            showlegend=False, hoverinfo="skip", width=0.55))
        # preenchimento conforme % real
        dias_preenchidos = round(total_dias*prog)
        if dias_preenchidos > 0:
            cor = RED if atrasada_flag else (GREEN if prog>=1 else AMBER)
            fig.add_trace(go.Bar(
                x=[dias_preenchidos], y=[nome], base=[ini], orientation="h",
                marker=dict(color=cor),
                text=f"{prog*100:.0f}%", textposition="inside", textfont=dict(color="white", size=11),
                showlegend=False,
                hovertemplate=f"<b>{nome}</b><br>Previsto: {ini:%d/%m}–{fim:%d/%m}<br>Real: {prog*100:.0f}%<extra></extra>",
                width=0.55))
    if not labels:
        return None
    fig.add_vline(x=datetime.combine(date.today(), datetime.min.time()),
                   line_width=1.5, line_dash="dot", line_color=RED)
    fig.update_layout(
        barmode="overlay", height=max(220, 48*len(labels)),
        margin=dict(l=10,r=10,t=10,b=10),
        xaxis=dict(type="date", title=None, gridcolor="#F0F2F7"),
        yaxis=dict(autorange="reversed", title=None),
        paper_bgcolor="white", plot_bgcolor="white",
        font=dict(family="Inter", size=12, color=NAVY))
    return fig

def _render_gantt(pid, colors):
    ativs = [a for a in listar_atividades(pid) if a.get("inicio_previsto") and a.get("termino_previsto")]
    if not ativs:
        st.info("Cadastre atividades na aba **Estrutura** com Início e Término previstos pra ver o Gantt aqui.")
        return
    st.caption("A barra tem o tamanho do planejado e é pintada conforme o % Progresso Real. "
              "A linha pontilhada vermelha é hoje. Vermelho na barra = atividade atrasada.")
    fig = build_gantt(ativs, colors)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# =====================================================================
# ESTRUTURA — atividades (o Gantt é derivado disso)
# =====================================================================
def _render_estrutura(pid, colors):
    SILVER=colors.get("SILVER","#8A9BB0")
    st.caption("Uma linha por atividade. **% Progresso Plan** é calculado sozinho (compara hoje com as "
              "datas previstas) — só pra referência. **% Progresso Real** você atualiza conforme o time "
              "avança. Ao bater 100%, a atividade some do posto de 'Atual Atribuição' e a próxima assume "
              "automaticamente no cartão do projeto.")

    ativs = listar_atividades(pid)
    for a in ativs:
        plan = progresso_plan_atividade(a.get("inicio_previsto"), a.get("termino_previsto"))
        real_v = a.get("progresso_real") or 0
        atrasada = plan is not None and real_v < 100 and plan >= 100
        titulo = f"{'⚠️ ' if atrasada else ''}#{a['ordem']} — {a['nome'] or '(sem nome)'} · Real {real_v:.0f}%"
        if plan is not None: titulo += f" · Plan {plan:.0f}%"
        with st.expander(titulo, expanded=False):
            with st.form(f"ativ_{a['id']}"):
                c1,c2 = st.columns(2)
                with c1: nome_e = st.text_input("Atividade", value=a.get("nome") or "")
                with c2: resp_e = st.text_input("Responsável", value=a.get("responsavel") or "")
                c1,c2,c3 = st.columns(3)
                with c1: ini_e = st.date_input("Início Previsto", value=_parse_date(a.get("inicio_previsto")), format="DD/MM/YYYY")
                with c2: fim_e = st.date_input("Término Previsto", value=_parse_date(a.get("termino_previsto")), format="DD/MM/YYYY")
                with c3: prog_e = st.number_input("% Progresso Real", min_value=0, max_value=100, value=int(real_v), step=5)
                acao_e = st.text_input("Ação / Observação", value=a.get("acao") or "")
                cs,cd = st.columns([4,1])
                with cs: salvar_at = st.form_submit_button("💾 Salvar", use_container_width=True)
                with cd: excluir_at = st.form_submit_button("🗑️", use_container_width=True)
            if salvar_at:
                atualizar_atividade(a["id"], {"nome":nome_e,"responsavel":resp_e,
                    "inicio_previsto":str(ini_e),"termino_previsto":str(fim_e),
                    "progresso_real":float(prog_e),"acao":acao_e})
                st.success("✅ Atualizado!"); st.rerun()
            if excluir_at:
                del_atividade(a["id"]); st.success("🗑️ Excluída."); st.rerun()

    st.markdown("**➕ Nova atividade**")
    with st.form(f"nova_ativ_{pid}", clear_on_submit=True):
        c1,c2 = st.columns(2)
        with c1: nome_n = st.text_input("Atividade")
        with c2: resp_n = st.text_input("Responsável")
        c1,c2 = st.columns(2)
        with c1: ini_n = st.date_input("Início Previsto", format="DD/MM/YYYY")
        with c2: fim_n = st.date_input("Término Previsto", format="DD/MM/YYYY")
        if st.form_submit_button("➕ Adicionar Atividade", use_container_width=True):
            if nome_n:
                add_atividade(pid, {"nome":nome_n,"responsavel":resp_n,
                    "inicio_previsto":str(ini_n),"termino_previsto":str(fim_n),"progresso_real":0})
                st.success("✅ Adicionada!"); st.rerun()
            else:
                st.error("Preencha o nome da atividade.")

    atual = atividade_atual(pid)
    if atual:
        st.info(f"📍 **Atual Atribuição (automática):** {atual['nome']} · "
               f"Responsável: {atual.get('responsavel') or '—'} · "
               f"Término Previsto: {str(atual.get('termino_previsto') or '—')[:10]}")
    elif ativs:
        st.success("✅ Todas as atividades concluídas!")

# =====================================================================
# A3 — 6 blocos + imagens inline + evidências gerais
# =====================================================================
def _render_a3(pid, colors):
    a3 = get_a3(pid)
    st.caption("Preencha cada bloco do A3. Pode anexar imagem em qualquer bloco (fica visível ali dentro — "
              "ex: um fluxo na Proposta/Desenvolvimento). Anexos que não são imagem (PPT, Excel, PDF) vão "
              "no espaço de Evidências, no fim da página.")
    valores = {}
    for campo, label in CAMPOS_A3:
        with st.expander(f"**{label}**", expanded=True):
            valores[campo] = st.text_area(label, value=a3.get(campo) or "", height=130,
                                           key=f"a3_{campo}_{pid}", label_visibility="collapsed")
            imgs = get_a3_midias(pid, campo)
            if imgs:
                cols = st.columns(min(len(imgs), 4))
                for i, img in enumerate(imgs):
                    with cols[i % 4]:
                        try:
                            st.image(base64.b64decode(img["dados_b64"]), caption=img.get("nome_arquivo"),
                                     use_container_width=True)
                        except Exception:
                            st.caption(f"📎 {img.get('nome_arquivo')}")
                        if st.button("🗑️ remover", key=f"delimg_{img['id']}", use_container_width=True):
                            del_a3_midia(img["id"]); st.rerun()
            up = st.file_uploader(f"Adicionar imagem — {label}", type=["png","jpg","jpeg","gif","webp"],
                                   key=f"upimg_{campo}_{pid}", label_visibility="collapsed")
            if up is not None:
                b64, erro = _arquivo_para_b64(up)
                if erro:
                    st.error(erro)
                elif b64:
                    add_a3_midia(pid, campo, up.name, up.type or "image/png", b64)
                    st.success("✅ Imagem adicionada."); st.rerun()

    if st.button("💾 Salvar A3", type="primary", use_container_width=True, key=f"salvar_a3_{pid}"):
        salvar_a3(pid, valores)
        st.success("✅ A3 salvo!")

    st.markdown("---")
    st.markdown("**📎 Evidências / Anexos** *(PPT, Excel, PDF ou qualquer arquivo de apoio)*")
    evids = get_evidencias(pid)
    for e in evids:
        c1,c2,c3 = st.columns([5,2,1])
        with c1: st.markdown(f"📄 **{e.get('nome_arquivo')}**")
        with c2: st.caption(e.get("mime_type") or "")
        with c3:
            if st.button("🗑️", key=f"delev_{e['id']}"): del_evidencia(e["id"]); st.rerun()
    up_ev = st.file_uploader("Adicionar evidência", key=f"upev_{pid}",
                              type=["pdf","ppt","pptx","xls","xlsx","doc","docx","png","jpg","jpeg"])
    if up_ev is not None:
        b64, erro = _arquivo_para_b64(up_ev)
        if erro:
            st.error(erro)
        elif b64:
            add_evidencia(pid, up_ev.name, up_ev.type or "application/octet-stream", b64)
            st.success("✅ Evidência anexada."); st.rerun()

# =====================================================================
# FUNDAMENTOS — cria o projeto (mesma paridade de campos do formato antigo)
# =====================================================================
def _render_fundamentos(user, colors):
    NAVY=colors.get("NAVY","#0B0F2B"); GREEN=colors.get("GREEN","#1AA260")

    pid_ativo = st.session_state.get("np2_pid")
    if pid_ativo:
        p = get_projeto(pid_ativo)
        if not p:
            st.session_state.pop("np2_pid", None); st.rerun(); return
        st.markdown(f"""<div style="background:#EAF0FF;border-left:3px solid {NAVY};border-radius:0 6px 6px 0;
             padding:10px 14px;margin-bottom:14px;font-size:12px;">
             ✏️ Editando <b>#{p['id']} — {p['nome']}</b> ({p['unidade_nome']}) — preencha A3, Estrutura e
             Gantt nas abas ao lado. Pra ajustar os campos daqui de novo, use o ✏️ em Minha Unidade.</div>""",
             unsafe_allow_html=True)
        if st.button("➕ Começar outro projeto novo", key="np2_novo"):
            st.session_state.pop("np2_pid", None); st.rerun()
        return

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    if user["perfil"] == "admin":
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np2_uni")
    elif user["perfil"] in ("facilitador","gestor","cost_control"):
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np2_uni")
        if user.get("unidade") and unidade_sel != user.get("unidade"):
            st.info(f"👁️ Você cria projetos apenas em **{user.get('unidade')}**")
    else:
        unidade_sel = user.get("unidade","")
        if unidade_sel not in nomes_u:
            st.warning("Unidade não configurada."); return

    if not pode_editar(user, unidade_sel):
        st.warning(f"⛔ Você só pode criar projetos em **{user.get('unidade','')}**.")
        return

    st.markdown("#### Identificação")
    c1,c2,c3 = st.columns(3)
    with c1: tipo = st.selectbox("Tipo *", TIPOS_PROJETO, key="np2_tipo")
    with c2: va   = st.selectbox("VA / GGF / Material Auxiliar *", VA_GGF_OPTS, key="np2_va")
    with c3: resp = st.text_input("Responsável", key="np2_resp")

    is_extra = tipo in EXTRA_DRE_TIPOS
    if is_extra:
        st.markdown(f'<div style="background:#F3E8FF;border-left:3px solid #9B59B6;border-radius:0 6px 6px 0;'
                    f'padding:8px 14px;font-size:11px;color:#6C3483;"><b>↷ Extra DRE</b> — {tipo} não gera '
                    f'lançamento de real mensal.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="background:#E6F4EC;border-left:3px solid {GREEN};border-radius:0 6px 6px 0;'
                    f'padding:8px 14px;font-size:11px;color:#1A5C2E;"><b>✓ Dentro do DRE</b> — {tipo} impacta '
                    f'diretamente o DRE.</div>', unsafe_allow_html=True)

    with st.form("form_novo2", clear_on_submit=False):
        nome = st.text_input("Nome do Projeto *")
        desc = st.text_area("Descrição / Objetivo", height=70)

        st.markdown("#### Cabeçalho do A3")
        c1,c2,c3 = st.columns(3)
        with c1: numero_p = st.text_input("Nº do Projeto")
        with c2: lider_p = st.text_input("Líder do Projeto")
        with c3: revisao_p = st.text_input("Revisão", value="Rev. 00")
        integrantes_p = st.text_input("Integrantes", placeholder="Nomes separados por vírgula")

        st.markdown("#### Datas e Valores")
        ganho_unico = st.checkbox(
            "🎯 Ganho Único — retorno pontual, só no mês do 1º retorno",
            help="Concentra o valor inteiro no mês de retorno, sem ratear em 12 meses.")
        c1,c2,c3 = st.columns(3)
        with c1: inicio  = st.date_input("Data de Início do Projeto", format="DD/MM/YYYY")
        with c2: termino = st.date_input("Data de Fim do Projeto", format="DD/MM/YYYY")
        with c3: mpr     = st.date_input("Ganho a partir de... *", format="DD/MM/YYYY",
            help="Mês em que o projeto começa a gerar ganho financeiro — base do rateio em 12 meses "
                 "(ou mês único, se Ganho Único estiver marcado).")
        previsto = st.number_input("Valor Previsto (R$) *", min_value=0.0, step=1000.0, format="%.2f")

        st.markdown("#### Links e Evidências (SharePoint / OneDrive)")
        st.caption("Links externos rápidos. Anexos de verdade (PPT, Excel, imagens) ficam dentro do A3, "
                  "depois que o projeto for criado.")
        c1,c2 = st.columns([2,4])
        with c1: link1_tit = st.text_input("Nome 1", placeholder="ex: A3 do Projeto")
        with c2: link1_url = st.text_input("URL 1", placeholder="https://...")
        c1,c2 = st.columns([2,4])
        with c1: link2_tit = st.text_input("Nome 2")
        with c2: link2_url = st.text_input("URL 2")

        st.markdown("#### Checklist")
        st.caption("Quando os 3 estiverem marcados, o projeto vai para validação de Custos.")
        c1,c2,c3 = st.columns(3)
        with c1: ck_a3  = st.checkbox("A3 desenvolvido")
        with c2: ck_mem = st.checkbox("Memória de Cálculo desenvolvida")
        with c3: ck_for = st.checkbox("Formalizado com Custos")

        st.markdown("#### Status e Observações")
        status = st.selectbox("Status", STATUS_OPTS)
        obs = st.text_area("Observações", height=70)

        st.markdown("---")
        salvar = st.form_submit_button("💾 Criar Projeto e Continuar pro A3", use_container_width=True, type="primary")

    if salvar:
        if not nome:
            st.error("Preencha o Nome do Projeto.")
        elif previsto <= 0:
            st.error("Preencha o Valor Previsto.")
        else:
            pid = criar_projeto(unidade_sel, {
                "nome": nome, "tipo": tipo, "va_ggf": va,
                "responsavel": resp, "descricao": desc, "obs": obs,
                "inicio": str(inicio), "termino": str(termino),
                "mes_primeiro_retorno": str(mpr),
                "previsto_unidade": previsto, "status": status,
                "check_a3": ck_a3, "check_memoria": ck_mem,
                "check_formalizado": ck_for, "ganho_unico": int(ganho_unico),
                "origem": "novo", "numero_projeto": numero_p, "lider_projeto": lider_p,
                "integrantes": integrantes_p, "revisao": revisao_p,
                # Atual Atribuição passa a ser automática (via Estrutura) — nasce vazia
                "atividade_atual": "", "onde_parado": "", "data_conclusao_ativ": "",
            }, user["id"])
            for tit, url in [(link1_tit,link1_url),(link2_tit,link2_url)]:
                if tit and url:
                    add_link(pid, tit, url)
            st.session_state["np2_pid"] = pid
            st.success(f"✅ Projeto **{nome}** criado! ID #{pid} — agora preencha A3, Estrutura e Gantt.")
            st.rerun()

def _render_novo_projeto(user, colors):
    sub_fund, sub_a3, sub_est, sub_gantt = st.tabs(["🧱 Fundamentos", "📋 A3", "🗓️ Estrutura", "📊 Gantt"])
    with sub_fund:
        _render_fundamentos(user, colors)

    pid_ativo = st.session_state.get("np2_pid")
    with sub_a3:
        if not pid_ativo:
            st.info("Preencha e salve os **Fundamentos** primeiro — o A3 é preenchido depois, dentro do projeto já criado.")
        else:
            _render_a3(pid_ativo, colors)
    with sub_est:
        if not pid_ativo:
            st.info("Preencha e salve os **Fundamentos** primeiro.")
        else:
            _render_estrutura(pid_ativo, colors)
    with sub_gantt:
        if not pid_ativo:
            st.info("Preencha e salve os **Fundamentos** primeiro.")
        else:
            _render_gantt(pid_ativo, colors)

# =====================================================================
# PROJETOS APLICADOS — formulário original, disponível só até 01/01/2027
# =====================================================================
def _render_projetos_aplicados(user, colors):
    NAVY=colors.get("NAVY","#0B0F2B"); AMBER=colors.get("AMBER","#E8A838")
    GREEN=colors.get("GREEN","#1AA260"); SILVER=colors.get("SILVER","#8A9BB0")

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    if user["perfil"] == "admin":
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np_uni")
    elif user["perfil"] in ("facilitador","gestor","cost_control"):
        unidade_sel = st.selectbox("Unidade:", nomes_u, key="np_uni")
        if user.get("unidade") and unidade_sel != user.get("unidade"):
            st.info(f"👁️ Você cria projetos apenas em **{user.get('unidade')}**")
    else:
        unidade_sel = user.get("unidade","")
        if unidade_sel not in nomes_u:
            st.warning("Unidade não configurada."); return

    pode = pode_editar(user, unidade_sel)
    if not pode:
        st.warning(f"⛔ Você só pode criar projetos em **{user.get('unidade','')}**.")
        return

    st.markdown("#### Identificação")
    c1,c2,c3 = st.columns(3)
    with c1: tipo = st.selectbox("Tipo *", TIPOS_PROJETO, key="np_tipo")
    with c2: va   = st.selectbox("VA / GGF / Material Auxiliar *", VA_GGF_OPTS, key="np_va")
    with c3: resp = st.text_input("Responsável", key="np_resp")

    is_extra = tipo in EXTRA_DRE_TIPOS
    if is_extra:
        st.markdown(
            f'<div style="background:#F3E8FF;border-left:3px solid #9B59B6;'
            f'border-radius:0 6px 6px 0;padding:10px 14px;font-size:11px;color:#6C3483;">'
            f'<b>↷ Extra DRE</b> — <b>{tipo}</b> gera valor operacional mas <b>não impacta o DRE</b>. '
            f'Custos valida o valor, mas não há lançamento de real mensal para este projeto. '
            f'O valor acumula mês a mês no indicador <b>Extra DRE</b> do dashboard.<br>'
            f'<span style="color:#555;">São Extra DRE: Kaizen - Custo Evitado, '
            f'Kaizen - Capital de Giro e Meta Executiva.</span></div>',
            unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div style="background:#E6F4EC;border-left:3px solid {GREEN};'
            f'border-radius:0 6px 6px 0;padding:10px 14px;font-size:11px;color:#1A5C2E;">'
            f'<b>✓ Dentro do DRE</b> — <b>{tipo}</b> impacta diretamente o DRE. '
            f'Após aprovação de Custos, o valor é distribuído em 12 meses a partir do '
            f'"Ganho a partir de" e passa a ter acompanhamento de real mensal.<br>'
            f'<span style="color:#555;">São DRE: BSW, Kaizen, Kaizen - Ganho Recorrente, '
            f'Redução de Custo, Você Resolve e Estratégia Comercial.</span></div>',
            unsafe_allow_html=True)

    with st.form("form_novo", clear_on_submit=True):

        nome = st.text_input("Nome do Projeto *")
        desc = st.text_area("Descrição / Objetivo", height=70)

        st.markdown("#### Datas e Valores")
        ganho_unico = st.checkbox(
            "🎯 Ganho Único — retorno pontual, só no mês do 1º retorno",
            help="Use pra projetos raros em que o ganho inteiro acontece de uma vez, "
                 "no próprio mês de retorno — sem rateio em 12 meses. Isso evita ficar "
                 "esperando lançamento de real nos meses seguintes, que nesse caso não existem.")
        c1,c2,c3 = st.columns(3)
        with c1: inicio  = st.date_input("Data de Início do Projeto", format="DD/MM/YYYY")
        with c2: termino = st.date_input("Data de Fim do Projeto", format="DD/MM/YYYY")
        with c3: mpr     = st.date_input(
            "Ganho a partir de... *", format="DD/MM/YYYY",
            help="Mês em que o projeto começa a gerar ganho financeiro. "
                 + ("Como é Ganho Único, todo o valor entra nesse mês só."
                    if ganho_unico else
                    "A partir daqui contam 12 meses de vida útil. "
                    "Obrigatório também para projetos Extra DRE."))

        previsto = st.number_input(
            "Valor Previsto (R$) *",
            min_value=0.0, step=1000.0, format="%.2f",
            help="Valor estimado pela unidade. "
                 + ("Ganho Único: valor inteiro lançado no mês de retorno, sem rateio."
                    if ganho_unico else
                    "Distribuído em 12 meses a partir do 1º retorno. "
                    + ("Para Extra DRE, acumula no indicador Extra DRE mês a mês." if is_extra else
                       "Após validação de Custos, o valor calculado substituirá este nas projeções.")))

        st.markdown("#### Links e Evidências (SharePoint / OneDrive)")
        st.caption("Cole os links completos (https://...). Você pode adicionar mais depois.")
        c1,c2 = st.columns([2,4])
        with c1: link1_tit = st.text_input("Nome 1", placeholder="ex: A3 do Projeto")
        with c2: link1_url = st.text_input("URL 1", placeholder="https://...")
        c1,c2 = st.columns([2,4])
        with c1: link2_tit = st.text_input("Nome 2", placeholder="ex: Memória de Cálculo")
        with c2: link2_url = st.text_input("URL 2", placeholder="https://...")
        c1,c2 = st.columns([2,4])
        with c1: link3_tit = st.text_input("Nome 3", placeholder="ex: Planilha de Apoio")
        with c2: link3_url = st.text_input("URL 3", placeholder="https://...")

        st.markdown("#### Acompanhamento")
        status = st.selectbox("Status", STATUS_OPTS)
        st.caption("Os campos abaixo são opcionais — preenchidos nos acompanhamentos semanais.")
        c1,c2,c3 = st.columns(3)
        with c1: ativ     = st.text_input("Atual Atribuição", placeholder="Atividade em andamento...")
        with c2: resp_ativ = st.text_input("Responsável da Atribuição", placeholder="Nome...")
        with c3: dt_ativ   = st.text_input("Data Final da Atribuição", placeholder="ex: 08/2026")

        st.markdown("#### Checklist")
        st.caption("Quando os 3 estiverem marcados, o projeto vai para validação de Custos.")
        c1,c2,c3 = st.columns(3)
        with c1: ck_a3  = st.checkbox("A3 e Plano de Projeto desenvolvido")
        with c2: ck_mem = st.checkbox("Memória de Cálculo desenvolvida")
        with c3: ck_for = st.checkbox("Formalizado com Custos")
        if ck_a3 and ck_mem and ck_for:
            st.success("✅ Checklist completo — será encaminhado para validação de Custos.")

        st.markdown("#### Observações")
        obs = st.text_area("", height=80, label_visibility="collapsed",
                            placeholder="Observações gerais sobre o projeto...")

        st.markdown("---")
        salvar = st.form_submit_button("💾 Cadastrar Projeto",
                                       use_container_width=True, type="primary")

    if salvar:
        if not nome:
            st.error("Preencha o Nome do Projeto.")
        elif previsto <= 0:
            st.error("Preencha o Valor Previsto.")
        else:
            pid = criar_projeto(unidade_sel, {
                "nome": nome, "tipo": tipo, "va_ggf": va,
                "responsavel": resp, "descricao": desc, "obs": obs,
                "inicio": str(inicio), "termino": str(termino),
                "mes_primeiro_retorno": str(mpr),
                "previsto_unidade": previsto, "status": status,
                "atividade_atual": ativ,
                "data_conclusao_ativ": dt_ativ,
                "onde_parado": resp_ativ,
                "check_a3": ck_a3, "check_memoria": ck_mem,
                "check_formalizado": ck_for, "ganho_unico": int(ganho_unico),
                "origem": "aplicado",
            }, user["id"])
            for tit, url in [(link1_tit,link1_url),(link2_tit,link2_url),(link3_tit,link3_url)]:
                if tit and url:
                    add_link(pid, tit, url)
            st.success(f"✅ Projeto **{nome}** cadastrado! ID #{pid}")
            st.rerun()

# =====================================================================
def render(user, **colors):
    st.markdown('<span class="st">Projetos</span>', unsafe_allow_html=True)

    aplicados_disponivel = date.today() < DATA_FIM_PROJETOS_APLICADOS
    if aplicados_disponivel:
        tab_aplicados, tab_novo = st.tabs(["📝 Projetos Aplicados", "🆕 Novo Projeto"])
        with tab_aplicados:
            _render_projetos_aplicados(user, colors)
        with tab_novo:
            _render_novo_projeto(user, colors)
    else:
        st.caption("O formulário 'Projetos Aplicados' (usado pra cadastrar o histórico) não está mais "
                  "disponível a partir de 01/01/2027 — todo projeto novo nasce no formato completo, "
                  "com A3, Estrutura e Gantt.")
        _render_novo_projeto(user, colors)
