Como Resolver o Erro AttributeError no Streamlit? - Manus

Compartilhar
pasted_content.txt
Texto · 13.37 KB
o cod hoje é esse
Max
Recebi o código. Vou localizar a criação da conexão e a função criar_projeto para identificar exatamente por que lastrowid está falhando.
Max
O erro está exatamente nesta linha do database.py:
Python
pid = conn.lastrowid
No SQLite, lastrowid pertence ao cursor, não à conexão. Como conn é um objeto sqlite3.Connection, o Python gera AttributeError. Isso não tem relação com seus créditos do Claude; é um erro de código no acesso ao banco.
Parte
Situação
conn.lastrowid
Incorreto
cursor.lastrowid
Correto
Mensagem “redacted”
O Streamlit Cloud esconde o texto original do erro por segurança
Substitua a função criar_projeto por esta versão:
Python
def criar_projeto(unidade_nome, dados, user_id):
    init_db()
    conn = get_conn()

    u = conn.execute(
        "SELECT id FROM unidades WHERE nome=?",
        (unidade_nome,),
    ).fetchone()

    if not u:
        conn.close()
        raise ValueError(f"Unidade não encontrada: {unidade_nome}")

    cursor = conn.execute(
        """INSERT INTO projetos (
            unidade_id, nome, tipo, va_ggf, responsavel, descricao, obs,
            inicio, termino, mes_primeiro_retorno, previsto_unidade,
            status, atividade_atual, data_conclusao_ativ, onde_parado,
            data_lib, criado_por, atualizado_por
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            u["id"],
            dados["nome"],
            dados["tipo"],
            dados.get("va_ggf"),
            dados.get("responsavel"),
            dados.get("descricao"),
            dados.get("obs"),
            dados.get("inicio"),
            dados.get("termino"),
            dados.get("mes_primeiro_retorno"),
            dados.get("previsto_unidade", 0),
            dados.get("status", "📝 Não iniciado"),
            dados.get("atividade_atual"),
            dados.get("data_conclusao_ativ"),
            dados.get("onde_parado"),
            dados.get("data_lib"),
            user_id,
            user_id,
        ),
    )

    pid = cursor.lastrowid
    conn.commit()
    conn.close()
    return pid
A correção essencial é:
Python
cursor = conn.execute("INSERT ...", valores)
pid = cursor.lastrowid
Depois de alterar o arquivo, faça o commit e push para o GitHub. O Streamlit Cloud normalmente detectará a atualização e reiniciará o aplicativo.
Há ainda um ponto importante: seu banco está configurado como:
Python
DB_PATH = "/tmp/plataforma_delga.db"
No Streamlit Cloud, /tmp é armazenamento temporário. O banco pode ser perdido quando o aplicativo reiniciar ou for recriado. Para uso real, considere um banco persistente, como PostgreSQL ou Supabase. Isso não causou o erro atual, mas pode causar perda futura dos projetos cadastrados.
Referência
[1] Documentação do Python — sqlite3.Cursor.lastrowid

me devolva ocod completo nao gosto de ficar recortando
Max
Claro. Vou devolver o database.py completo, já com a correção aplicada, para você substituir o arquivo inteiro sem precisar recortar trechos.
Formatação de Código para Evitar Quebras de Linha


Max
Segue o database.py completo e corrigido. Basta baixar e substituir integralmente o arquivo atual no seu projeto. A sintaxe foi validada e a criação de projeto foi testada com sucesso, retornando corretamente o novo ID.
database.py
Código · 13.20 KB
Ver todos os arquivos nesta tarefa
Tarefa concluída
Como foi este resultado?




Manus is an AI Agent and can make mistakes. Please double-check before use.

import sqlite3, hashlib, os
from datetime import datetime, date

DB_PATH = "/tmp/plataforma_delga.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL, perfil TEXT NOT NULL DEFAULT 'operador',
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

TIPOS_PROJETO = ["BSW","Kaizen","Kaizen - Ganho Recorrente","Kaizen - Custo Evitado",
    "Kaizen - Capital de Giro","Redução de Custo","Você Resolve","Meta Executiva","Estratégia Comercial"]
VA_GGF_OPTS = ["VA","GGF","Material Auxiliar"]
STATUS_OPTS = ["📝 Não iniciado","⏳ Em Execução","✓ Concluído","⚠️ Suspenso"]
MESES_PT = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

def autenticar(email, senha):
    init_db()
    conn = get_conn()
    row = conn.execute("SELECT * FROM usuarios WHERE email=? AND senha_hash=? AND ativo=1",
        (email.strip().lower(), hash_senha(senha))).fetchone()
    conn.close()
    return dict(row) if row else None

def listar_usuarios():
    init_db()
    conn = get_conn()
    rows = conn.execute("SELECT * FROM usuarios ORDER BY nome").fetchall()
    conn.close(); return [dict(r) for r in rows]

def criar_usuario(nome, email, senha, perfil, unidade):
    init_db()
    conn = get_conn()
    conn.execute("INSERT INTO usuarios (nome,email,senha_hash,perfil,unidade) VALUES (?,?,?,?,?)",
        (nome, email.lower(), hash_senha(senha), perfil, unidade or None))
    conn.commit(); conn.close()

def alterar_senha(user_id, nova):
    conn = get_conn()
    conn.execute("UPDATE usuarios SET senha_hash=? WHERE id=?",(hash_senha(nova),user_id))
    conn.commit(); conn.close()

def listar_unidades(so_ativas=True):
    init_db()
    conn = get_conn()
    q = "SELECT * FROM unidades" + (" WHERE ativo=1" if so_ativas else "") + " ORDER BY tipo,nome"
    rows = conn.execute(q).fetchall()
    conn.close(); return [dict(r) for r in rows]

def criar_unidade(nome, tipo):
    init_db()
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO unidades (nome,tipo) VALUES (?,?)",(nome,tipo))
    conn.commit(); conn.close()

def get_meta(unidade_nome, ano):
    init_db()
    conn = get_conn()
    row = conn.execute("""SELECT m.valor FROM metas m JOIN unidades u ON m.unidade_id=u.id
        WHERE u.nome=? AND m.ano=?""",(unidade_nome,ano)).fetchone()
    conn.close(); return row["valor"] if row else 0.0

def set_meta(unidade_nome, ano, valor):
    init_db()
    conn = get_conn()
    u = conn.execute("SELECT id FROM unidades WHERE nome=?",(unidade_nome,)).fetchone()
    if u:
        conn.execute("""INSERT INTO metas (unidade_id,ano,valor) VALUES (?,?,?)
            ON CONFLICT(unidade_id,ano) DO UPDATE SET valor=excluded.valor""",
            (u["id"],ano,valor))
    conn.commit(); conn.close()

def get_todas_metas(ano):
    init_db()
    conn = get_conn()
    rows = conn.execute("""SELECT u.nome,u.tipo,COALESCE(m.valor,0) as valor
        FROM unidades u LEFT JOIN metas m ON u.id=m.unidade_id AND m.ano=?
        WHERE u.ativo=1 ORDER BY u.tipo,u.nome""",(ano,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def listar_projetos(unidade_nome=None, incluir_campeao=False):
    init_db()
    conn = get_conn()
    q = """SELECT p.*,u.nome as unidade_nome,u.tipo as unidade_tipo
        FROM projetos p JOIN unidades u ON p.unidade_id=u.id WHERE 1=1"""
    params = []
    if unidade_nome: q += " AND u.nome=?"; params.append(unidade_nome)
    if not incluir_campeao: q += " AND p.campeao=0"
    q += " ORDER BY p.check_formalizado ASC,p.criado_em ASC"
    rows = conn.execute(q,params).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_projeto(proj_id):
    init_db()
    conn = get_conn()
    row = conn.execute("""SELECT p.*,u.nome as unidade_nome FROM projetos p
        JOIN unidades u ON p.unidade_id=u.id WHERE p.id=?""",(proj_id,)).fetchone()
    conn.close(); return dict(row) if row else None

def criar_projeto(unidade_nome, dados, user_id):
    init_db()
    conn = get_conn()
    u = conn.execute("SELECT id FROM unidades WHERE nome=?", (unidade_nome,)).fetchone()

    if not u:
        conn.close()
        raise ValueError(f"Unidade não encontrada: {unidade_nome}")

    cursor = conn.execute("""INSERT INTO projetos (unidade_id,nome,tipo,va_ggf,responsavel,descricao,obs,
        inicio,termino,mes_primeiro_retorno,previsto_unidade,status,atividade_atual,
        data_conclusao_ativ,onde_parado,data_lib,criado_por,atualizado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (u["id"],dados["nome"],dados["tipo"],dados.get("va_ggf"),dados.get("responsavel"),
         dados.get("descricao"),dados.get("obs"),dados.get("inicio"),dados.get("termino"),
         dados.get("mes_primeiro_retorno"),dados.get("previsto_unidade",0),
         dados.get("status","📝 Não iniciado"),dados.get("atividade_atual"),
         dados.get("data_conclusao_ativ"),dados.get("onde_parado"),dados.get("data_lib"),
         user_id,user_id))

    pid = cursor.lastrowid
    conn.commit()
    conn.close()
    return pid

def atualizar_projeto(proj_id, campos, user_id):
    campos["ultima_atualizacao"] = datetime.now().isoformat()
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
            mpr_str = str(p["mes_primeiro_retorno"])[:7]
            mpr = datetime.strptime(mpr_str, "%Y-%m").date()
            ano_c = mpr.year + (mpr.month + 11) // 12
            mes_c = (mpr.month + 11) % 12 + 1
            if hoje >= date(ano_c, mes_c, 1):
                conn.execute("UPDATE projetos SET campeao=1,campeao_em=? WHERE id=?",
                             (hoje.isoformat(),p["id"]))
        except: pass
    conn.commit(); conn.close()

def get_links(proj_id):
    init_db()
    conn = get_conn()
    rows = conn.execute("SELECT * FROM projeto_links WHERE projeto_id=? ORDER BY id",(proj_id,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def add_link(proj_id, titulo, url):
    conn = get_conn()
    conn.execute("INSERT INTO projeto_links (projeto_id,titulo,url) VALUES (?,?,?)",(proj_id,titulo,url))
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
    init_db()
    conn = get_conn()
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

def get_real_por_mes(unidade_nome, ano):
    lancs = get_lancamentos(unidade_nome=unidade_nome, ano=ano)
    r = {m: 0.0 for m in range(1,13)}
    for l in lancs: r[l["mes"]] += l["valor_real"]
    return r

def get_previsto_curva(proj_id):
    p = get_projeto(proj_id)
    if not p or not p.get("mes_primeiro_retorno"): return {}
    valor = p["previsto_custos"] if p["previsto_custos"]>0 else p["previsto_unidade"]
    if valor<=0: return {}
    mensal = valor/12
    try:
        mpr = datetime.strptime(str(p["mes_primeiro_retorno"])[:7],"%Y-%m")
    except: return {}
    curva = {}
    for i in range(12):
        mes = (mpr.month-1+i)%12+1
        ano = mpr.year+(mpr.month-1+i)//12
        curva[(ano,mes)] = mensal
    return curva

def alertas_pendentes(unidade_nome=None):
    projetos = listar_projetos(unidade_nome)
    hoje = date.today(); alertas = []
    for p in projetos:
        if not p.get("mes_primeiro_retorno"): continue
        curva = get_previsto_curva(p["id"])
        lancs = {(l["ano"],l["mes"]) for l in get_lancamentos(proj_id=p["id"])}
        for (ano,mes) in curva:
            if date(ano,mes,1)<date(hoje.year,hoje.month,1) and (ano,mes) not in lancs:
                alertas.append({"projeto":p["nome"],"unidade":p["unidade_nome"],"ano":ano,"mes":mes,"proj_id":p["id"]})
    return alertas

def kpis_unidade(unidade_nome, ano):
    init_db()
    projetos = listar_projetos(unidade_nome)
    real_mes = get_real_por_mes(unidade_nome, ano)
    meta = get_meta(unidade_nome, ano)
    prev_mes = {m:0.0 for m in range(1,13)}
    for p in projetos:
        for (y,m),v in get_previsto_curva(p["id"]).items():
            if y==ano: prev_mes[m]+=v
    total_prev = sum(p["previsto_custos"] if p["previsto_custos"]>0 else p["previsto_unidade"] for p in projetos)
    total_val  = sum(p["saving_validado"] for p in projetos)
    total_real = sum(real_mes.values())
    return {
        "n_projetos":  len(projetos),
        "previsto":    total_prev,
        "validado":    total_val,
        "real":        total_real,
        "meta":        meta,
        "pct_meta":    total_real/meta*100 if meta>0 else 0,
        "prev_mensal": [prev_mes[m] for m in range(1,13)],
        "real_mensal": [real_mes[m] for m in range(1,13)],
        "projetos":    projetos,
    }

init_db()
