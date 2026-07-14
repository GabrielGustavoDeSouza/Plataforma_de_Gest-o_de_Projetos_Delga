"""
database.py — Banco de dados SQLite da Plataforma Delga
Gerencia usuários, unidades, projetos e lançamentos mensais.
"""
import sqlite3, hashlib, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "plataforma.db")

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Cria todas as tabelas e popula dados iniciais."""
    conn = get_conn()
    c = conn.cursor()

    # Usuários
    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT NOT NULL,
            email     TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            perfil    TEXT NOT NULL DEFAULT 'operador',  -- admin | gestor | operador
            unidade   TEXT,                              -- NULL = acesso global
            ativo     INTEGER DEFAULT 1,
            criado_em TEXT DEFAULT (datetime('now'))
        )
    """)

    # Unidades / Departamentos
    c.execute("""
        CREATE TABLE IF NOT EXISTS unidades (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            nome     TEXT UNIQUE NOT NULL,
            tipo     TEXT NOT NULL,  -- planta | area
            meta_anual REAL DEFAULT 0
        )
    """)

    # Projetos
    c.execute("""
        CREATE TABLE IF NOT EXISTS projetos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            unidade_id   INTEGER NOT NULL REFERENCES unidades(id),
            nome         TEXT NOT NULL,
            tipo         TEXT NOT NULL,  -- BSW | Kaizen | Redução de Custo | ...
            responsavel  TEXT,
            descricao    TEXT,
            previsto_rs  REAL DEFAULT 0,
            inicio       TEXT,
            termino      TEXT,
            status       TEXT DEFAULT 'Não iniciado',
            onde_parado  TEXT,
            data_lib     TEXT,
            validado_ok  TEXT DEFAULT 'Pendente',
            saving_valid REAL DEFAULT 0,
            criado_em    TEXT DEFAULT (datetime('now')),
            criado_por   INTEGER REFERENCES usuarios(id)
        )
    """)

    # Lançamentos mensais (real acumulado por projeto por mês)
    c.execute("""
        CREATE TABLE IF NOT EXISTS lancamentos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER NOT NULL REFERENCES projetos(id),
            ano        INTEGER NOT NULL,
            mes        INTEGER NOT NULL,  -- 1-12
            valor_real REAL DEFAULT 0,
            observacao TEXT,
            lancado_em TEXT DEFAULT (datetime('now')),
            lancado_por INTEGER REFERENCES usuarios(id),
            UNIQUE(projeto_id, ano, mes)
        )
    """)

    # Inserir unidades padrão Delga
    unidades_padrao = [
        ("Diadema",      "planta"),
        ("Ferraz",       "planta"),
        ("São Leopoldo", "planta"),
        ("Jarinu",       "planta"),
        ("Anchieta",     "planta"),
        ("Compras",      "area"),
        ("Vendas",       "area"),
        ("Corporativo",  "area"),
    ]
    for nome, tipo in unidades_padrao:
        c.execute("INSERT OR IGNORE INTO unidades (nome, tipo) VALUES (?, ?)", (nome, tipo))

    # Usuário admin padrão
    admin_hash = hashlib.sha256("Delga@2026".encode()).hexdigest()
    c.execute("""
        INSERT OR IGNORE INTO usuarios (nome, email, senha_hash, perfil, unidade)
        VALUES ('Administrador', 'admin@delga.com.br', ?, 'admin', NULL)
    """, (admin_hash,))

    conn.commit()
    conn.close()

# ── Autenticação ───────────────────────────────────────────────────────────────
def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode()).hexdigest()

def autenticar(email: str, senha: str):
    """Retorna dict do usuário ou None se credenciais inválidas."""
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE email=? AND senha_hash=? AND ativo=1",
        (email.strip().lower(), hash_senha(senha))
    ).fetchone()
    conn.close()
    return dict(row) if row else None

# ── Usuários ───────────────────────────────────────────────────────────────────
def listar_usuarios():
    conn = get_conn()
    rows = conn.execute("SELECT u.*, un.nome as unidade_nome FROM usuarios u LEFT JOIN unidades un ON u.unidade=un.nome ORDER BY u.nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def criar_usuario(nome, email, senha, perfil, unidade):
    conn = get_conn()
    conn.execute(
        "INSERT INTO usuarios (nome, email, senha_hash, perfil, unidade) VALUES (?,?,?,?,?)",
        (nome, email.lower(), hash_senha(senha), perfil, unidade)
    )
    conn.commit(); conn.close()

def alterar_senha(user_id, nova_senha):
    conn = get_conn()
    conn.execute("UPDATE usuarios SET senha_hash=? WHERE id=?", (hash_senha(nova_senha), user_id))
    conn.commit(); conn.close()

# ── Unidades ───────────────────────────────────────────────────────────────────
def listar_unidades(tipo=None):
    conn = get_conn()
    if tipo:
        rows = conn.execute("SELECT * FROM unidades WHERE tipo=? ORDER BY nome", (tipo,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM unidades ORDER BY tipo, nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def atualizar_meta(unidade_nome, meta):
    conn = get_conn()
    conn.execute("UPDATE unidades SET meta_anual=? WHERE nome=?", (meta, unidade_nome))
    conn.commit(); conn.close()

# ── Projetos ───────────────────────────────────────────────────────────────────
TIPOS_PROJETO = [
    "BSW", "Kaizen", "Kaizen - Ganho Recorrente", "Kaizen - Custo Evitado",
    "Kaizen - Capital de Giro", "Redução de Custo", "Você Resolve",
    "Meta Executiva", "Estratégia Comercial",
]

STATUS_PROJETO = ["📝 Não iniciado", "⏳ Em Execução", "✓ Concluído", "⚠️ Suspenso"]

def listar_projetos(unidade_nome=None):
    conn = get_conn()
    if unidade_nome:
        rows = conn.execute("""
            SELECT p.*, u.nome as unidade_nome FROM projetos p
            JOIN unidades u ON p.unidade_id=u.id
            WHERE u.nome=? ORDER BY p.tipo, p.nome
        """, (unidade_nome,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT p.*, u.nome as unidade_nome FROM projetos p
            JOIN unidades u ON p.unidade_id=u.id ORDER BY u.nome, p.tipo, p.nome
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def criar_projeto(unidade_nome, nome, tipo, responsavel, descricao,
                  previsto_rs, inicio, termino, user_id):
    conn = get_conn()
    u = conn.execute("SELECT id FROM unidades WHERE nome=?", (unidade_nome,)).fetchone()
    conn.execute("""
        INSERT INTO projetos (unidade_id, nome, tipo, responsavel, descricao,
                              previsto_rs, inicio, termino, criado_por)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (u["id"], nome, tipo, responsavel, descricao, previsto_rs, inicio, termino, user_id))
    conn.commit(); conn.close()

def atualizar_projeto(proj_id, campos: dict):
    """campos = dict com apenas os campos a atualizar."""
    conn = get_conn()
    sets = ", ".join(f"{k}=?" for k in campos)
    vals = list(campos.values()) + [proj_id]
    conn.execute(f"UPDATE projetos SET {sets} WHERE id=?", vals)
    conn.commit(); conn.close()

def deletar_projeto(proj_id):
    conn = get_conn()
    conn.execute("DELETE FROM lancamentos WHERE projeto_id=?", (proj_id,))
    conn.execute("DELETE FROM projetos WHERE id=?", (proj_id,))
    conn.commit(); conn.close()

# ── Lançamentos mensais ────────────────────────────────────────────────────────
def lancar_real(projeto_id, ano, mes, valor, obs, user_id):
    conn = get_conn()
    conn.execute("""
        INSERT INTO lancamentos (projeto_id, ano, mes, valor_real, observacao, lancado_por)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(projeto_id, ano, mes) DO UPDATE SET
            valor_real=excluded.valor_real,
            observacao=excluded.observacao,
            lancado_em=datetime('now'),
            lancado_por=excluded.lancado_por
    """, (projeto_id, ano, mes, valor, obs, user_id))
    conn.commit(); conn.close()

def get_lancamentos(unidade_nome=None, ano=None):
    conn = get_conn()
    q = """
        SELECT l.*, p.nome as proj_nome, p.tipo, p.previsto_rs, p.saving_valid,
               u.nome as unidade_nome
        FROM lancamentos l
        JOIN projetos p ON l.projeto_id=p.id
        JOIN unidades u ON p.unidade_id=u.id
        WHERE 1=1
    """
    params = []
    if unidade_nome: q += " AND u.nome=?"; params.append(unidade_nome)
    if ano:          q += " AND l.ano=?";  params.append(ano)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── KPIs calculados ────────────────────────────────────────────────────────────
def kpis_unidade(unidade_nome, ano=None):
    ano = ano or datetime.now().year
    projetos = listar_projetos(unidade_nome)
    lancamentos = get_lancamentos(unidade_nome, ano)

    real_por_mes = {m: 0.0 for m in range(1, 13)}
    for l in lancamentos:
        real_por_mes[l["mes"]] += l["valor_real"]

    total_previsto = sum(p["previsto_rs"] for p in projetos)
    total_validado = sum(p["saving_valid"] for p in projetos)
    total_real     = sum(real_por_mes.values())
    unidade        = next((u for u in listar_unidades() if u["nome"]==unidade_nome), {})
    meta           = unidade.get("meta_anual", 0) or 1

    return {
        "n_projetos":  len(projetos),
        "previsto":    total_previsto,
        "validado":    total_validado,
        "real":        total_real,
        "meta":        meta,
        "pct_meta":    total_real / meta * 100,
        "real_mensal": [real_por_mes[m] for m in range(1, 13)],
        "projetos":    projetos,
    }

# Inicializa ao importar
init_db()
