import sqlite3, hashlib, os, shutil
from datetime import datetime, date
import streamlit as st

# Caminho persistente — usa /tmp mas mantém backup em session via cache_resource
DB_PATH = "/tmp/plataforma_delga.db"

EXTRA_DRE_TIPOS = {"Kaizen - Custo Evitado","Kaizen - Capital de Giro","Meta Executiva"}
def is_extra_dre(tipo): return tipo in EXTRA_DRE_TIPOS

APP_VERSION = "REV2.1"

@st.cache_resource
def get_engine():
    """Mantém conexão viva enquanto o servidor estiver rodando."""
    _ensure_db()
    return True

def _ensure_db():
    """Garante que o banco existe e está inicializado."""
    if not os.path.exists(DB_PATH):
        init_db()

def get_conn():
    _ensure_db()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL, perfil TEXT NOT NULL DEFAULT 'facilitador',
        unidade TEXT, ativo INTEGER DEFAULT 1,
        criado_em TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS unidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL, tipo TEXT NOT NULL DEFAULT 'planta',
        ativo INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS metas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unidade_id INTEGER NOT NULL REFERENCES unidades(id),
        ano INTEGER NOT NULL, valor REAL DEFAULT 0,
        UNIQUE(unidade_id, ano))""")
    c.execute("""CREATE TABLE IF NOT EXISTS projetos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unidade_id INTEGER NOT NULL REFERENCES unidades(id),
        nome TEXT NOT NULL, tipo TEXT NOT NULL, va_ggf TEXT,
        responsavel TEXT, descricao TEXT, obs TEXT,
        inicio TEXT, termino TEXT, mes_primeiro_retorno TEXT,
        previsto_unidade REAL DEFAULT 0, previsto_custos REAL DEFAULT 0,
        status TEXT DEFAULT '📝 Não iniciado',
        atividade_atual TEXT, data_conclusao_ativ TEXT,
        check_a3 INTEGER DEFAULT 0, check_memoria INTEGER DEFAULT 0,
        check_formalizado INTEGER DEFAULT 0,
        validador_ok TEXT DEFAULT 'Pendente',
        saving_validado REAL DEFAULT 0,
        onde_parado TEXT, data_lib TEXT,
        campeao INTEGER DEFAULT 0, campeao_em TEXT,
        criado_em TEXT DEFAULT (datetime('now')),
        criado_por INTEGER REFERENCES usuarios(id),
        ultima_atualizacao TEXT DEFAULT (datetime('now')),
        atualizado_por INTEGER REFERENCES usuarios(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS projeto_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
        titulo TEXT NOT NULL, url TEXT NOT NULL,
        criado_em TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS lancamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
        ano INTEGER NOT NULL, mes INTEGER NOT NULL,
        valor_real REAL DEFAULT 0, observacao TEXT,
        lancado_em TEXT DEFAULT (datetime('now')),
        lancado_por INTEGER REFERENCES usuarios(id),
        UNIQUE(projeto_id, ano, mes))""")
    for nome, tipo in [
        ("Diadema","planta"),("Ferraz","planta"),("São Leopoldo","planta"),
        ("Jarinu","planta"),("Anchieta","planta"),
        ("Compras","area"),("Vendas","area"),("Corporativo","area")]:
        c.execute("INSERT OR IGNORE INTO unidades (nome,tipo) VALUES (?,?)",(nome,tipo))
    h = hashlib.sha256("Delga@2026".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO usuarios (nome,email,senha_hash,perfil) VALUES (?,?,?,?)",
              ("Administrador","admin@delga.com.br",h,"admin"))
    conn.commit(); conn.close()

def hash_senha(s): return hashlib.sha256(s.encode()).hexdigest()

def normalizar_url(url):
    """Garante que o link tenha esquema (https://), senão o navegador
    interpreta como caminho relativo e abre a própria página do app."""
    url = (url or "").strip()
    if not url: return url
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    return url

def fmt_brl(v, decimais=2):
    """Formato brasileiro: R$ 0.000.000,00"""
    if v is None: return "—"
    try: v = float(v)
    except (TypeError, ValueError): return "—"
    s = f"{v:,.{decimais}f}"
    s = s.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {s}"

def fmt_card(v):
    """Formato compacto brasileiro: R$ 0,00M / R$ 0,0k / R$ 0"""
    if v is None: return "—"
    try: v = float(v)
    except (TypeError, ValueError): return "—"
    if abs(v) >= 1_000_000:
        return fmt_brl(v/1_000_000, 2) + "M"
    if abs(v) >= 1_000:
        return fmt_brl(v/1_000, 1) + "k"
    return fmt_brl(v, 0)

TIPOS_PROJETO = ["BSW","Kaizen","Kaizen - Ganho Recorrente","Kaizen - Custo Evitado",
    "Kaizen - Capital de Giro","Redução de Custo","Você Resolve",
    "Meta Executiva","Estratégia Comercial"]
VA_GGF_OPTS  = ["VA","GGF","Material Auxiliar"]
STATUS_OPTS  = ["📝 Não iniciado","⏳ Em Execução","✓ Concluído","⚠️ Suspenso"]
MESES_PT     = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
PERFIS       = ["facilitador","gestor","cost_control","visualizador","admin"]
PERFIS_LBL   = {
    "facilitador":  "Facilitador — cria/edita só sua unidade, vê só sua unidade",
    "gestor":       "Gestor — cria/edita só sua unidade, vê todas",
    "cost_control": "Cost Control — valida e lança real em todas as unidades",
    "visualizador": "Visualizador — apenas visualiza unidade(s) e dashboard",
    "admin":        "Admin — acesso total",
}

def autenticar(email, senha):
    get_engine()
    conn = get_conn()
    row = conn.execute("SELECT * FROM usuarios WHERE email=? AND senha_hash=? AND ativo=1",
        (email.strip().lower(), hash_senha(senha))).fetchone()
    conn.close()
    return dict(row) if row else None

def listar_usuarios():
    get_engine(); conn = get_conn()
    rows = conn.execute("SELECT * FROM usuarios ORDER BY nome").fetchall()
    conn.close(); return [dict(r) for r in rows]

def criar_usuario(nome, email, senha, perfil, unidade):
    get_engine(); conn = get_conn()
    conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil,unidade) VALUES (?,?,?,?,?)",
        (nome, email.lower(), hash_senha(senha), perfil, unidade or None))
    conn.commit(); conn.close()

def editar_usuario(user_id, campos):
    conn = get_conn()
    sets = ", ".join(f"{k}=?" for k in campos)
    conn.execute(f"UPDATE usuarios SET {sets} WHERE id=?", list(campos.values())+[user_id])
    conn.commit(); conn.close()

def deletar_usuario(user_id):
    conn = get_conn()
    try:
        conn.execute("DELETE FROM usuarios WHERE id=?", (user_id,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()

def alterar_senha(user_id, nova):
    conn = get_conn()
    conn.execute("UPDATE usuarios SET senha_hash=? WHERE id=?",(hash_senha(nova),user_id))
    conn.commit(); conn.close()

def listar_unidades(so_ativas=True):
    get_engine(); conn = get_conn()
    q = "SELECT * FROM unidades" + (" WHERE ativo=1" if so_ativas else "") + " ORDER BY tipo,nome"
    rows = conn.execute(q).fetchall()
    conn.close(); return [dict(r) for r in rows]

def criar_unidade(nome, tipo):
    get_engine(); conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO unidades (nome,tipo) VALUES (?,?)",(nome,tipo))
    conn.commit(); conn.close()

def get_meta(unidade_nome, ano):
    get_engine(); conn = get_conn()
    row = conn.execute("""SELECT m.valor FROM metas m JOIN unidades u ON m.unidade_id=u.id
        WHERE u.nome=? AND m.ano=?""",(unidade_nome,ano)).fetchone()
    conn.close(); return row["valor"] if row else 0.0

def set_meta(unidade_nome, ano, valor):
    get_engine(); conn = get_conn()
    u = conn.execute("SELECT id FROM unidades WHERE nome=?",(unidade_nome,)).fetchone()
    if u:
        conn.execute("""INSERT INTO metas (unidade_id,ano,valor) VALUES (?,?,?)
            ON CONFLICT(unidade_id,ano) DO UPDATE SET valor=excluded.valor""",
            (u["id"],ano,valor))
    conn.commit(); conn.close()

def get_todas_metas(ano):
    get_engine(); conn = get_conn()
    rows = conn.execute("""SELECT u.nome,u.tipo,COALESCE(m.valor,0) as valor
        FROM unidades u LEFT JOIN metas m ON u.id=m.unidade_id AND m.ano=?
        WHERE u.ativo=1 ORDER BY u.tipo,u.nome""",(ano,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def listar_projetos(unidade_nome=None, incluir_campeao=False):
    get_engine(); conn = get_conn()
    q = """SELECT p.*,u.nome as unidade_nome,u.tipo as unidade_tipo
        FROM projetos p JOIN unidades u ON p.unidade_id=u.id WHERE 1=1"""
    params = []
    if unidade_nome: q += " AND u.nome=?"; params.append(unidade_nome)
    if not incluir_campeao: q += " AND p.campeao=0"
    q += " ORDER BY p.check_formalizado ASC,p.criado_em ASC"
    rows = conn.execute(q,params).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_projeto(proj_id):
    get_engine(); conn = get_conn()
    row = conn.execute("""SELECT p.*,u.nome as unidade_nome FROM projetos p
        JOIN unidades u ON p.unidade_id=u.id WHERE p.id=?""",(proj_id,)).fetchone()
    conn.close(); return dict(row) if row else None

def criar_projeto(unidade_nome, dados, user_id):
    get_engine(); conn = get_conn()
    u = conn.execute("SELECT id FROM unidades WHERE nome=?",(unidade_nome,)).fetchone()
    if not u: conn.close(); raise ValueError(f"Unidade não encontrada: {unidade_nome}")
    cursor = conn.execute("""INSERT INTO projetos (unidade_id,nome,tipo,va_ggf,responsavel,
        descricao,obs,inicio,termino,mes_primeiro_retorno,previsto_unidade,status,
        atividade_atual,data_conclusao_ativ,onde_parado,data_lib,
        check_a3,check_memoria,check_formalizado,criado_por,atualizado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (u["id"],dados["nome"],dados["tipo"],dados.get("va_ggf"),dados.get("responsavel"),
         dados.get("descricao"),dados.get("obs"),dados.get("inicio"),dados.get("termino"),
         dados.get("mes_primeiro_retorno"),dados.get("previsto_unidade",0),
         dados.get("status","📝 Não iniciado"),dados.get("atividade_atual"),
         dados.get("data_conclusao_ativ"),dados.get("onde_parado"),dados.get("data_lib"),
         int(dados.get("check_a3",0)),int(dados.get("check_memoria",0)),
         int(dados.get("check_formalizado",0)),user_id,user_id))
    pid = cursor.lastrowid; conn.commit(); conn.close(); return pid

def atualizar_projeto(proj_id, campos, user_id):
    campos["ultima_atualizacao"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    campos["atualizado_por"] = user_id
    conn = get_conn()
    sets = ", ".join(f"{k}=?" for k in campos)
    conn.execute(f"UPDATE projetos SET {sets} WHERE id=?", list(campos.values())+[proj_id])
    conn.commit(); conn.close()

def deletar_projeto(proj_id):
    conn = get_conn()
    conn.execute("DELETE FROM projetos WHERE id=?",(proj_id,))
    conn.commit(); conn.close()

def verificar_campeoes():
    conn = get_conn()
    projetos = conn.execute(
        "SELECT id,mes_primeiro_retorno FROM projetos WHERE campeao=0 AND mes_primeiro_retorno IS NOT NULL"
    ).fetchall()
    hoje = date.today()
    for p in projetos:
        try:
            mpr = datetime.strptime(str(p["mes_primeiro_retorno"])[:7],"%Y-%m").date()
            ano_c = mpr.year+(mpr.month+11)//12
            mes_c = (mpr.month+11)%12+1
            if hoje >= date(ano_c,mes_c,1):
                conn.execute("UPDATE projetos SET campeao=1,campeao_em=? WHERE id=?",
                             (hoje.isoformat(),p["id"]))
        except: pass
    conn.commit(); conn.close()

def get_links(proj_id):
    get_engine(); conn = get_conn()
    rows = conn.execute("SELECT * FROM projeto_links WHERE projeto_id=? ORDER BY id",(proj_id,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def add_link(proj_id, titulo, url):
    conn = get_conn()
    conn.execute("INSERT INTO projeto_links (projeto_id,titulo,url) VALUES (?,?,?)",
                 (proj_id, titulo, normalizar_url(url)))
    conn.commit(); conn.close()

def del_link(link_id):
    conn = get_conn()
    conn.execute("DELETE FROM projeto_links WHERE id=?",(link_id,))
    conn.commit(); conn.close()

def lancar_real(proj_id, ano, mes, valor, obs, user_id):
    conn = get_conn()
    conn.execute("""INSERT INTO lancamentos (projeto_id,ano,mes,valor_real,observacao,lancado_por)
        VALUES (?,?,?,?,?,?) ON CONFLICT(projeto_id,ano,mes) DO UPDATE SET
        valor_real=excluded.valor_real,observacao=excluded.observacao,
        lancado_em=datetime('now'),lancado_por=excluded.lancado_por""",
        (proj_id,ano,mes,valor,obs,user_id))
    conn.commit(); conn.close()

def get_lancamentos(unidade_nome=None, ano=None, proj_id=None):
    get_engine(); conn = get_conn()
    q = """SELECT l.*,p.nome as proj_nome,p.tipo,p.previsto_custos,p.previsto_unidade,
        p.mes_primeiro_retorno,u.nome as unidade_nome
        FROM lancamentos l JOIN projetos p ON l.projeto_id=p.id
        JOIN unidades u ON p.unidade_id=u.id WHERE 1=1"""
    params = []
    if unidade_nome: q += " AND u.nome=?"; params.append(unidade_nome)
    if ano:          q += " AND l.ano=?";  params.append(ano)
    if proj_id:      q += " AND l.projeto_id=?"; params.append(proj_id)
    rows = conn.execute(q,params).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_curva_unidade(proj_id):
    """Curva mensal usando previsto_unidade."""
    p = get_projeto(proj_id)
    if not p or not p.get("mes_primeiro_retorno"): return {}
    valor = p["previsto_unidade"]
    if valor<=0: return {}
    mensal = valor/12
    try: mpr = datetime.strptime(str(p["mes_primeiro_retorno"])[:7],"%Y-%m")
    except: return {}
    curva = {}
    for i in range(12):
        mes = (mpr.month-1+i)%12+1
        ano = mpr.year+(mpr.month-1+i)//12
        curva[(ano,mes)] = mensal
    return curva

def get_curva_custos(proj_id):
    """Curva mensal usando previsto_custos."""
    p = get_projeto(proj_id)
    if not p or not p.get("mes_primeiro_retorno") or not p["previsto_custos"]>0: return {}
    mensal = p["previsto_custos"]/12
    try: mpr = datetime.strptime(str(p["mes_primeiro_retorno"])[:7],"%Y-%m")
    except: return {}
    curva = {}
    for i in range(12):
        mes = (mpr.month-1+i)%12+1
        ano = mpr.year+(mpr.month-1+i)//12
        curva[(ano,mes)] = mensal
    return curva

def get_curva_saving(proj_id):
    """Curva mensal do saving validado — mesma regra do previsto:
    rateia em 12 meses a partir do mês de primeiro retorno."""
    p = get_projeto(proj_id)
    if not p or not p.get("mes_primeiro_retorno"): return {}
    valor = p.get("saving_validado", 0)
    if not valor or valor <= 0: return {}
    mensal = valor/12
    try: mpr = datetime.strptime(str(p["mes_primeiro_retorno"])[:7],"%Y-%m")
    except: return {}
    curva = {}
    for i in range(12):
        mes = (mpr.month-1+i)%12+1
        ano = mpr.year+(mpr.month-1+i)//12
        curva[(ano,mes)] = mensal
    return curva

def get_previsto_curva(proj_id):
    """Usa custos se disponível, senão unidade."""
    p = get_projeto(proj_id)
    if not p: return {}
    if p["previsto_custos"]>0: return get_curva_custos(proj_id)
    return get_curva_unidade(proj_id)

def alertas_validacao(unidade_nome=None):
    """Projetos com checklist completo aguardando validação de Custos."""
    projetos = listar_projetos(unidade_nome)
    return [p for p in projetos
            if p["check_a3"] and p["check_memoria"] and p["check_formalizado"]
            and p.get("validador_ok","Pendente") == "Pendente"]

def alertas_lancamento(unidade_nome=None):
    """Meses já vencidos sem lançamento de real — apenas projetos já
    aprovados por Custos (validador_ok='OK'), pois só esses têm curva
    de acompanhamento de real ativa."""
    projetos = listar_projetos(unidade_nome)
    hoje = date.today(); alertas = []
    for p in projetos:
        if is_extra_dre(p["tipo"]): continue
        if p.get("validador_ok") != "OK": continue
        if not p.get("mes_primeiro_retorno"): continue
        curva = get_curva_unidade(p["id"])
        lancs = {(l["ano"],l["mes"]) for l in get_lancamentos(proj_id=p["id"])}
        for (ano,mes),valor in curva.items():
            if date(ano,mes,1) < date(hoje.year,hoje.month,1) and (ano,mes) not in lancs:
                alertas.append({"projeto":p["nome"],"unidade":p["unidade_nome"],
                                "ano":ano,"mes":mes,"proj_id":p["id"],"valor_previsto":valor})
    return alertas

def get_ultima_obs_custos(proj_id):
    """Retorna a observação de Custos mais recente para o projeto —
    seja da última decisão de validação/reprovação, seja do último
    lançamento de real, o que tiver ocorrido por último."""
    p = get_projeto(proj_id)
    if not p: return None
    candidatos = []
    obs_txt = str(p.get("obs") or "")
    linhas_validacao = [l for l in obs_txt.split("\n")
                         if l.strip().startswith(("[Custos]","[Reprovado]"))]
    if linhas_validacao:
        candidatos.append({"texto": linhas_validacao[-1].strip(),
                            "data": p.get("ultima_atualizacao") or ""})
    lancs = get_lancamentos(proj_id=proj_id)
    lancs_com_obs = [l for l in lancs if (l.get("observacao") or "").strip()]
    if lancs_com_obs:
        ultimo = max(lancs_com_obs, key=lambda l: (l["ano"], l["mes"], l.get("lancado_em") or ""))
        mes_lbl = MESES_PT[ultimo["mes"]-1]
        candidatos.append({
            "texto": f"[Real {mes_lbl}/{ultimo['ano']}] {ultimo['observacao'].strip()}",
            "data": ultimo.get("lancado_em") or ""})
    if not candidatos: return None
    return max(candidatos, key=lambda c: c["data"])

def resetar_projetos_teste():
    """Apaga todos os projetos (e em cascata links e lançamentos),
    mantendo usuários, unidades e metas intactos."""
    conn = get_conn()
    conn.execute("DELETE FROM projetos")
    conn.commit(); conn.close()

def kpis_unidade(unidade_nome, ano):
    get_engine()
    projetos = listar_projetos(unidade_nome)
    meta     = get_meta(unidade_nome, ano)
    hoje     = date.today()

    prev_uni_mes  = {m:0.0 for m in range(1,13)}
    prev_cust_mes = {m:0.0 for m in range(1,13)}
    real_mes      = {m:0.0 for m in range(1,13)}
    total_prev_uni= 0.0
    total_validado= 0.0
    total_extra   = 0.0

    for p in projetos:
        extra = is_extra_dre(p["tipo"])
        curva_uni  = get_curva_unidade(p["id"])
        curva_cust = get_curva_custos(p["id"])

        if extra:
            # Extra DRE: soma frações dos meses JÁ PASSADOS (inclusive mês atual)
            for (y,m),v in curva_uni.items():
                if y==ano and date(y,m,1) <= date(hoje.year,hoje.month,1):
                    total_extra += v
        else:
            for mes in range(1,13):
                vu = curva_uni.get((ano,mes),0)
                vc = curva_cust.get((ano,mes),0)
                prev_uni_mes[mes]  += vu
                prev_cust_mes[mes] += vc
                total_prev_uni     += vu
            curva_sav = get_curva_saving(p["id"])
            total_validado += sum(v for (y,m),v in curva_sav.items() if y==ano)

    for l in get_lancamentos(unidade_nome=unidade_nome, ano=ano):
        p_tipo = next((p["tipo"] for p in projetos if p["id"]==l["projeto_id"]),"")
        if not is_extra_dre(p_tipo):
            real_mes[l["mes"]] += l["valor_real"]

    total_real = sum(real_mes.values())

    return {
        "n_projetos":         len(projetos),
        "previsto":           total_prev_uni,
        "validado":           total_validado,
        "real":               total_real,
        "extra_dre":          total_extra,
        "meta":               meta,
        "pct_meta":           total_real/meta*100 if meta>0 else 0,
        "prev_mensal_uni":    [prev_uni_mes[m]  for m in range(1,13)],
        "prev_mensal_custos": [prev_cust_mes[m] for m in range(1,13)],
        "real_mensal":        [real_mes[m]       for m in range(1,13)],
        "prev_mensal":        [prev_uni_mes[m]  for m in range(1,13)],
        "projetos":           projetos,
    }

# Inicializa ao importar
get_engine()

# ── Funções analíticas — Dashboard estratégico ──────────────────────────────

def funil_conversao(ano, unidade_nome=None):
    """Funil Meta do Grupo -> Previsto -> Validado por Custos -> Real,
    para o ano informado. unidade_nome=None agrega o grupo inteiro."""
    metas = get_todas_metas(ano)
    meta = sum(m["valor"] for m in metas if (unidade_nome is None or m["nome"]==unidade_nome))

    projetos = listar_projetos(unidade_nome)
    previsto = validado = 0.0
    for p in projetos:
        if is_extra_dre(p["tipo"]): continue
        curva = get_curva_unidade(p["id"])
        previsto += sum(v for (y,m),v in curva.items() if y==ano)
        curva_s = get_curva_saving(p["id"])
        validado += sum(v for (y,m),v in curva_s.items() if y==ano)

    real = 0.0
    for l in get_lancamentos(unidade_nome=unidade_nome, ano=ano):
        if not is_extra_dre(l.get("tipo","")):
            real += l["valor_real"]

    return {"meta":meta, "previsto":previsto, "validado":validado, "real":real,
            "pct_meta": (real/meta*100) if meta>0 else 0}

def saving_por_unidade(ano, tipo_unidade=None):
    """Saving validado por unidade (rateado no ano), opcionalmente filtrado
    por tipo de unidade ('planta' ou 'area'). Só retorna unidades com valor."""
    unidades = listar_unidades()
    if tipo_unidade:
        unidades = [u for u in unidades if u["tipo"]==tipo_unidade]
    resultado = []
    for u in unidades:
        total = 0.0
        for p in listar_projetos(u["nome"]):
            if is_extra_dre(p["tipo"]): continue
            curva_s = get_curva_saving(p["id"])
            total += sum(v for (y,m),v in curva_s.items() if y==ano)
        if total > 0:
            resultado.append({"unidade":u["nome"], "valor":total})
    resultado.sort(key=lambda x:-x["valor"])
    return resultado

def distribuicao_por_tipo(ano, unidade_nome=None):
    """Previsto/Validado/Real por tipo de projeto, rateados no ano informado."""
    projetos = listar_projetos(unidade_nome)
    tipos = {}
    for p in projetos:
        t = p["tipo"]
        d = tipos.setdefault(t, {"previsto":0.0,"validado":0.0,"real":0.0,
                                  "extra":is_extra_dre(t)})
        curva = get_curva_unidade(p["id"])
        d["previsto"] += sum(v for (y,m),v in curva.items() if y==ano)
        curva_s = get_curva_saving(p["id"])
        d["validado"] += sum(v for (y,m),v in curva_s.items() if y==ano)
    for l in get_lancamentos(unidade_nome=unidade_nome, ano=ano):
        t = l.get("tipo","")
        if t in tipos:
            tipos[t]["real"] += l["valor_real"]
    return tipos

def resumo_por_pilar(unidade_nome=None):
    """Qtd de projetos, saving previsto/validado totais (não rateados) e
    real acumulado HISTÓRICO (todos os anos) por tipo de projeto."""
    projetos = listar_projetos(unidade_nome)
    pilares = {}
    for p in projetos:
        t = p["tipo"]
        d = pilares.setdefault(t, {"qtd":0,"previsto":0.0,"validado":0.0,
                                    "real_total":0.0,"extra":is_extra_dre(t)})
        d["qtd"] += 1
        d["previsto"] += p["previsto_unidade"] or 0
        d["validado"] += p["saving_validado"] or 0
    for l in get_lancamentos(unidade_nome=unidade_nome):
        t = l.get("tipo","")
        if t in pilares:
            pilares[t]["real_total"] += l["valor_real"]
    return pilares

def get_carry_over(ano_ref, unidade_nome=None):
    """Meses da curva de projetos DRE que caem FORA do ano de referência —
    parte do previsto que 'sai' do ano vigente (geralmente por causa de um
    'Ganho a partir de' fora de janeiro, que joga meses pro ano seguinte)."""
    projetos = listar_projetos(unidade_nome)
    fora = []
    for p in projetos:
        if is_extra_dre(p["tipo"]): continue
        curva = get_curva_unidade(p["id"])
        for (y,m),v in curva.items():
            if y != ano_ref and v > 0:
                fora.append({"projeto":p["nome"], "unidade":p["unidade_nome"],
                            "proj_id":p["id"], "ano":y, "mes":m, "valor":v,
                            "direcao":"anterior" if y<ano_ref else "seguinte"})
    fora.sort(key=lambda x:(x["ano"],x["mes"]))
    return fora
