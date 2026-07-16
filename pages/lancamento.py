import streamlit as st
from datetime import datetime, date
from database import (listar_unidades, listar_projetos, lancar_real,
                      get_lancamentos, get_curva_unidade, get_curva_custos,
                      get_links, atualizar_projeto, is_extra_dre, MESES_PT)

def clean_html(html):
    return "".join(l.strip() for l in html.strip().split("\n"))

def hc(html): st.markdown(clean_html(html), unsafe_allow_html=True)

def fmt_brl(v):
    if not v and v != 0: return "—"
    return f"R$ {float(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")

def render(user, **colors):
    NAVY=colors.get("NAVY","#1C2B4A"); GREEN=colors.get("GREEN","#1A7A3A")
    AMBER=colors.get("AMBER","#E8A838"); RED=colors.get("RED","#C8202E")
    TEAL=colors.get("TEAL","#20C997"); SILVER=colors.get("SILVER","#8A9BB0")

    ano_atual = datetime.now().year
    is_cc = user["perfil"] in ("admin","cost_control")

    tab_fila, tab_real = st.tabs(["📋 Fila de Aprovação","💰 Controle de Custos"])

    unidades = listar_unidades()
    nomes_u  = [u["nome"] for u in unidades]

    def filtro_checkboxes(key):
        """Filtro por unidade via checkboxes em grid."""
        st.markdown(f"<p style='font-size:10px;font-weight:600;color:{SILVER};text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px;'>Filtrar unidades:</p>", unsafe_allow_html=True)
        n_cols = 4
        rows = [nomes_u[i:i+n_cols] for i in range(0,len(nomes_u),n_cols)]
        sel = []
        for row in rows:
            cols = st.columns(len(row))
            for i,u in enumerate(row):
                with cols[i]:
                    if st.checkbox(u, value=True, key=f"{key}_{u}"):
                        sel.append(u)
        return sel

    # ── Fila de Aprovação ─────────────────────────────────────────────────────
    with tab_fila:
        hc(f'<span class="st">Fila de Aprovação — Cost Control</span>')
        st.caption("Projetos com checklist completo aguardando validação. "
                   "Clique nos links para estudar antes de validar.")

        if not is_cc:
            st.info("Acesso restrito ao time de Cost Control."); 
        else:
            unis_fila = filtro_checkboxes("fila")
            todos = listar_projetos()
            fila  = [p for p in todos
                     if p["check_a3"] and p["check_memoria"] and p["check_formalizado"]
                     and p.get("validador_ok","Pendente")=="Pendente"
                     and p["unidade_nome"] in unis_fila]

            st.markdown(f"**{len(fila)} projeto(s) aguardando aprovação**")
            if not fila:
                st.success("✅ Nenhum projeto aguardando aprovação.")
            else:
                for p in fila:
                    links = get_links(p["id"])
                    extra = is_extra_dre(p["tipo"])
                    dre_b = f'<span style="background:#F3E8FF;color:#9B59B6;font-size:9px;padding:1px 6px;border-radius:6px;font-weight:600;">↷ N/DRE</span>' if extra else f'<span style="background:#E6F4EC;color:{GREEN};font-size:9px;padding:1px 6px;border-radius:6px;font-weight:600;">✓ DRE</span>'

                    # Links como botões HTML clicáveis com href real
                    if links:
                        link_items = "".join(
                            f'<a href="{lk["url"]}" target="_blank" rel="noopener noreferrer" '
                            f'style="display:inline-flex;align-items:center;gap:4px;'
                            f'background:{NAVY};color:white;font-size:11px;font-weight:600;'
                            f'padding:5px 12px;border-radius:6px;text-decoration:none;'
                            f'margin-right:6px;margin-top:4px;">'
                            f'🔗 {lk["titulo"]}</a>'
                            for lk in links)
                        links_html = f'<div style="margin-top:8px;">{link_items}</div>'
                    else:
                        links_html = f'<p style="font-size:10px;color:#ccc;margin-top:6px;">Sem links cadastrados</p>'

                    hc(f"""
<div style="border-left:4px solid {NAVY};background:white;border-radius:0 8px 8px 0;
     padding:14px 18px;margin-bottom:6px;box-shadow:0 1px 4px rgba(28,43,74,.08);">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div style="flex:1;">
      <div style="font-size:10px;color:{SILVER};">{p['unidade_nome']} · {p['tipo']} {dre_b}</div>
      <div style="font-size:13px;font-weight:700;color:{NAVY};margin-top:2px;">#{p['id']} — {p['nome']}</div>
      <div style="font-size:11px;color:#555;margin-top:4px;">{p.get('descricao','') or '—'}</div>
      {links_html}
    </div>
    <div style="text-align:right;flex-shrink:0;margin-left:20px;">
      <div style="font-size:9px;color:{SILVER};text-transform:uppercase;letter-spacing:.4px;">Previsto Unidade</div>
      <div style="font-size:18px;font-weight:700;color:{AMBER};">R$ {p['previsto_unidade']:,.0f}</div>
    </div>
  </div>
</div>""")

                    with st.expander(f"⚖️ Aprovar / Reprovar #{p['id']} — {p['nome'][:40]}", expanded=False):
                        with st.form(f"fap_{p['id']}"):
                            decisao = st.radio("Decisão:", ["✅ Aprovar","❌ Reprovar"],
                                               horizontal=True, key=f"dec_{p['id']}")
                            valor_c = 0.0
                            if decisao == "✅ Aprovar":
                                valor_c = st.number_input(
                                    "Valor Calculado por Custos (R$)" +
                                    (" **(Extra DRE — pode deixar 0)**" if extra else " *"),
                                    min_value=0.0, step=500.0, format="%.2f",
                                    key=f"vc_{p['id']}")
                                obs_ap = st.text_area("Observação (opcional)", height=60, key=f"oa_{p['id']}")
                            else:
                                obs_ap = st.text_area("Motivo da reprovação", height=60, key=f"or_{p['id']}")

                            confirmar = st.form_submit_button("Confirmar", use_container_width=True)

                        if confirmar:
                            if decisao == "✅ Aprovar":
                                if not extra and valor_c <= 0:
                                    st.error("Informe o Valor Calculado por Custos.")
                                else:
                                    atualizar_projeto(p["id"], {
                                        "validador_ok":  "OK",
                                        "previsto_custos": valor_c,
                                        "saving_validado": valor_c,
                                        "obs": (p.get("obs","") or "") + (f"\n[Custos] {obs_ap}" if obs_ap else ""),
                                    }, user["id"])
                                    st.success(f"✅ Projeto #{p['id']} aprovado!")
                                    st.rerun()
                            else:
                                atualizar_projeto(p["id"], {
                                    "validador_ok": "NOK",
                                    "check_formalizado": 0,
                                    "obs": (p.get("obs","") or "") + (f"\n[Reprovado] {obs_ap}" if obs_ap else ""),
                                }, user["id"])
                                st.warning(f"⚠️ Projeto #{p['id']} reprovado. Retorna para a unidade.")
                                st.rerun()

    # ── Controle de Custos ────────────────────────────────────────────────────
    with tab_real:
        hc(f'<span class="st">Controle de Custos — Lançamento Real Mensal</span>')
        st.info("📌 Lance o retorno do **mês anterior** na primeira semana do mês atual. "
                "Valores já lançados podem ser editados.")

        if not is_cc:
            st.info("Acesso restrito ao time de Cost Control."); return

        unis_real = filtro_checkboxes("real")

        c1,c2 = st.columns(2)
        with c1:
            anos = list(range(2025,2030))
            ano_sel = st.selectbox("Ano:", anos,
                index=anos.index(ano_atual) if ano_atual in anos else 0, key="cc_ano")
        with c2:
            mes_sel = st.selectbox("Mês de referência:", range(1,13),
                format_func=lambda m: MESES_PT[m-1], key="cc_mes")

        # Todos projetos DRE aprovados das unidades selecionadas
        todos_ap = [p for p in listar_projetos()
                    if p.get("validador_ok")=="OK"
                    and not is_extra_dre(p["tipo"])
                    and p["unidade_nome"] in unis_real]

        # Filtra os que têm fração prevista neste mês
        proj_mes = []
        for p in todos_ap:
            curva = get_curva_unidade(p["id"])  # usa previsto_unidade para referência
            frac  = curva.get((ano_sel, mes_sel), 0)
            if curva and any(y==ano_sel for (y,m) in curva):
                # Inclui se tem frações no ANO (não só no mês exato)
                proj_mes.append((p, frac))

        if not proj_mes:
            st.info(f"Nenhum projeto DRE aprovado com retorno em {ano_sel} "
                    f"nas unidades selecionadas.")
        else:
            # Busca lançamentos existentes para este mês/ano
            lancs_exist = {}
            for l in get_lancamentos(ano=ano_sel):
                if l["mes"] == mes_sel and not is_extra_dre(l.get("tipo","")):
                    lancs_exist[l["projeto_id"]] = l

            pendentes = [(p,f) for p,f in proj_mes if p["id"] not in lancs_exist]
            lancados  = [(p,f) for p,f in proj_mes if p["id"] in lancs_exist]

            st.markdown(f"**{len(proj_mes)} projeto(s)** · "
                        f"{len(pendentes)} pendente(s) · {len(lancados)} lançado(s) "
                        f"em {MESES_PT[mes_sel-1]}/{ano_sel}")
            st.markdown("---")

            # ── Formulário único com TODOS os projetos ────────────────────────
            with st.form("form_real_todos"):
                valores = {}; obs_map = {}
                header_html = f"""
<div style="display:grid;grid-template-columns:3fr 1fr 1fr 2fr;gap:8px;
     padding:6px 10px;background:{NAVY};border-radius:6px;margin-bottom:4px;">
  <div style="color:white;font-size:10px;font-weight:600;text-transform:uppercase;">Projeto</div>
  <div style="color:rgba(255,255,255,.7);font-size:10px;font-weight:600;text-transform:uppercase;text-align:center;">Fração Prev.</div>
  <div style="color:rgba(255,255,255,.7);font-size:10px;font-weight:600;text-transform:uppercase;text-align:center;">Real (R$)</div>
  <div style="color:rgba(255,255,255,.7);font-size:10px;font-weight:600;text-transform:uppercase;">Observação</div>
</div>"""
                hc(header_html)

                for p, frac in proj_mes:
                    ant    = lancs_exist.get(p["id"])
                    val_ant= float(ant["valor_real"]) if ant else 0.0
                    obs_ant= ant["observacao"] if ant else ""
                    ja     = p["id"] in lancs_exist
                    badge  = f'<span style="color:{GREEN};font-size:10px;">✅</span>' if ja else f'<span style="color:{AMBER};font-size:10px;">⏳</span>'

                    hc(f"""
<div style="padding:6px 10px;background:{'#F9FFF9' if ja else 'white'};
     border-radius:6px;border:1px solid {'#D4EDDA' if ja else '#EEF0F3'};margin-bottom:4px;">
  <div style="font-size:11px;font-weight:700;color:{NAVY};">{badge} #{p['id']} — {p['nome'][:45]}</div>
  <div style="font-size:10px;color:{SILVER};">{p['unidade_nome']} · {p['tipo']}</div>
</div>""")

                    c1,c2,c3 = st.columns([2,2,4])
                    with c1:
                        st.markdown(f"**Fração:** R$ {frac:,.0f}" if frac else "**Sem fração**")
                    with c2:
                        valores[p["id"]] = st.number_input(
                            "Real", value=val_ant, step=100.0, format="%.2f",
                            key=f"rv_{p['id']}", label_visibility="collapsed")
                    with c3:
                        obs_map[p["id"]] = st.text_input(
                            "Obs", value=obs_ant, key=f"ro_{p['id']}",
                            label_visibility="collapsed", placeholder="Observação...")
                    st.markdown("<hr style='margin:4px 0;border-color:#F0F0F0;'>", unsafe_allow_html=True)

                salvar = st.form_submit_button(
                    f"💾 Salvar todos os lançamentos de {MESES_PT[mes_sel-1]}/{ano_sel}",
                    use_container_width=True, type="primary")

            if salvar:
                count = 0
                for pid, val in valores.items():
                    if val >= 0:
                        lancar_real(pid, ano_sel, mes_sel, val, obs_map.get(pid,""), user["id"])
                        count += 1
                st.success(f"✅ {count} lançamento(s) salvos para {MESES_PT[mes_sel-1]}/{ano_sel}!")
                st.rerun()

            # ── Seção de revisão / edição ─────────────────────────────────────
            if lancados:
                st.markdown("---")
                st.markdown(f"**✏️ Revisar lançamentos de {MESES_PT[mes_sel-1]}/{ano_sel}:**")
                st.caption("Edite valores lançados incorretamente.")

                for p, frac in lancados:
                    lc     = lancs_exist[p["id"]]
                    real_v = lc["valor_real"]
                    diff   = real_v - frac if frac else 0
                    diff_c = GREEN if diff >= 0 else RED

                    with st.expander(
                        f"✏️ #{p['id']} — {p['nome'][:40]} | "
                        f"Lançado: R$ {real_v:,.0f} | Fração: R$ {frac:,.0f}",
                        expanded=False):
                        with st.form(f"rev_{p['id']}_{mes_sel}"):
                            c1,c2 = st.columns([2,4])
                            with c1:
                                novo_val = st.number_input(
                                    "Novo valor real (R$)",
                                    value=float(real_v), step=100.0, format="%.2f")
                            with c2:
                                nova_obs = st.text_input(
                                    "Observação", value=lc.get("observacao","") or "")
                            hc(f"""
<div style="display:flex;gap:16px;font-size:11px;padding:6px 0;">
  <span>Fração prevista: <b>R$ {frac:,.0f}</b></span>
  <span>Diferença: <b style="color:{diff_c};">{'▲' if diff>=0 else '▼'} R$ {abs(diff):,.0f}</b></span>
</div>""")
                            if st.form_submit_button("💾 Atualizar", use_container_width=True):
                                lancar_real(p["id"], ano_sel, mes_sel,
                                           novo_val, nova_obs, user["id"])
                                st.success("✅ Atualizado!")
                                st.rerun()
