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
    """Garante que o banco existe e está com o schema atualizado. init_db()
    é idempotente (CREATE TABLE IF NOT EXISTS + ALTER TABLE em try/except),
    então rodar sempre aqui — não só quando o arquivo não existe — garante
    que uma coluna/tabela nova apareça mesmo se a primeira página acessada
    depois de um deploy não for o Dashboard Global."""
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
        ganho_unico INTEGER DEFAULT 0,
        origem TEXT DEFAULT 'aplicado',
        numero_projeto TEXT, lider_projeto TEXT, integrantes TEXT, revisao TEXT,
        replanejamentos INTEGER DEFAULT 0,
        criado_em TEXT DEFAULT (datetime('now')),
        criado_por INTEGER REFERENCES usuarios(id),
        ultima_atualizacao TEXT DEFAULT (datetime('now')),
        atualizado_por INTEGER REFERENCES usuarios(id))""")
    # Migração leve — adiciona a coluna se o banco já existia sem ela
    for _sql in [
        "ALTER TABLE projetos ADD COLUMN ganho_unico INTEGER DEFAULT 0",
        "ALTER TABLE projetos ADD COLUMN origem TEXT DEFAULT 'aplicado'",
        "ALTER TABLE projetos ADD COLUMN numero_projeto TEXT",
        "ALTER TABLE projetos ADD COLUMN lider_projeto TEXT",
        "ALTER TABLE projetos ADD COLUMN integrantes TEXT",
        "ALTER TABLE projetos ADD COLUMN revisao TEXT",
        "ALTER TABLE projetos ADD COLUMN replanejamentos INTEGER DEFAULT 0",
    ]:
        try: c.execute(_sql)
        except sqlite3.OperationalError: pass
    c.execute("""CREATE TABLE IF NOT EXISTS projeto_a3 (
        projeto_id INTEGER PRIMARY KEY REFERENCES projetos(id) ON DELETE CASCADE,
        objetivo_geral TEXT, proposta_desenvolvimento TEXT, situacao_atual TEXT,
        metas_entregas TEXT, premissas_restricoes TEXT, acompanhamento_indicadores TEXT,
        atualizado_em TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS projeto_a3_midias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
        campo TEXT NOT NULL,
        nome_arquivo TEXT, mime_type TEXT, dados_b64 TEXT,
        criado_em TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS projeto_evidencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
        nome_arquivo TEXT, mime_type TEXT, dados_b64 TEXT,
        criado_em TEXT DEFAULT (datetime('now')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS projeto_atividades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        projeto_id INTEGER NOT NULL REFERENCES projetos(id) ON DELETE CASCADE,
        ordem INTEGER NOT NULL DEFAULT 0,
        nome TEXT NOT NULL, responsavel TEXT,
        inicio_previsto TEXT, termino_previsto TEXT,
        progresso_real REAL DEFAULT 0, acao TEXT,
        criado_em TEXT DEFAULT (datetime('now')))""")
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

def normalizar_valor_lista(valor, opcoes):
    """Casa 'valor' (vindo de uma planilha, com acento/caixa variável) com a
    opção oficial mais parecida da lista. Retorna a opção oficial ou None."""
    import unicodedata
    def _norm(s):
        s = str(s or "").strip().lower()
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        return s
    alvo = _norm(valor)
    if not alvo: return None
    for op in opcoes:
        if _norm(op) == alvo:
            return op
    # tenta por substring (ex: "kaizen ganho recorrente" ~ "Kaizen - Ganho Recorrente")
    for op in opcoes:
        if alvo in _norm(op) or _norm(op) in alvo:
            return op
    return None

def anualizar_valor_custos(valor_bruto, mes_primeiro_retorno_str, ano_referencia=None):
    """Custos normalmente calcula o saving 'do primeiro ganho até dezembro
    DO ANO CORRENTE', não os 12 meses cheios que o sistema espera para
    ratear. Esta função reverte essa conta: valor_mensal x 12 = valor
    anualizado — mas SÓ quando o primeiro retorno é do ano de referência;
    projetos com retorno em ano passado ou futuro usam o valor como está,
    pois a premissa 'até dezembro deste ano' não se aplica a eles."""
    ano_referencia = ano_referencia or datetime.now().year
    # NaN (célula vazia lida via pandas) é "verdadeiro" em Python, então
    # precisa de checagem própria — sem isso o cálculo abaixo produz NaN,
    # que o SQLite grava como NULL silenciosamente.
    if valor_bruto is None or valor_bruto != valor_bruto:
        valor_bruto = 0
    try:
        dt = datetime.strptime(str(mes_primeiro_retorno_str)[:7], "%Y-%m")
    except Exception:
        return None
    if not valor_bruto: return 0.0
    if dt.year != ano_referencia:
        try: return round(float(valor_bruto), 2)
        except (ValueError, TypeError): return None
    meses_restantes = 13 - dt.month
    if meses_restantes <= 0 or meses_restantes > 12: return None
    try:
        return round(float(valor_bruto) / meses_restantes * 12, 2)
    except (ValueError, TypeError):
        return None

def importar_projetos_lote(linhas, criado_por_id):
    """Importa uma lista de dicts (uma linha de planilha cada) como projetos.
    Cada linha já deve vir validada/normalizada. Retorna (sucesso, erros)."""
    sucesso, erros = [], []
    for i, l in enumerate(linhas, start=1):
        try:
            valor_anual = anualizar_valor_custos(l.get("valor_custos_bruto"), l["mes_primeiro_retorno"])
            pid = criar_projeto(l["unidade"], {
                "nome": l["nome"], "tipo": l["tipo"], "va_ggf": l["va_ggf"],
                "responsavel": l.get("responsavel",""), "descricao": l.get("descricao",""),
                "obs": "[Importado via Excel]",
                "inicio": l.get("inicio",""), "termino": l.get("termino",""),
                "mes_primeiro_retorno": l["mes_primeiro_retorno"],
                "previsto_unidade": l["previsto_unidade"],
                "status": l.get("status") or "⏳ Em Execução",
                "check_a3": 1, "check_memoria": 1, "check_formalizado": 1,
            }, criado_por_id)
            campos_extra = {}
            if l.get("validacao") in ("OK","NOK"):
                campos_extra["validador_ok"] = l["validacao"]
            if valor_anual is not None:
                campos_extra["previsto_custos"] = valor_anual
                campos_extra["saving_validado"] = valor_anual if l.get("validacao")=="OK" else 0.0
            if campos_extra:
                atualizar_projeto(pid, campos_extra, criado_por_id)
            sucesso.append({"linha": i, "nome": l["nome"], "id": pid})
        except Exception as e:
            erros.append({"linha": i, "nome": l.get("nome","?"), "erro": str(e)})
    return sucesso, erros

def exportar_backup_completo():
    """Gera o backup completo (projetos com real mês a mês embutido + metas +
    usuários + A3 + Estrutura + evidências) em listas de dicts prontas pra
    virar planilha de várias abas. Formato que a própria plataforma sabe
    reler 100%, pensado pra 'zerei hoje, recupero amanhã' sem perder nada —
    incluindo os projetos no formato novo (A3/Estrutura/Gantt)."""
    projetos = listar_projetos(incluir_campeao=True)

    # Descobre todos os (ano,mes) com lançamento em qualquer projeto, pra criar
    # as colunas de Real dinamicamente — funciona mesmo depois de virar o ano.
    lancs_por_projeto = {}
    meses_com_real = set()
    for p in projetos:
        mapa = {(l["ano"],l["mes"]): l["valor_real"] for l in get_lancamentos(proj_id=p["id"])}
        lancs_por_projeto[p["id"]] = mapa
        meses_com_real.update(mapa.keys())
    meses_ordenados = sorted(meses_com_real)

    def _sn(v): return "Sim" if v else "Não"

    linhas_proj = []
    for p in projetos:
        linha = {
            "Unidade": p["unidade_nome"], "Tipo": p["tipo"], "VA/GGF": p.get("va_ggf") or "",
            "Nome do Projeto": p["nome"], "Descrição": p.get("descricao") or "",
            "Responsável": p.get("responsavel") or "",
            "Data Início": str(p.get("inicio") or ""), "Data Fim": str(p.get("termino") or ""),
            "Valor Previsto": p.get("previsto_unidade") or 0,
            "Mês Primeiro Retorno": str(p.get("mes_primeiro_retorno") or ""),
            "Ganho Único": _sn(p.get("ganho_unico")),
            "Validação": p.get("validador_ok") or "Pendente",
            "Valor Calculado Custos": p.get("previsto_custos") or 0,
            "Saving Validado": p.get("saving_validado") or 0,
            "Status": p.get("status") or "",
            "Check A3": _sn(p.get("check_a3")),
            "Check Memória": _sn(p.get("check_memoria")),
            "Check Formalizado": _sn(p.get("check_formalizado")),
            "Atividade Atual": p.get("atividade_atual") or "",
            "Responsável Atividade": p.get("onde_parado") or "",
            "Previsão Conclusão": p.get("data_conclusao_ativ") or "",
            "Observações": p.get("obs") or "",
            "Origem": p.get("origem") or "aplicado",
            "Nº Projeto": p.get("numero_projeto") or "",
            "Líder do Projeto": p.get("lider_projeto") or "",
            "Integrantes": p.get("integrantes") or "",
            "Revisão": p.get("revisao") or "",
            "Replanejamentos": p.get("replanejamentos") or 0,
        }
        lancs = lancs_por_projeto[p["id"]]
        for (ano_m, mes_m) in meses_ordenados:
            linha[f"Real {mes_m:02d}/{ano_m}"] = lancs.get((ano_m, mes_m), "")
        linhas_proj.append(linha)

    linhas_metas = []
    for u in listar_unidades(so_ativas=False):
        for ano in range(2025,2032):
            m = get_meta(u["nome"], ano)
            if m and m > 0:
                linhas_metas.append({"Unidade": u["nome"], "Ano": ano, "Valor da Meta": m})

    linhas_usuarios = []
    for u in listar_usuarios():
        linhas_usuarios.append({
            "Nome": u["nome"], "Email": u["email"], "Perfil": u["perfil"],
            "Unidade": u.get("unidade") or "", "Ativo": _sn(u.get("ativo")),
            "SenhaHashInterno": u.get("senha_hash") or "",
        })

    # A3 — só exporta projetos que realmente têm algo preenchido
    linhas_a3 = []
    for p in projetos:
        a3 = get_a3(p["id"])
        if any(a3.get(k) for k,_ in CAMPOS_A3):
            row = {"Unidade": p["unidade_nome"], "Nome do Projeto": p["nome"]}
            for k, label in CAMPOS_A3:
                row[label] = a3.get(k) or ""
            linhas_a3.append(row)

    # Estrutura (atividades) — uma linha por atividade
    linhas_atividades = []
    for p in projetos:
        for a in listar_atividades(p["id"]):
            linhas_atividades.append({
                "Unidade": p["unidade_nome"], "Nome do Projeto": p["nome"],
                "Ordem": a["ordem"], "Atividade": a["nome"],
                "Responsável": a.get("responsavel") or "",
                "Início Previsto": str(a.get("inicio_previsto") or ""),
                "Término Previsto": str(a.get("termino_previsto") or ""),
                "% Progresso Real": a.get("progresso_real") or 0,
                "Ação": a.get("acao") or "",
            })

    # Imagens do A3 e evidências — dados em base64 (o backup carrega o
    # arquivo inteiro, senão um restore perderia as evidências anexadas)
    linhas_midias = []
    for p in projetos:
        for m in get_a3_midias(p["id"]):
            linhas_midias.append({
                "Unidade": p["unidade_nome"], "Nome do Projeto": p["nome"],
                "Campo": m["campo"], "Nome Arquivo": m.get("nome_arquivo") or "",
                "Mime Type": m.get("mime_type") or "", "Dados Base64": m.get("dados_b64") or "",
            })

    linhas_evidencias = []
    for p in projetos:
        for e in get_evidencias(p["id"]):
            linhas_evidencias.append({
                "Unidade": p["unidade_nome"], "Nome do Projeto": p["nome"],
                "Nome Arquivo": e.get("nome_arquivo") or "", "Mime Type": e.get("mime_type") or "",
                "Dados Base64": e.get("dados_b64") or "",
            })

    return (linhas_proj, linhas_metas, linhas_usuarios,
            linhas_a3, linhas_atividades, linhas_midias, linhas_evidencias)

def restaurar_backup_completo(linhas_proj, linhas_metas, linhas_usuarios, user_id,
                               linhas_a3=None, linhas_atividades=None,
                               linhas_midias=None, linhas_evidencias=None):
    """Apaga TODOS os projetos e metas atuais e recarrega a partir de um backup
    exportado por exportar_backup_completo — incluindo real mês a mês,
    checklist, validação, ganho único, A3, Estrutura e evidências. Usuários
    já existentes (mesmo e-mail) não são sobrescritos; só os que faltam são
    recriados, com a senha que tinham antes preservada. Os 4 últimos
    parâmetros são opcionais — um backup antigo (sem essas abas) continua
    restaurando normalmente, só sem A3/Estrutura. Operação destrutiva — a
    UI precisa confirmar."""
    linhas_a3 = linhas_a3 or []
    linhas_atividades = linhas_atividades or []
    linhas_midias = linhas_midias or []
    linhas_evidencias = linhas_evidencias or []

    conn = get_conn()
    conn.execute("DELETE FROM projetos")
    conn.execute("DELETE FROM metas")
    conn.commit(); conn.close()

    def _truthy(v): return str(v or "").strip().lower() in ("sim","1","true","yes")

    mapa_id = {}
    erros = []
    for l in linhas_proj:
        try:
            pid = criar_projeto(l["Unidade"], {
                "nome": l["Nome do Projeto"], "tipo": l["Tipo"], "va_ggf": l.get("VA/GGF",""),
                "descricao": l.get("Descrição",""), "responsavel": l.get("Responsável",""),
                "inicio": l.get("Data Início",""), "termino": l.get("Data Fim",""),
                "mes_primeiro_retorno": l.get("Mês Primeiro Retorno") or None,
                "previsto_unidade": l.get("Valor Previsto",0),
                "status": l.get("Status") or "⏳ Em Execução",
                "atividade_atual": l.get("Atividade Atual",""),
                "onde_parado": l.get("Responsável Atividade",""),
                "data_conclusao_ativ": l.get("Previsão Conclusão",""),
                "obs": l.get("Observações",""),
                "check_a3": int(_truthy(l.get("Check A3"))),
                "check_memoria": int(_truthy(l.get("Check Memória"))),
                "check_formalizado": int(_truthy(l.get("Check Formalizado"))),
                "ganho_unico": int(_truthy(l.get("Ganho Único"))),
                "origem": l.get("Origem") or "aplicado",
                "numero_projeto": l.get("Nº Projeto",""),
                "lider_projeto": l.get("Líder do Projeto",""),
                "integrantes": l.get("Integrantes",""),
                "revisao": l.get("Revisão",""),
            }, user_id)
            atualizar_projeto(pid, {
                "validador_ok": l.get("Validação") or "Pendente",
                "previsto_custos": l.get("Valor Calculado Custos",0),
                "saving_validado": l.get("Saving Validado",0),
                "replanejamentos": int(l.get("Replanejamentos") or 0),
            }, user_id)
            mapa_id[(l["Unidade"], l["Nome do Projeto"])] = pid
        except Exception as e:
            erros.append({"nome": l.get("Nome do Projeto","?"), "erro": str(e)})

    n_lanc = 0
    for l in linhas_proj:
        pid = mapa_id.get((l["Unidade"], l["Nome do Projeto"]))
        if not pid: continue
        for chave, valor in l.items():
            if not str(chave).startswith("Real "): continue
            if valor is None or valor == "" or (isinstance(valor,float) and valor!=valor): continue
            try:
                mes_str, ano_str = chave[5:].split("/")
                lancar_real(pid, int(ano_str), int(mes_str), float(valor), "", user_id)
                n_lanc += 1
            except Exception:
                pass

    for m in linhas_metas:
        try: set_meta(m["Unidade"], int(m["Ano"]), m["Valor da Meta"])
        except Exception: pass

    n_usu = 0
    conn = get_conn()
    for u in linhas_usuarios:
        email = str(u.get("Email","")).strip().lower()
        if not email: continue
        existe = conn.execute("SELECT id FROM usuarios WHERE email=?", (email,)).fetchone()
        if existe: continue  # não sobrescreve usuário que já existe (ex: admin padrão)
        senha_hash = u.get("SenhaHashInterno") or hash_senha("Delga@2026")
        try:
            conn.execute(
                "INSERT INTO usuarios (nome,email,senha_hash,perfil,unidade,ativo) VALUES (?,?,?,?,?,?)",
                (u.get("Nome",""), email, senha_hash, u.get("Perfil","facilitador"),
                 u.get("Unidade") or None, int(_truthy(u.get("Ativo","Sim")))))
            n_usu += 1
        except Exception:
            pass
    conn.commit(); conn.close()

    n_a3 = 0
    for l in linhas_a3:
        pid = mapa_id.get((l.get("Unidade"), l.get("Nome do Projeto")))
        if not pid: continue
        try:
            campos = {k: l.get(label,"") for k, label in CAMPOS_A3}
            if any(campos.values()):
                salvar_a3(pid, campos); n_a3 += 1
        except Exception:
            pass

    n_ativ = 0
    for l in linhas_atividades:
        pid = mapa_id.get((l.get("Unidade"), l.get("Nome do Projeto")))
        if not pid: continue
        try:
            add_atividade(pid, {
                "ordem": int(l.get("Ordem") or 0), "nome": l.get("Atividade",""),
                "responsavel": l.get("Responsável",""),
                "inicio_previsto": l.get("Início Previsto") or None,
                "termino_previsto": l.get("Término Previsto") or None,
                "progresso_real": float(l.get("% Progresso Real") or 0),
                "acao": l.get("Ação",""),
            })
            n_ativ += 1
        except Exception:
            pass

    n_mid = 0
    for l in linhas_midias:
        pid = mapa_id.get((l.get("Unidade"), l.get("Nome do Projeto")))
        if not pid or not l.get("Dados Base64"): continue
        try:
            add_a3_midia(pid, l.get("Campo",""), l.get("Nome Arquivo",""),
                         l.get("Mime Type",""), l.get("Dados Base64",""))
            n_mid += 1
        except Exception:
            pass

    n_evid = 0
    for l in linhas_evidencias:
        pid = mapa_id.get((l.get("Unidade"), l.get("Nome do Projeto")))
        if not pid or not l.get("Dados Base64"): continue
        try:
            add_evidencia(pid, l.get("Nome Arquivo",""), l.get("Mime Type",""), l.get("Dados Base64",""))
            n_evid += 1
        except Exception:
            pass

    return len(mapa_id), n_lanc, len(linhas_metas), n_usu, erros, n_a3, n_ativ, n_mid, n_evid

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
        check_a3,check_memoria,check_formalizado,ganho_unico,
        origem,numero_projeto,lider_projeto,integrantes,revisao,
        criado_por,atualizado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (u["id"],dados["nome"],dados["tipo"],dados.get("va_ggf"),dados.get("responsavel"),
         dados.get("descricao"),dados.get("obs"),dados.get("inicio"),dados.get("termino"),
         dados.get("mes_primeiro_retorno"),dados.get("previsto_unidade",0),
         dados.get("status","📝 Não iniciado"),dados.get("atividade_atual"),
         dados.get("data_conclusao_ativ"),dados.get("onde_parado"),dados.get("data_lib"),
         int(dados.get("check_a3",0)),int(dados.get("check_memoria",0)),
         int(dados.get("check_formalizado",0)),int(dados.get("ganho_unico",0)),
         dados.get("origem","aplicado"),dados.get("numero_projeto"),dados.get("lider_projeto"),
         dados.get("integrantes"),dados.get("revisao"),user_id,user_id))
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
    """Marca como 'campeão' (arquivado, some das listas ativas) só projetos
    que já passaram pelo fluxo completo: validados por Custos (validador_ok
    = 'OK') E cuja curva de retorno já se encerrou. Ganho Único encerra logo
    no mês seguinte ao próprio retorno (curva de 1 mês só); projeto normal
    encerra 12 meses depois. Nunca arquiva um projeto ainda Pendente/NOK —
    senão ele desapareceria da Fila de Aprovação antes mesmo de ser validado."""
    conn = get_conn()
    projetos = conn.execute(
        "SELECT id,mes_primeiro_retorno,ganho_unico FROM projetos "
        "WHERE campeao=0 AND mes_primeiro_retorno IS NOT NULL AND validador_ok='OK'"
    ).fetchall()
    hoje = date.today()
    for p in projetos:
        try:
            mpr = datetime.strptime(str(p["mes_primeiro_retorno"])[:7],"%Y-%m").date()
            if p["ganho_unico"]:
                # Ganho Único: a curva inteira é o próprio mês de retorno, então
                # "forma" logo no mês seguinte — não espera 12 meses como os
                # projetos com rateio normal.
                ano_c = mpr.year + mpr.month // 12
                mes_c = mpr.month % 12 + 1
            else:
                ano_c = mpr.year+(mpr.month+11)//12
                mes_c = (mpr.month+11)%12+1
            if hoje >= date(ano_c,mes_c,1):
                conn.execute("UPDATE projetos SET campeao=1,campeao_em=? WHERE id=?",
                             (hoje.isoformat(),p["id"]))
        except: pass
    conn.commit(); conn.close()

CAMPOS_A3 = [
    ("objetivo_geral", "Objetivo Geral / Considerações Iniciais"),
    ("proposta_desenvolvimento", "Proposta / Desenvolvimento"),
    ("situacao_atual", "Situação Atual"),
    ("metas_entregas", "Metas / Entregas"),
    ("premissas_restricoes", "Premissas / Restrições"),
    ("acompanhamento_indicadores", "Acompanhamento / Indicadores"),
]

def get_a3(projeto_id):
    get_engine(); conn = get_conn()
    row = conn.execute("SELECT * FROM projeto_a3 WHERE projeto_id=?", (projeto_id,)).fetchone()
    conn.close()
    return dict(row) if row else {k: "" for k,_ in CAMPOS_A3}

def salvar_a3(projeto_id, campos):
    conn = get_conn()
    existe = conn.execute("SELECT 1 FROM projeto_a3 WHERE projeto_id=?", (projeto_id,)).fetchone()
    valores = {k: campos.get(k,"") for k,_ in CAMPOS_A3}
    if existe:
        sets = ", ".join(f"{k}=?" for k in valores)
        conn.execute(f"UPDATE projeto_a3 SET {sets}, atualizado_em=datetime('now') WHERE projeto_id=?",
                     list(valores.values())+[projeto_id])
    else:
        cols = ",".join(valores.keys()); qs = ",".join("?" for _ in valores)
        conn.execute(f"INSERT INTO projeto_a3 (projeto_id,{cols}) VALUES (?,{qs})",
                     [projeto_id]+list(valores.values()))
    conn.commit(); conn.close()

def add_a3_midia(projeto_id, campo, nome_arquivo, mime_type, dados_b64):
    conn = get_conn()
    conn.execute("""INSERT INTO projeto_a3_midias (projeto_id,campo,nome_arquivo,mime_type,dados_b64)
        VALUES (?,?,?,?,?)""", (projeto_id, campo, nome_arquivo, mime_type, dados_b64))
    conn.commit(); conn.close()

def get_a3_midias(projeto_id, campo=None):
    get_engine(); conn = get_conn()
    if campo:
        rows = conn.execute("SELECT * FROM projeto_a3_midias WHERE projeto_id=? AND campo=? ORDER BY id",
                             (projeto_id, campo)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM projeto_a3_midias WHERE projeto_id=? ORDER BY id",
                             (projeto_id,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def del_a3_midia(midia_id):
    conn = get_conn()
    conn.execute("DELETE FROM projeto_a3_midias WHERE id=?", (midia_id,))
    conn.commit(); conn.close()

def add_evidencia(projeto_id, nome_arquivo, mime_type, dados_b64):
    conn = get_conn()
    conn.execute("""INSERT INTO projeto_evidencias (projeto_id,nome_arquivo,mime_type,dados_b64)
        VALUES (?,?,?,?)""", (projeto_id, nome_arquivo, mime_type, dados_b64))
    conn.commit(); conn.close()

def get_evidencias(projeto_id):
    get_engine(); conn = get_conn()
    rows = conn.execute("SELECT * FROM projeto_evidencias WHERE projeto_id=? ORDER BY id",
                         (projeto_id,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def del_evidencia(ev_id):
    conn = get_conn()
    conn.execute("DELETE FROM projeto_evidencias WHERE id=?", (ev_id,))
    conn.commit(); conn.close()

def listar_atividades(projeto_id):
    get_engine(); conn = get_conn()
    rows = conn.execute("SELECT * FROM projeto_atividades WHERE projeto_id=? ORDER BY ordem,id",
                         (projeto_id,)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def add_atividade(projeto_id, dados):
    conn = get_conn()
    ordem = dados.get("ordem")
    if ordem is None:
        row = conn.execute("SELECT COALESCE(MAX(ordem),0)+1 AS o FROM projeto_atividades WHERE projeto_id=?",
                            (projeto_id,)).fetchone()
        ordem = row["o"]
    cur = conn.execute("""INSERT INTO projeto_atividades
        (projeto_id,ordem,nome,responsavel,inicio_previsto,termino_previsto,progresso_real,acao)
        VALUES (?,?,?,?,?,?,?,?)""",
        (projeto_id, ordem, dados.get("nome",""), dados.get("responsavel",""),
         dados.get("inicio_previsto"), dados.get("termino_previsto"),
         float(dados.get("progresso_real",0) or 0), dados.get("acao","")))
    conn.commit(); aid = cur.lastrowid; conn.close(); return aid

def atualizar_atividade(atividade_id, dados):
    """Atualiza uma atividade. Se o Término Previsto mudar em relação ao
    que estava salvo, soma +1 no contador discreto de replanejamento do
    projeto — nunca bloqueia a edição, só registra que aconteceu."""
    conn = get_conn()
    atual = conn.execute("SELECT * FROM projeto_atividades WHERE id=?", (atividade_id,)).fetchone()
    if not atual:
        conn.close(); return
    termino_antigo = str(atual["termino_previsto"] or "")
    campos = {k: dados[k] for k in
              ("nome","responsavel","inicio_previsto","termino_previsto","progresso_real","acao","ordem")
              if k in dados}
    if campos:
        sets = ", ".join(f"{k}=?" for k in campos)
        conn.execute(f"UPDATE projeto_atividades SET {sets} WHERE id=?", list(campos.values())+[atividade_id])
    termino_novo = str(dados.get("termino_previsto", termino_antigo) or "")
    if termino_antigo and termino_novo and termino_novo != termino_antigo:
        conn.execute("UPDATE projetos SET replanejamentos=COALESCE(replanejamentos,0)+1 WHERE id=?",
                     (atual["projeto_id"],))
    conn.commit(); conn.close()

def del_atividade(atividade_id):
    conn = get_conn()
    conn.execute("DELETE FROM projeto_atividades WHERE id=?", (atividade_id,))
    conn.commit(); conn.close()

def progresso_plan_atividade(inicio_previsto, termino_previsto):
    """% planejado até hoje (0-100), comparando hoje com o intervalo
    previsto — mesma fórmula de interpolação linear do A3 original."""
    try:
        ini = datetime.strptime(str(inicio_previsto)[:10], "%Y-%m-%d").date()
        fim = datetime.strptime(str(termino_previsto)[:10], "%Y-%m-%d").date()
    except Exception:
        return None
    total = (fim - ini).days + 1
    if total <= 0: return None
    hoje = date.today()
    if hoje < ini: return 0.0
    if hoje > fim: return 100.0
    return round(((hoje - ini).days + 1) / total * 100, 1)

def atividade_atual(projeto_id):
    """Primeira atividade da Estrutura com % Progresso Real < 100, em
    ordem. None se não houver atividades ou todas já estiverem em 100%."""
    for a in listar_atividades(projeto_id):
        if (a.get("progresso_real") or 0) < 100:
            return a
    return None

def atividade_atual_atrasada(atividade):
    """A atividade ATUAL está atrasada quando o próprio término previsto
    dela já passou e ela ainda não chegou a 100% — sinal independente de
    o projeto como um todo estar ou não no prazo."""
    if not atividade: return False
    if (atividade.get("progresso_real") or 0) >= 100: return False
    t = str(atividade.get("termino_previsto") or "")
    if not t: return False
    try:
        return datetime.strptime(t[:10], "%Y-%m-%d").date() < date.today()
    except Exception:
        return False

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

def _curva_de(p, valor):
    """Monta a curva mensal de um valor — rateado em 12 meses a partir do
    mês de primeiro retorno, OU concentrado num mês só se o projeto for
    'Ganho Único' (ganho pontual, sem distribuição)."""
    if not p or not p.get("mes_primeiro_retorno") or not valor or valor <= 0:
        return {}
    try: mpr = datetime.strptime(str(p["mes_primeiro_retorno"])[:7],"%Y-%m")
    except: return {}
    if p.get("ganho_unico"):
        return {(mpr.year, mpr.month): valor}
    mensal = valor/12
    curva = {}
    for i in range(12):
        mes = (mpr.month-1+i)%12+1
        ano = mpr.year+(mpr.month-1+i)//12
        curva[(ano,mes)] = mensal
    return curva

def get_curva_unidade(proj_id):
    """Curva mensal usando previsto_unidade."""
    p = get_projeto(proj_id)
    return _curva_de(p, p.get("previsto_unidade") if p else 0)

def get_curva_custos(proj_id):
    """Curva mensal usando previsto_custos."""
    p = get_projeto(proj_id)
    return _curva_de(p, p.get("previsto_custos") if p else 0)

def get_curva_saving(proj_id):
    """Curva mensal do saving validado — mesma regra do previsto:
    rateia em 12 meses a partir do mês de primeiro retorno (ou concentra
    num mês só se for Ganho Único)."""
    p = get_projeto(proj_id)
    return _curva_de(p, p.get("saving_validado") if p else 0)

def get_previsto_curva(proj_id):
    """Usa custos se disponível, senão unidade."""
    p = get_projeto(proj_id)
    if not p: return {}
    if (p.get("previsto_custos") or 0)>0: return get_curva_custos(proj_id)
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
    projetos = listar_projetos(unidade_nome, incluir_campeao=True)
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
    projetos = listar_projetos(unidade_nome, incluir_campeao=True)
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
            # Extra DRE: soma do ano cheio (previsto da curva), e entra também
            # no Previsto total da unidade — só fica de fora de Validado/Real,
            # que são exclusivos de projetos DRE.
            extra_ano = sum(v for (y,m),v in curva_uni.items() if y==ano)
            total_extra    += extra_ano
            total_prev_uni += extra_ano
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

    projetos = listar_projetos(unidade_nome, incluir_campeao=True)
    previsto = validado = 0.0
    for p in projetos:
        curva = get_curva_unidade(p["id"])
        ano_total = sum(v for (y,m),v in curva.items() if y==ano)
        previsto += ano_total
        if not is_extra_dre(p["tipo"]):
            curva_s = get_curva_saving(p["id"])
            validado += sum(v for (y,m),v in curva_s.items() if y==ano)

    real = 0.0
    for l in get_lancamentos(unidade_nome=unidade_nome, ano=ano):
        if not is_extra_dre(l.get("tipo","")):
            real += l["valor_real"]

    return {"meta":meta, "previsto":previsto, "validado":validado, "real":real,
            "pct_meta": (real/meta*100) if meta>0 else 0}

def saving_por_unidade(ano, tipo_unidade=None, metrica="validado"):
    """Distribuição por unidade de um indicador financeiro, opcionalmente
    filtrado por tipo de unidade ('planta' ou 'area'). Só retorna unidades
    com valor > 0.
    metrica:
      'previsto' -> Previsto por Unidade (rateado no ano)
      'custos'   -> Calculado por Custos (rateado no ano)
      'validado' -> Saving Validado (rateado no ano)
      'real'     -> Real até o Momento (soma direta dos lançamentos no ano)
    """
    unidades = listar_unidades()
    if tipo_unidade:
        unidades = [u for u in unidades if u["tipo"]==tipo_unidade]
    curva_fn = {"previsto": get_curva_unidade,
                "custos": get_curva_custos,
                "validado": get_curva_saving}.get(metrica)
    resultado = []
    for u in unidades:
        total = 0.0
        # Campeão é só uma questão de exibição na lista de cartões — nunca
        # deveria tirar dinheiro (já realizado ou já validado) dos totais.
        for p in listar_projetos(u["nome"], incluir_campeao=True):
            if is_extra_dre(p["tipo"]): continue
            if metrica == "real":
                total += sum(l["valor_real"] for l in get_lancamentos(proj_id=p["id"], ano=ano))
            else:
                curva = curva_fn(p["id"])
                total += sum(v for (y,m),v in curva.items() if y==ano)
        if total > 0:
            resultado.append({"unidade":u["nome"], "valor":total})
    resultado.sort(key=lambda x:-x["valor"])
    return resultado

def distribuicao_por_tipo(ano, unidade_nome=None):
    """Previsto/Validado/Real por tipo de projeto, rateados no ano informado."""
    projetos = listar_projetos(unidade_nome, incluir_campeao=True)
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

def resumo_por_pilar(unidade_nome=None, ano=None):
    """Qtd de projetos, saving previsto/validado e real por tipo de projeto.
    Com 'ano' informado, tudo fica restrito àquele ano (rateado, igual ao
    resto do Dashboard). Sem 'ano', mantém o modo histórico original —
    valores totais (não rateados) somando todos os anos."""
    projetos = listar_projetos(unidade_nome, incluir_campeao=True)
    pilares = {}
    for p in projetos:
        t = p["tipo"]
        if ano is None:
            prev_ano = p["previsto_unidade"] or 0
            val_ano = p["saving_validado"] or 0
        else:
            curva = get_curva_unidade(p["id"])
            prev_ano = sum(v for (y,m),v in curva.items() if y==ano)
            curva_s = get_curva_saving(p["id"])
            val_ano = sum(v for (y,m),v in curva_s.items() if y==ano)
            if prev_ano == 0 and val_ano == 0:
                continue  # projeto sem curva nesse ano — não entra na contagem
        d = pilares.setdefault(t, {"qtd":0,"previsto":0.0,"validado":0.0,
                                    "real_total":0.0,"extra":is_extra_dre(t)})
        d["qtd"] += 1
        d["previsto"] += prev_ano
        d["validado"] += val_ano
    for l in get_lancamentos(unidade_nome=unidade_nome, ano=ano):
        t = l.get("tipo","")
        if t in pilares:
            pilares[t]["real_total"] += l["valor_real"]
    return pilares

def get_carry_over(ano_ref, unidade_nome=None):
    """Meses da curva de projetos DRE que caem FORA do ano de referência —
    parte do previsto que 'sai' do ano vigente (geralmente por causa de um
    'Ganho a partir de' fora de janeiro, que joga meses pro ano seguinte)."""
    projetos = listar_projetos(unidade_nome, incluir_campeao=True)
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
