"""
Dashboard de Controle de Matéria-Prima — Bobinas BSW
- Visitantes veem os dados automaticamente (sem upload)
- Admin atualiza os dados via upload protegido por senha
- Dados persistem no GitHub (não somem quando o app dorme)
"""
import html as html_lib
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import io
import base64
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Grupo Delga | Dashboard Bobinas BSW",
    page_icon="🔵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# ESTILO CSS CUSTOMIZADO (identidade Grupo Delga)
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap' );

    .stApp { background-color: #F4F6FB; font-family: 'Inter', sans-serif; }
    header[data-testid="stHeader"] { background-color: #F4F6FB; }
    section[data-testid="stSidebar"] { background-color: #F8FAFD; border-right: 1px solid #E2E6F0; }
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #FFFFFF 0%, #EEF1F8 100%);
        border: 1px solid #E2E6F0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 10px rgba(15,23,42,0.06);
    }
    div[data-testid="stMetric"] label { color: #64748B !important; font-weight: 500 !important; text-transform: uppercase; font-size: 11px !important; letter-spacing: 0.5px; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #1F2937 !important;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background-color: #F8FAFD; border-radius: 10px; padding: 4px; border: 1px solid #E2E6F0;
    }
    .stTabs [data-baseweb="tab"] { color: #64748B; border-radius: 8px; font-weight: 500; }
    .stTabs [aria-selected="true"] { background-color: #4D6BFF !important; color: #FFFFFF !important; box-shadow: none !important; }
    .stTabs [data-baseweb="tab-highlight"] { background-color: #4D6BFF !important; }
    h1, h2, h3 { color: #1F2937 !important; font-family: 'Inter', sans-serif; font-weight: 700; }
    h4, h5, h6 { color: #64748B !important; font-family: 'Inter', sans-serif; font-weight: 600; }
    p, span, li { color: #475569; }
    .stDataFrame { border: 1px solid #E2E6F0; border-radius: 10px; overflow: hidden; }
    hr { border-color: #E2E6F0; }
    div[data-testid="stFileUploader"] {
        background-color: #FFFFFF; border: 2px dashed #E2E6F0; border-radius: 12px; padding: 16px;
    }
    div[data-testid="stFileUploader"]:hover { border-color: #1400FF; }
    div[data-testid="stSidebar"] .stRadio label { color: #64748B !important; }
    .stSelectbox label { color: #64748B !important; }
    .stButton > button[kind="primary"] { background-color: #1400FF !important; border: none; }
    .stButton > button[kind="primary"]:hover { background-color: #2010FF !important; }

    /* ===== Selectbox / Multiselect (componentes BaseWeb) ===== */
    .stSelectbox label, .stMultiSelect label { color: #475569 !important; font-weight: 600 !important; }
    /* Caixa de seleção fechada */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E6F0 !important;
        border-radius: 8px !important;
        box-shadow: none !important;
    }
    div[data-baseweb="select"] * { color: #1F2937 !important; }
    div[data-baseweb="select"] svg { fill: #94A3B8 !important; }
    /* Tags (pílulas dos itens selecionados) */
    span[data-baseweb="tag"] {
        background-color: #E6ECFD !important;
        color: #1400FF !important;
        border: 1px solid #CBD8FB !important;
        border-radius: 6px !important;
    }
    span[data-baseweb="tag"] span { color: #1400FF !important; }
    span[data-baseweb="tag"] svg { fill: #1400FF !important; }
    /* Dropdown aberto (popover/portal — renderizado fora do main pelo React) */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] * { background-color: #FFFFFF !important; color: #1F2937 !important; }
    div[data-baseweb="popover"] svg { fill: #94A3B8 !important; }
    div[data-baseweb="menu"],
    ul[data-baseweb="menu"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E6F0 !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 20px rgba(15,23,42,0.08) !important;
        overflow: hidden !important;
    }
    ul[data-baseweb="menu"] li,
    li[role="option"],
    div[role="option"] {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    ul[data-baseweb="menu"] li:hover,
    li[role="option"]:hover,
    div[role="option"]:hover,
    li[aria-selected="true"],
    div[aria-selected="true"] {
        background-color: #EEF1FB !important;
        color: #1400FF !important;
    }
    /* Checkmark e ícones dentro das opções */
    li[role="option"] svg, div[role="option"] svg { fill: #4D6BFF !important; }
    /* Input de busca dentro do popover */
    div[data-baseweb="popover"] input {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        border-color: #E2E6F0 !important;
    }

    /* ===== Inputs do BaseWeb (senha, texto) — tema claro ===== */
    div[data-baseweb="input"], div[data-baseweb="base-input"] {
        background-color: #FFFFFF !important;
        border-color: #E2E6F0 !important;
    }
    div[data-baseweb="input"] input {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        -webkit-text-fill-color: #1F2937 !important;
    }
    div[data-baseweb="input"] svg { fill: #94A3B8 !important; }

    /* ===== Expander (Área do Administrador) — tema claro ===== */
    section[data-testid="stSidebar"] details {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E6F0 !important;
        border-radius: 10px !important;
        overflow: hidden;
    }
    section[data-testid="stSidebar"] summary {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    section[data-testid="stSidebar"] summary svg { fill: #475569 !important; }

    /* ===== Uploader de arquivo — tema claro ===== */
    div[data-testid="stFileUploaderDropzone"] {
        background-color: #FFFFFF !important;
        border: 2px dashed #E2E6F0 !important;
    }
    div[data-testid="stFileUploaderDropzone"] * { color: #475569 !important; fill: #94A3B8 !important; }
    div[data-testid="stFileUploaderDropzone"] button {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        border: 1px solid #E2E6F0 !important;
    }
    div[data-testid="stFileUploaderFile"] {
        background-color: #F4F6FB !important;
        border: 1px solid #E2E6F0 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stFileUploaderFile"] * { color: #1F2937 !important; fill: #475569 !important; }

    /* ===== Toggle (botões on/off de filtro) ===== */
    div[data-testid="stToggle"] label p { color: #475569 !important; font-weight: 600 !important; font-size: 13.5px !important; }
    div[role="switch"] { background-color: #CBD5E1 !important; }
    div[role="switch"][aria-checked="true"] { background-color: #1400FF !important; }

    /* ===== Texto branco garantido sobre fundos azul forte ===== */
    .stTabs [aria-selected="true"] * { color: #FFFFFF !important; }
    .stButton > button[kind="primary"] * { color: #FFFFFF !important; }

    /* ===== Aba Acompanhamento (timeline) ===== */
    .acomp-block { margin-bottom: 30px; }
    .acomp-header {
        display:flex; align-items:center; justify-content:space-between;
        padding:14px 18px; background: linear-gradient(135deg, #FFFFFF 0%, #EEF1F8 100%);
        border:1px solid #E2E6F0; border-radius:10px 10px 0 0;
    }
    .acomp-header-title { display:flex; align-items:center; gap:12px; }
    .acomp-dot { width:14px; height:14px; border-radius:4px; flex-shrink:0; }
    .acomp-header-title b { color:#1F2937; font-size:15px; letter-spacing:.3px; }
    .acomp-header-sub { color:#64748B; font-size:12px; }
    .acomp-header-stats { display:flex; gap:24px; }
    .acomp-stat { text-align:right; }
    .acomp-stat-val { color:#1F2937; font-weight:700; font-size:17px; }
    .acomp-stat-lbl { color:#64748B; font-size:10px; text-transform:uppercase; letter-spacing:.5px; }
    .acomp-rows { border:1px solid #E2E6F0; border-top:none; border-radius:0 0 10px 10px; overflow:hidden; }

    .tl-row { display:flex; align-items:center; padding:22px 20px 40px 20px; border-bottom:1px solid #EDF0F6; gap:24px; }
    .tl-row:last-child { border-bottom:none; }
    .tl-row:hover { background:#F8FAFD; }

    .tl-info { width:260px; flex-shrink:0; }
    .tl-code { color:#1F2937; font-weight:700; font-size:14px; }
    .tl-desc { color:#64748B; font-size:12px; margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .tl-meta { color:#64748B; font-size:11px; margin-top:5px; }
    .tl-badge {
        display:inline-block; font-size:10.5px; padding:3px 10px; border-radius:20px;
        margin-top:8px; font-weight:700; letter-spacing:.3px;
    }

    .tl-track { flex:1; position:relative; height:78px; min-width:520px; }
    .tl-line-bg { position:absolute; top:11px; left:11px; right:11px; height:3px; background:#E2E6F0; border-radius:2px; }
    .tl-line-fill { position:absolute; top:11px; left:11px; height:3px; background:linear-gradient(90deg,#1400FF,#4DA3FF); border-radius:2px; }
    .tl-nodes { position:absolute; top:0; left:0; right:0; bottom:0; display:flex; justify-content:space-between; }
    .tl-node { display:flex; flex-direction:column; align-items:center; width:1px; position:relative; }
    .tl-dot { width:22px; height:22px; border-radius:50%; border:3px solid #E2E6F0; background:#F8FAFD; z-index:1; box-sizing:border-box; flex-shrink:0; transform:translateX(-11px); }
    .tl-dot.done { background:#1400FF; border-color:#1400FF; }
    .tl-dot.na { background:#1400FF; border-color:#1400FF; }
    .tl-dot.planned { background:#F8FAFD; border-color:#4DA3FF; }
    .tl-dot.pending { background:#F8FAFD; border-color:#FFB800; }
    .tl-dot.empty { background:#F8FAFD; border-color:#D1D7E3; }
    .tl-label { font-size:10.5px; color:#1F2937; font-weight:600; margin-top:8px; text-align:center; width:104px; transform:translateX(-51.5px); line-height:1.3; }
    .tl-value { font-size:10px; color:#8893A6; margin-top:3px; text-align:center; width:104px; transform:translateX(-51.5px); line-height:1.25; }

    .tl-pct { width:90px; text-align:right; flex-shrink:0; }
    .tl-pct-num { font-size:22px; font-weight:800; color:#1F2937; }
    .tl-pct-label { font-size:10.5px; color:#64748B; }

    /* ===== Tabela clara (substitui st.dataframe em pontos específicos) ===== */
    .light-table-wrap { border:1px solid #E2E6F0; border-radius:10px; overflow:hidden; margin: 6px 0 18px 0; }
    table.light-table { width:100%; border-collapse:collapse; background:#FFFFFF; }
    table.light-table thead th {
        background:#F4F6FB; color:#475569; text-align:left; font-size:12px;
        text-transform:uppercase; letter-spacing:.4px; font-weight:700;
        padding:10px 14px; border-bottom:1px solid #E2E6F0;
    }
    table.light-table tbody td {
        color:#1F2937; font-size:13.5px; padding:10px 14px; border-bottom:1px solid #EEF1F7;
    }
    table.light-table tbody tr:last-child td { border-bottom:none; }
    table.light-table tbody tr:hover td { background:#F8FAFD; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# CORES POR UNIDADE DELGA (padronizadas)
# ============================================================
UNIDADE_COLORS = {
    "Ferraz":  "#1E88E5",
    "Diadema": "#43A047",
    "Jarinu":  "#FB8C00",
    "Sul":     "#8E24AA",
}

COLORS = {
    "cyan": "#4DA3FF", "amber": "#FFB800", "emerald": "#00E676",
    "coral": "#FF6B6B", "purple": "#A78BFA", "teal": "#4DD0E1",
    "blue_delga": "#1400FF", "blue_light": "#4DA3FF",
    "bg_card": "#FFFFFF", "bg_dark": "#F8FAFD",
    "border": "#E2E6F0", "text_light": "#64748B", "text_white": "#1F2937",
}

CHART_COLORS = [
    "#4DA3FF", "#FFB800", "#00E676", "#A78BFA", "#FF6B6B",
    "#4DD0E1", "#FFD54F", "#69F0AE", "#B39DDB", "#FF8A80",
    "#80DEEA", "#FFF176", "#A5D6A7", "#CE93D8", "#EF9A9A",
]

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(color="#475569", family="Inter, Arial"),
    margin=dict(l=40, r=40, t=50, b=40),
    legend=dict(
        bgcolor="rgba(255,255,255,0.95)", bordercolor="#E2E6F0",
        borderwidth=1, font=dict(color="#64748B"),
    ),
)

# ============================================================
# CONFIGURAÇÃO DO GITHUB (para persistência de dados)
# ============================================================
GITHUB_REPO = "GabrielGustavoDeSouza/dashboard-bobinas"
GITHUB_DATA_PATH = "data/dados_atuais.xlsx"
GITHUB_BRANCH = "main"

ADMIN_PASSWORD = "M@ster"

# ============================================================
# CONFIGURAÇÃO DA ABA "A.Propostas" (Acompanhamento)
# ============================================================
# Coluna "FORMALIZADO COM COMPRAS" + "PASSADO PARA USINA ?" + as 7 etapas seguintes
STAGE_DEFS = [
    ("FORMALIZADO COM COMPRAS", "Formalização com Compras"),
    ("DATA ENVIO P/ USINA", "Envio à Usina"),
    ("PRAZO DA USINA PARA RETORNO", "Retorno da Usina"),
    ("DATA DE DEVOLUÇÃO DA CONSULTA", "Devolução da Consulta"),
    ("ENVIO DE PLANO DE CORTE PARA COMPRAS", "Plano de Corte → Compras"),
    ("ENVIO DO PLANO DE CORTE PARA USINAS", "Plano de Corte → Usina"),
    ("PRAZO PARA CADASTRO DO NOVO PN (LIBERAR PROGRAMAÇÃO)", "Cadastro Novo PN"),
    ("PRAZO DE RECEBIMENTO NAS NOVAS ESPECIFICAÇÕES (APROXIMADO)", "Recebimento Material"),
]

STAGE_STATUS_COLOR = {
    "done": "#1400FF",
    "na": "#1400FF",
    "planned": "#4DA3FF",
    "pending": "#FFB800",
    "empty": "#D1D7E3",
}


def get_github_token():
    try:
        return st.secrets["GITHUB_TOKEN"]
    except (KeyError, FileNotFoundError):
        return None


def get_unidade_color(nome):
    for key, color in UNIDADE_COLORS.items():
        if key.lower() in str(nome).lower():
            return color
    return COLORS["cyan"]


def get_unidade_colors_list(names):
    return [get_unidade_color(n) for n in names]


# ============================================================
# FUNÇÕES DE PERSISTÊNCIA (GitHub API)
# ============================================================
@st.cache_data(ttl=120)
def load_data_from_github():
    token = get_github_token()
    if not token:
        return None, None, None

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_DATA_PATH}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {"ref": GITHUB_BRANCH}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        content = response.json()
        file_content = base64.b64decode(content["content"])
        excel_bytes = io.BytesIO(file_content)
        df_controle = smart_read_excel(excel_bytes, "Controle")
        excel_bytes.seek(0)
        df_formulas = pd.read_excel(excel_bytes, sheet_name="Formulas")
        excel_bytes.seek(0)
        df_propostas = smart_read_propostas(excel_bytes)
        return df_controle, df_formulas, df_propostas
    return None, None, None


def save_data_to_github(file_bytes, filename):
    token = get_github_token()
    if not token:
        return False, "Token do GitHub não configurado nos Secrets."

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_DATA_PATH}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers, params={"ref": GITHUB_BRANCH})
    sha = None
    if response.status_code == 200:
        sha = response.json()["sha"]

    content_b64 = base64.b64encode(file_bytes).decode("utf-8")

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    payload = {
        "message": f"Atualização de dados: {filename} ({now})",
        "content": content_b64,
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    response = requests.put(url, headers=headers, json=payload)
    if response.status_code in [200, 201]:
        load_data_from_github.clear()
        return True, "Dados atualizados com sucesso!"
    else:
        return False, f"Erro ao salvar: {response.status_code} - {response.json().get('message', '')}"


# ============================================================
# FUNÇÕES DE CONEXÃO COM SHAREPOINT
# ============================================================
@st.cache_data(ttl=300)
def get_access_token():
    tenant_id = st.secrets["TENANT_ID"]
    client_id = st.secrets["CLIENT_ID"]
    client_secret = st.secrets["CLIENT_SECRET"]
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()["access_token"]


@st.cache_data(ttl=300)
def load_data_from_sharepoint():
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    site_domain = st.secrets["SHAREPOINT_DOMAIN"]
    site_path = st.secrets["SHAREPOINT_SITE_PATH"]
    file_path = st.secrets["SHAREPOINT_FILE_PATH"]
    site_url = f"https://graph.microsoft.com/v1.0/sites/{site_domain}:/sites/{site_path}"
    site_resp = requests.get(site_url, headers=headers)
    site_resp.raise_for_status()
    site_id = site_resp.json()["id"]
    file_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root:/{file_path}:/content"
    file_resp = requests.get(file_url, headers=headers)
    file_resp.raise_for_status()
    excel_bytes = io.BytesIO(file_resp.content)
    df_controle = smart_read_excel(excel_bytes, "Controle")
    excel_bytes.seek(0)
    df_formulas = pd.read_excel(excel_bytes, sheet_name="Formulas")
    excel_bytes.seek(0)
    df_propostas = smart_read_propostas(excel_bytes)
    return df_controle, df_formulas, df_propostas


def find_header_row(excel_bytes, sheet_name, markers, max_scan=15):
    """Procura, dentro das primeiras linhas de uma aba, a linha que contém os
    cabeçalhos reais (algumas abas têm títulos/linhas em branco antes)."""
    excel_bytes.seek(0)
    df_raw = pd.read_excel(excel_bytes, sheet_name=sheet_name, header=None, nrows=max_scan)
    for row_idx in range(len(df_raw)):
        row_vals = [str(v).replace('\n', ' ').strip().upper() for v in df_raw.iloc[row_idx] if pd.notna(v)]
        for marker in markers:
            if any(marker.upper() in v for v in row_vals):
                return row_idx
    return 0


def smart_read_excel(excel_bytes, sheet_name):
    df = pd.read_excel(excel_bytes, sheet_name=sheet_name, header=0)
    unnamed_count = sum(1 for c in df.columns if str(c).startswith('Unnamed'))
    if unnamed_count > len(df.columns) * 0.5:
        excel_bytes.seek(0)
        df_raw = pd.read_excel(excel_bytes, sheet_name=sheet_name, header=None)
        for row_idx in range(min(5, len(df_raw))):
            row_vals = [str(v).replace('\n', ' ').strip() for v in df_raw.iloc[row_idx] if pd.notna(v)]
            if any('Código' in v or 'Bobina' in v or 'NECESSIDADE' in v or 'Tipo' in v for v in row_vals):
                excel_bytes.seek(0)
                df = pd.read_excel(excel_bytes, sheet_name=sheet_name, header=row_idx)
                break
    return df


def smart_read_propostas(excel_bytes):
    """Lê a aba 'A.Propostas' (controle de acompanhamento de propostas BSW).
    Retorna None se a aba não existir no arquivo (compatibilidade com arquivos antigos)."""
    try:
        excel_bytes.seek(0)
        xls = pd.ExcelFile(excel_bytes)
        sheet_name = None
        for s in xls.sheet_names:
            if s.strip().upper().replace(' ', '') in ('A.PROPOSTAS', 'APROPOSTAS'):
                sheet_name = s
                break
        if sheet_name is None:
            return None
        header_row = find_header_row(excel_bytes, sheet_name, ['CÓDIGO DELGA', 'CODIGO DELGA'])
        excel_bytes.seek(0)
        df = pd.read_excel(
            excel_bytes, sheet_name=sheet_name, header=header_row,
            keep_default_na=False, na_values=['']
        )
        return df
    except Exception:
        return None


def load_data_from_upload(uploaded_file):
    excel_bytes = io.BytesIO(uploaded_file.getvalue())
    df_controle = smart_read_excel(excel_bytes, "Controle")
    excel_bytes.seek(0)
    df_formulas = pd.read_excel(excel_bytes, sheet_name="Formulas")
    excel_bytes.seek(0)
    df_propostas = smart_read_propostas(excel_bytes)
    return df_controle, df_formulas, df_propostas


def process_data(df_raw):
    df = df_raw.copy()
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

    col_codigo = [c for c in df.columns if 'Código' in c and 'Bobina' in c]
    if col_codigo:
        df = df[df[col_codigo[0]].notna() & (df[col_codigo[0]] != '')]

    nec_cols = {
        'jan': [c for c in df.columns if 'Janeiro' in c and 'MÉDIA' not in c.upper()],
        'fev': [c for c in df.columns if 'Fevereiro' in c and 'MÉDIA' not in c.upper()],
        'mar': [c for c in df.columns if ('Março' in c or 'Marco' in c) and 'MÉDIA' not in c.upper()],
        'abr': [c for c in df.columns if 'Abril' in c and 'MÉDIA' not in c.upper()],
        'mai': [c for c in df.columns if 'Maio' in c and 'MÉDIA' not in c.upper()],
        'media': [c for c in df.columns if 'MÉDIA' in c.upper() and 'FEV' in c.upper()],
    }

    col_names = {}
    for key, cols in nec_cols.items():
        if cols:
            col_names[key] = cols[0]

    for key, col in col_names.items():
        df[col] = df[col].apply(parse_numero_brasileiro)

    return df, col_names


def parse_formulas(df_formulas):
    unidades = []
    usinas = []

    for i in range(min(10, len(df_formulas))):
        row = df_formulas.iloc[i]
        nome = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        if nome.lower() == 'total':
            break
        if not nome or nome.lower() in ['nan', 'usinas', '']:
            continue
        try:
            bobinas = int(float(row.iloc[1])) if pd.notna(row.iloc[1]) else 0
        except (ValueError, TypeError):
            continue
        try:
            peso_total = float(row.iloc[2]) if pd.notna(row.iloc[2]) else 0
        except (ValueError, TypeError):
            peso_total = 0
        try:
            peso_analisado = float(row.iloc[3]) if pd.notna(row.iloc[3]) else 0
        except (ValueError, TypeError):
            peso_analisado = 0
        try:
            pct_raw = row.iloc[4]
            if pd.notna(pct_raw):
                pct = float(pct_raw)
                pct = pct * 100 if pct <= 1 else pct
            else:
                pct = 0
        except (ValueError, TypeError):
            pct = 0
        unidades.append({
            'unidade': nome, 'bobinas': bobinas, 'peso_total': peso_total,
            'peso_analisado': peso_analisado, 'pct': pct,
        })

    usina_start = None
    for i in range(len(df_formulas)):
        val = str(df_formulas.iloc[i, 0]).strip().lower() if pd.notna(df_formulas.iloc[i, 0]) else ''
        if val == 'usinas':
            usina_start = i + 1
            break
    if usina_start:
        for i in range(usina_start, len(df_formulas)):
            row = df_formulas.iloc[i]
            nome = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
            if nome.lower() in ['total', '']:
                if nome.lower() == 'total':
                    break
                continue
            if nome.lower() == 'nan' or nome == '0':
                continue
            try:
                bobinas = int(float(row.iloc[1])) if pd.notna(row.iloc[1]) else 0
            except (ValueError, TypeError):
                continue
            try:
                peso = float(row.iloc[2]) if pd.notna(row.iloc[2]) else 0
            except (ValueError, TypeError):
                peso = 0
            try:
                pct_repr = float(row.iloc[3]) if pd.notna(row.iloc[3]) else 0
            except (ValueError, TypeError):
                pct_repr = 0
            usinas.append({
                'usina': nome, 'bobinas': bobinas, 'peso': peso,
                'pct_representacao': pct_repr * 100 if pct_repr <= 1 else pct_repr,
            })

    df_unidades = pd.DataFrame(unidades) if unidades else pd.DataFrame()
    df_usinas = pd.DataFrame(usinas) if usinas else pd.DataFrame()
    return df_unidades, df_usinas


# ============================================================
# FUNÇÕES DA ABA "A.Propostas" (Acompanhamento)
# ============================================================
def classify_stage_value(v):
    """Classifica o valor de uma célula de etapa em:
    done (data já passou), planned (data futura), na (não se aplica),
    pending (texto tipo 'PENDENTE'/outro), empty (vazio)."""
    if pd.isna(v):
        return 'empty', ''
    if isinstance(v, str) and v.strip() == '':
        return 'empty', ''
    if isinstance(v, (pd.Timestamp, datetime)):
        d = pd.Timestamp(v)
        texto = d.strftime('%d/%m/%Y')
        if d.date() <= datetime.now().date():
            return 'done', texto
        return 'planned', texto
    txt = str(v).strip()
    up = txt.upper()
    if up in ('N/A', 'NA', 'NÃO SE APLICA', 'NAO SE APLICA', '-'):
        return 'na', 'N/A'
    if 'PENDENTE' in up:
        return 'pending', 'Pendente'
    return 'pending', txt[:40]


def normalizar_texto_simples(valor, default='Desconhecida'):
    if pd.isna(valor):
        return default
    txt = str(valor).replace('\n', ' / ').strip()
    txt = ' '.join(txt.split())
    return txt.upper() if txt else default


def classify_formalizacao(valor_formalizacao, passado_usina, data_envio_usina):
    """Classifica a etapa 'Formalização com Compras'.
    Regra: se a célula tiver uma data, usa essa data normalmente.
    Se não tiver data própria, mas a etapa 'Envio à Usina' já tem uma data
    (já foi enviado) OU está marcada como 'N/A' (não se aplica), consideramos
    a formalização automaticamente OK — afinal só se envia à usina depois de
    formalizar com compras, e se a etapa de envio nem se aplica, a
    formalização também não se aplica. Nesses casos mostramos o que estiver
    escrito na própria célula de formalização (mesmo que esteja vazia ou diga
    algo como 'Data não informada.').
    Caso a etapa de envio também não esteja resolvida, devolvemos o status
    real da própria célula (ex.: pendente, com o texto escrito), para sabermos
    há quanto tempo a proposta está parada na mão de Compras."""
    status_f, texto_f = classify_stage_value(valor_formalizacao)
    if status_f == 'done':
        return status_f, texto_f

    status_e, _texto_e = classify_stage_value(data_envio_usina)
    if status_e in ('done', 'na'):
        return 'done', texto_f

    return status_f, texto_f


def process_propostas(df_raw):
    """Processa a aba 'A.Propostas': normaliza colunas e calcula, para cada
    proposta, o status de cada uma das 8 etapas e o percentual de conclusão."""
    if df_raw is None:
        return None

    df = df_raw.copy()
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]

    col_codigo = next((c for c in df.columns if c.strip().upper() == 'CÓDIGO DELGA'), None)
    if col_codigo is None:
        return None
    df = df[df[col_codigo].notna() & (df[col_codigo].astype(str).str.strip() != '')].copy()
    if len(df) == 0:
        return None

    # Evita contagens duplicadas quando o mesmo Código Delga aparece mais de
    # uma vez na planilha (mantém a primeira ocorrência).
    df = df.drop_duplicates(subset=[col_codigo], keep='first')

    df = df.rename(columns={col_codigo: 'CÓDIGO DELGA'})

    col_desc = next((c for c in df.columns if 'DESCRIÇÃO' in c.upper()), None)
    col_planta = next((c for c in df.columns if 'PLANTA DELGA' in c.upper()), None)
    col_fonte = next((c for c in df.columns if c.strip().upper() == 'FONTE'), None)
    col_passado = next((c for c in df.columns if 'PASSADO PARA USINA' in c.upper()), None)
    col_reducao = next((c for c in df.columns if 'REDUÇÃO POTENCIAL' in c.upper()), None)
    col_consumo = next((c for c in df.columns if 'MÉDIA CONSUMO' in c.upper()), None)
    col_envio_usina = next((c for c in df.columns if c.strip().upper() == 'DATA ENVIO P/ USINA'), None)

    df['_DESCRICAO'] = df[col_desc].astype(str).str.strip() if col_desc else ''
    df['_PLANTA'] = df[col_planta].apply(lambda x: normalizar_texto_simples(x)) if col_planta else 'Desconhecida'
    df['_FONTE'] = df[col_fonte].apply(lambda x: normalizar_texto_simples(x)) if col_fonte else 'Desconhecida'
    df['_PASSADO'] = df[col_passado].apply(lambda x: normalizar_texto_simples(x, default='')) if col_passado else ''
    df['_REDUCAO'] = df[col_reducao].apply(parse_numero_brasileiro) if col_reducao else 0.0
    df['_CONSUMO'] = df[col_consumo].apply(parse_numero_brasileiro) if col_consumo else 0.0

    stage_status_list = []
    pct_list = []
    badge_list = []
    completed_list = []

    available_stages = [(c, label) for c, label in STAGE_DEFS if c in df.columns]

    for _, row in df.iterrows():
        stages = []
        completed = 0
        for col, label in available_stages:
            if col == 'FORMALIZADO COM COMPRAS':
                status, texto = classify_formalizacao(
                    row.get(col), row['_PASSADO'],
                    row.get(col_envio_usina) if col_envio_usina else None,
                )
            else:
                status, texto = classify_stage_value(row.get(col))
            if status in ('done', 'na'):
                completed += 1
            stages.append({'col': col, 'label': label, 'status': status, 'texto': texto})

        n_stages = len(available_stages) if available_stages else 1
        passado = row['_PASSADO']

        if 'NÃO' in passado or passado == 'NAO':
            pct = 0
            badge = ('Não enviado à usina', COLORS['coral'])
        elif 'KAIZEN' in passado:
            pct = round(completed / n_stages * 100)
            badge = ('Kaizen Plano de Corte', COLORS['purple'])
        elif completed == n_stages and n_stages > 0:
            pct = 100
            badge = ('Concluído', COLORS['emerald'])
        elif completed == 0:
            pct = 0
            badge = ('Aguardando início', COLORS['text_light'])
        else:
            pct = round(completed / n_stages * 100)
            badge = ('Em andamento', COLORS['cyan'])

        stage_status_list.append(stages)
        pct_list.append(pct)
        badge_list.append(badge)
        completed_list.append(completed)

    df['_STAGES'] = stage_status_list
    df['_PCT'] = pct_list
    df['_BADGE'] = badge_list
    df['_COMPLETED'] = completed_list
    df['_N_STAGES'] = len(available_stages) if available_stages else 0

    return df


def render_timeline_row_html(row):
    n_stages = max(row['_N_STAGES'], 1)
    pct = row['_PCT']
    codigo = html_lib.escape(str(row['CÓDIGO DELGA']))
    desc = html_lib.escape(str(row['_DESCRICAO'])[:60])
    badge_label, badge_color = row['_BADGE']

    nodes_html = []
    for st_info in row['_STAGES']:
        status = st_info['status']
        label = html_lib.escape(st_info['label'])
        texto_raw = st_info['texto'] if st_info['texto'] else '—'
        texto = html_lib.escape(texto_raw)
        tooltip = f"{label}: {texto_raw}"
        nodes_html.append(
            f'<div class="tl-node" title="{tooltip}">'
            f'<div class="tl-dot {status}"></div>'
            f'<div class="tl-label">{label}</div>'
            f'<div class="tl-value">{texto}</div>'
            f'</div>'
        )

    fonte_txt = html_lib.escape(str(row['_FONTE']))

    # IMPORTANTE: sem indentação/quebras de linha "soltas" no HTML — texto
    # indentado com 4+ espaços é interpretado pelo Markdown do Streamlit
    # como bloco de código, quebrando a renderização.
    row_html = (
        '<div class="tl-row">'
        '<div class="tl-info">'
        f'<div class="tl-code">{codigo}</div>'
        f'<div class="tl-desc">{desc}</div>'
        f'<div class="tl-meta">{fonte_txt}</div>'
        f'<span class="tl-badge" style="background:{badge_color}22; color:{badge_color}; border:1px solid {badge_color}55;">{badge_label}</span>'
        '</div>'
        '<div class="tl-track">'
        '<div class="tl-line-bg"></div>'
        f'<div class="tl-line-fill" style="width:{pct}%;"></div>'
        f'<div class="tl-nodes">{"".join(nodes_html)}</div>'
        '</div>'
        '<div class="tl-pct">'
        f'<div class="tl-pct-num">{pct}%</div>'
        '<div class="tl-pct-label">concluído</div>'
        '</div>'
        '</div>'
    )
    return row_html


def render_acompanhamento_block(planta, df_grupo):
    color = get_unidade_color(planta)
    avg_pct = df_grupo['_PCT'].mean() if len(df_grupo) else 0
    n_itens = len(df_grupo)
    n_concluidos = int((df_grupo['_PCT'] == 100).sum())

    rows_html = ''.join(render_timeline_row_html(r) for _, r in df_grupo.iterrows())

    # Sem indentação/quebras de linha soltas (ver nota em render_timeline_row_html).
    block_html = (
        '<div class="acomp-block">'
        '<div class="acomp-header">'
        '<div class="acomp-header-title">'
        f'<div class="acomp-dot" style="background:{color};"></div>'
        '<div>'
        f'<b>{html_lib.escape(str(planta))}</b><br/>'
        f'<span class="acomp-header-sub">{n_itens} propostas</span>'
        '</div>'
        '</div>'
        '<div class="acomp-header-stats">'
        '<div class="acomp-stat">'
        f'<div class="acomp-stat-val">{avg_pct:.0f}%</div>'
        '<div class="acomp-stat-lbl">Progresso Médio</div>'
        '</div>'
        '<div class="acomp-stat">'
        f'<div class="acomp-stat-val">{n_concluidos}</div>'
        '<div class="acomp-stat-lbl">Concluídas</div>'
        '</div>'
        '</div>'
        '</div>'
        f'<div class="acomp-rows">{rows_html}</div>'
        '</div>'
    )
    return block_html


# ============================================================
# FUNÇÕES DE GRÁFICOS
# ============================================================
def create_area_chart(df, col_names):
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai']
    keys = ['jan', 'fev', 'mar', 'abr', 'mai']
    valores = []
    for k in keys:
        if k in col_names:
            valores.append(round(df[col_names[k]].sum(), 1))
        else:
            valores.append(0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=meses, y=valores,
        fill='tozeroy', fillcolor='rgba(20,0,255,0.12)',
        line=dict(color=COLORS["cyan"], width=3),
        mode='lines+markers',
        marker=dict(size=10, color=COLORS["cyan"]),
        name='Necessidade (ton)',
        hovertemplate='%{x}/2026 <b>%{y:,.0f} ton</b><extra></extra>',
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Evolução da Necessidade Mensal (ton)", font=dict(size=16, color=COLORS["cyan"])),
        yaxis=dict(title="Toneladas", gridcolor="#E5E9F2", zerolinecolor="#E5E9F2"),
        xaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2"),
        height=400,
    )
    return fig


def create_unidade_pie_chart(df, col_media):
    unidade_col = [c for c in df.columns if 'Unidade' in c and 'Delga' in c]
    if not unidade_col:
        return None
    df_valid = df[df[unidade_col[0]].notna() & (df[unidade_col[0]].astype(str).str.strip() != '')].copy()
    if len(df_valid) == 0:
        return None
    dist = df_valid.groupby(unidade_col[0])[col_media].sum().sort_values(ascending=False)
    colors = get_unidade_colors_list(dist.index)
    fig = go.Figure(data=[go.Pie(
        labels=[str(x) for x in dist.index],
        values=dist.values.tolist(),
        hole=0.45,
        marker=dict(colors=colors),
        textinfo='percent+label',
        textfont=dict(size=12, color="#1F2937"),
        hovertemplate='%{label}  <b>%{value:,.1f} ton</b>  %{percent}<extra></extra>',
    )])
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Distribuição por Unidade Delga", font=dict(size=16, color=COLORS["cyan"])),
        height=400,
    )
    return fig


def create_tipo_pie_chart(df, col_media):
    tipo_col = [c for c in df.columns if c.strip() == 'Tipo']
    if not tipo_col:
        return None
    df_valid = df[df[tipo_col[0]].notna() & (df[tipo_col[0]].astype(str).str.strip() != '')].copy()
    if len(df_valid) == 0:
        return None

    def agrupar_tipo(tipo):
        t = str(tipo).strip().upper()
        if t.endswith('Z'): return 'BZ'
        if t.endswith('Q'): return 'BQ'
        if t.endswith('F'): return 'BF'
        return 'Outros'

    df_valid['Tipo_Agrupado'] = df_valid[tipo_col[0]].apply(agrupar_tipo)
    df_valid = df_valid[df_valid['Tipo_Agrupado'] != 'Outros']
    dist = df_valid.groupby('Tipo_Agrupado')[col_media].sum().sort_values(ascending=False)
    cores_fatias = ["#4DA3FF", "#FFB800", "#00E676"]

    fig = go.Figure(data=[go.Pie(
        labels=[str(x) for x in dist.index],
        values=dist.values.tolist(),
        hole=0.45,
        marker=dict(colors=cores_fatias),
        textinfo='percent+label',
        textfont=dict(size=12, color="#1F2937"),
        hovertemplate='%{label}<b>%{value:,.1f} ton</b> %{percent}<extra></extra>',
    )])
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Distribuição por Tipo de Bobina", font=dict(size=16, color=COLORS["cyan"])),
        height=400,
    )
    return fig


def create_thickness_chart(df, col_media):
    esp_col = [c for c in df.columns if 'Esp' in c and 'mm' in c]
    if not esp_col:
        return None
    df_temp = df.copy()
    df_temp['esp_num'] = pd.to_numeric(df_temp[esp_col[0]], errors='coerce')
    df_temp = df_temp[df_temp['esp_num'].notna()]
    if len(df_temp) == 0:
        return None
    bins = [0, 1, 2, 4, 6, 8, 10, 15, 20, 50]
    labels = ['0-1', '1-2', '2-4', '4-6', '6-8', '8-10', '10-15', '15-20', '20+']
    df_temp['faixa'] = pd.cut(df_temp['esp_num'], bins=bins, labels=labels, right=True)
    dist = df_temp.groupby('faixa', observed=True)[col_media].sum().sort_index()
    dist = dist[dist > 0]
    if len(dist) == 0:
        return None
    fig = go.Figure(data=[go.Bar(
        x=[str(x) for x in dist.index],
        y=dist.values.tolist(),
        marker=dict(color=CHART_COLORS[:len(dist)]),
        hovertemplate='%{x} mm  <b>%{y:,.1f} ton</b><extra></extra>',
    )])
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Distribuição por Faixa de Espessura (mm)", font=dict(size=16, color=COLORS["cyan"])),
        yaxis=dict(title="Toneladas", gridcolor="#E5E9F2", zerolinecolor="#E5E9F2"),
        xaxis=dict(title="Espessura (mm)", gridcolor="#E5E9F2", zerolinecolor="#E5E9F2"),
        height=400,
    )
    return fig


def create_progress_chart(df_unidades):
    if len(df_unidades) == 0:
        return None
    unidades = df_unidades['unidade'].tolist()
    peso_total = df_unidades['peso_total'].tolist()
    peso_analisado = df_unidades['peso_analisado'].tolist()
    colors = get_unidade_colors_list(unidades)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Peso Total',
        x=unidades, y=peso_total,
        marker=dict(color=colors, opacity=0.4),
        hovertemplate='%{x}  Peso Total: <b>%{y:,.1f} ton</b><extra></extra>',
    ))
    fig.add_trace(go.Bar(
        name='Peso Analisado',
        x=unidades, y=peso_analisado,
        marker=dict(color=colors, opacity=1.0),
        hovertemplate='%{x}  Analisado: <b>%{y:,.1f} ton</b><extra></extra>',
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Peso Total vs Analisado por Unidade", font=dict(size=16, color=COLORS["cyan"])),
        barmode='group',
        yaxis=dict(title="Toneladas", gridcolor="#E5E9F2", zerolinecolor="#E5E9F2"),
        xaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2"),
        height=400,
    )
    return fig


def create_usinas_chart(df_usinas, top_n=15):
    if len(df_usinas) == 0:
        return None
    df_sorted = df_usinas.nlargest(top_n, 'peso')
    df_sorted = df_sorted.sort_values('peso', ascending=True)
    fig = go.Figure(data=[go.Bar(
        x=df_sorted['peso'].tolist(),
        y=df_sorted['usina'].tolist(),
        orientation='h',
        marker=dict(color=COLORS["teal"]),
        hovertemplate='%{y}  <b>%{x:,.1f} ton</b><extra></extra>',
    )])
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Top Usinas por Peso (ton)", font=dict(size=16, color=COLORS["cyan"])),
        height=max(400, min(top_n, len(df_sorted)) * 32),
        yaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2"),
        xaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2", title="Toneladas"),
    )
    return fig


def create_bar_chart(df, col_media, title, group_col, top_n=15, color=None):
    df_valid = df[df[group_col].notna() & (df[group_col].astype(str).str.strip() != '')].copy()
    if len(df_valid) == 0:
        return None
    dist = df_valid.groupby(group_col)[col_media].sum().sort_values(ascending=True).tail(top_n)
    fig = go.Figure(data=[go.Bar(
        x=dist.values.tolist(),
        y=[str(x) for x in dist.index],
        orientation='h',
        marker=dict(color=color or COLORS["cyan"]),
        hovertemplate='%{y}  <b>%{x:,.1f} ton</b><extra></extra>',
    )])
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title, font=dict(size=16, color=COLORS["cyan"])),
        height=max(400, min(top_n, len(dist)) * 32),
        yaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2"),
        xaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2", title="Toneladas"),
    )
    return fig


def create_unidade_bar_chart(df, col_media):
    unidade_col = [c for c in df.columns if 'Unidade' in c and 'Delga' in c]
    if not unidade_col:
        return None
    df_valid = df[df[unidade_col[0]].notna() & (df[unidade_col[0]].astype(str).str.strip() != '')].copy()
    if len(df_valid) == 0:
        return None
    dist = df_valid.groupby(unidade_col[0])[col_media].sum().sort_values(ascending=True)
    colors = get_unidade_colors_list(dist.index)
    fig = go.Figure(data=[go.Bar(
        x=dist.values.tolist(),
        y=[str(x) for x in dist.index],
        orientation='h',
        marker=dict(color=colors),
        hovertemplate='%{y}  <b>%{x:,.1f} ton</b><extra></extra>',
    )])
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text="Necessidade por Unidade Delga (ton)", font=dict(size=16, color=COLORS["cyan"])),
        height=350,
        yaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2"),
        xaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2", title="Toneladas"),
    )
    return fig


def create_propostas_progress_chart(df_propostas):
    if df_propostas is None or len(df_propostas) == 0:
        return None
    dist = df_propostas.groupby('_PLANTA')['_PCT'].mean().sort_values(ascending=True)
    colors = get_unidade_colors_list(dist.index)
    fig = go.Figure(data=[go.Bar(
        x=dist.values.tolist(),
        y=[str(x) for x in dist.index],
        orientation='h',
        marker=dict(color=colors),
        text=[f"{v:.0f}%" for v in dist.values],
        textposition='outside',
        textfont=dict(color="#1F2937", size=12),
        cliponaxis=False,
        hovertemplate='%{y}  <b>%{x:.0f}% concluído</b><extra></extra>',
    )])
    layout = dict(PLOTLY_LAYOUT)
    layout['margin'] = dict(l=140, r=60, t=50, b=40)
    fig.update_layout(
        **layout,
        title=dict(text="Progresso Médio das Propostas por Planta Delga", font=dict(size=16, color=COLORS["cyan"])),
        height=max(320, len(dist) * 60),
        yaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2", automargin=True, tickfont=dict(size=13)),
        xaxis=dict(gridcolor="#E5E9F2", zerolinecolor="#E5E9F2", title="% Concluído", range=[0, 108]),
    )
    return fig


def parse_numero_brasileiro(valor):
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    txt = str(valor).strip()
    if not txt or txt.lower() in ["nan", "none", "-", ""]:
        return 0.0
    txt = (txt.replace("R$", "")
              .replace(" ", "")
              .replace("\xa0", ""))
    if "," in txt and "." in txt:
        if txt.rfind(",") > txt.rfind("."):
            txt = txt.replace(".", "").replace(",", ".")
        else:
            txt = txt.replace(",", "")
    elif "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except Exception:
        return 0.0


def normalizar_unidade(valor):
    if pd.isna(valor):
        return "Desconhecida"
    txt = str(valor).replace("\n", " ").strip()
    txt = " ".join(txt.split())
    if not txt or txt.lower() in ["nan", "none"]:
        return "Desconhecida"
    return txt


def render_chart(fig):
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, theme=None)
        return True
    return False


def build_light_table_html(df_table):
    """Gera uma tabela HTML com o tema claro do dashboard. Usada no lugar de
    st.dataframe, que renderiza em canvas e não respeita a folha de estilo
    customizada (ficava com fundo azul-escuro mesmo no tema claro)."""
    headers_html = ''.join(f'<th>{html_lib.escape(str(c))}</th>' for c in df_table.columns)
    rows_html = []
    for _, r in df_table.iterrows():
        cells = ''.join(f'<td>{html_lib.escape(str(v))}</td>' for v in r)
        rows_html.append(f'<tr>{cells}</tr>')
    table_html = (
        '<div class="light-table-wrap">'
        '<table class="light-table">'
        f'<thead><tr>{headers_html}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>'
        '</div>'
    )
    return table_html


# ============================================================
# APLICAÇÃO PRINCIPAL
# ============================================================
def main():
    # SIDEBAR
    with st.sidebar:
        st.image("logo_delga.png", use_container_width=True)
        st.markdown("""
        <div style="text-align:center; padding:8px 0 16px 0;">
            <p style="color:#64748B; font-size:11px; margin:0; text-transform:uppercase; letter-spacing:1.5px; font-weight:600;">Controle de Matéria-Prima</p>
        </div>
        <hr style="border-color:#E2E6F0; margin:0 0 16px 0;">
        """, unsafe_allow_html=True)

        st.markdown("#### 🔐 Área do Administrador")
        with st.expander("Atualizar Dados (requer senha)", expanded=False):
            senha = st.text_input("Senha:", type="password", key="admin_pwd")
            if senha == ADMIN_PASSWORD:
                st.success("Acesso liberado!")
                admin_file = st.file_uploader(
                    "Envie o Excel atualizado:",
                    type=["xlsx", "xls"],
                    key="admin_upload",
                    help="O arquivo será salvo e ficará disponível para todos os visitantes.",
                )
                if admin_file:
                    if st.button("📤 Salvar e Publicar Dados", type="primary"):
                        with st.spinner("Salvando dados no servidor..."):
                            file_bytes = admin_file.getvalue()
                            success, msg = save_data_to_github(file_bytes, admin_file.name)
                        if success:
                            st.success(f"✅ {msg}")
                            st.info("Os dados já estão disponíveis para todos os visitantes!")
                            st.balloons()
                        else:
                            st.error(f"❌ {msg}")
            elif senha and senha != ADMIN_PASSWORD:
                st.error("Senha incorreta.")

        st.markdown("---")

        st.markdown("#### Cores por Unidade")
        for unidade, cor in UNIDADE_COLORS.items():
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
                f'<div style="width:16px;height:16px;border-radius:4px;background:{cor};"></div>'
                f'<span style="color:#64748B;font-size:13px;">{unidade}</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("""
        <div style="padding:10px; background:linear-gradient(135deg, #FFFFFF 0%, #EEF1F8 100%); border-radius:10px; border:1px solid #E2E6F0; margin-top:8px;">
            <p style="color:#64748B; font-size:11px; margin:0; line-height:1.6;">
                <b style="color:#64748B;">📋 Rotina:</b> Dados atualizados toda segunda-feira.<br>
                <b style="color:#64748B;">👥 Visitantes:</b> Visualizam automaticamente os dados mais recentes.
            </p>
        </div>
        """, unsafe_allow_html=True)

    # HEADER
    st.markdown("""
    <div style="display:flex; align-items:center; gap:16px; margin-bottom:16px; padding-bottom:16px; border-bottom:1px solid #E2E6F0;">
        <div style="background:linear-gradient(135deg, #1400FF 0%, #0A00AA 100%); border-radius:12px; padding:14px; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 16px rgba(20,0,255,0.3);">
            <span style="font-size:24px; color:white; font-weight:800; font-family:'Inter',sans-serif;">BSW</span>
        </div>
        <div>
            <h1 style="margin:0; font-size:26px; color:#1F2937 !important; font-weight:800; letter-spacing:-0.5px;">Controle de Matéria-Prima</h1>
            <p style="margin:4px 0 0 0; color:#64748B; font-size:12px; font-weight:500; letter-spacing:0.5px;">BOBINAS BSW — JAN A MAI / 2026 | GRUPO DELGA</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ============================================================
    # CARREGAR DADOS (prioridade: GitHub > SharePoint > vazio)
    # ============================================================
    df_raw = None
    df_formulas = None
    df_propostas_raw = None

    try:
        df_raw, df_formulas, df_propostas_raw = load_data_from_github()
    except Exception:
        df_raw, df_formulas, df_propostas_raw = None, None, None

    if df_raw is None:
        try:
            df_raw, df_formulas, df_propostas_raw = load_data_from_sharepoint()
        except Exception:
            df_raw, df_formulas, df_propostas_raw = None, None, None

    if df_raw is None:
        st.markdown("""
        <div style="text-align:center; padding:80px 20px; background:linear-gradient(135deg, #FFFFFF 0%, #EEF1F8 100%); border:2px dashed #E2E6F0; border-radius:16px; margin:40px auto; max-width:600px;">
            <span style="font-size:64px;">📊</span>
            <h2 style="color:#1F2937 !important; margin:16px 0 8px 0;">Aguardando Dados</h2>
            <p style="color:#64748B; font-size:14px;">
                Nenhum dado disponível ainda.<br><br>
                <b style="color:#64748B;">Administrador:</b> Use a área "Atualizar Dados" no painel lateral
                para enviar o arquivo Excel pela primeira vez.
            </p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    df, col_names = process_data(df_raw)
    df_unidades, df_usinas = parse_formulas(df_formulas)
    df_propostas = process_propostas(df_propostas_raw)

    col_media = col_names.get('media', '')
    if not col_media:
        st.error("Coluna de necessidade média não encontrada no arquivo.")
        st.stop()

    st.markdown(f"""
    <p style="text-align:right; color:#64748B; font-size:12px; font-family:Consolas,monospace;">
        Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}
    </p>
    """, unsafe_allow_html=True)

    # ============================================================
    # KPIs GERAIS
    # ============================================================
    total_bobinas = int(df_unidades['bobinas'].sum()) if len(df_unidades) > 0 else 0
    total_peso = float(df_unidades['peso_total'].sum()) if len(df_unidades) > 0 else 0
    total_peso_analisado = float(df_unidades['peso_analisado'].sum()) if len(df_unidades) > 0 else 0
    total_pct_geral = (total_peso_analisado / total_peso * 100) if total_peso > 0 else 0

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Peso Médio Total (MP)", f"{total_peso:,.0f} ton".replace(",", "."))
    with k2:
        st.metric("Peso Médio Analisado (MP)", f"{total_peso_analisado:,.0f} ton".replace(",", "."))
    with k3:
        st.metric("% Concluído Geral", f"{total_pct_geral:.1f}%")

    # ============================================================
    # SELETOR DE UNIDADE
    # ============================================================
    if len(df_unidades) > 0:
        st.markdown("  ", unsafe_allow_html=True)
        st.markdown("#### Detalhamento por Unidade")

        unidade_names = ["Todas"] + df_unidades['unidade'].tolist()
        selected_unidade = st.selectbox(
            "Selecione a unidade:", unidade_names, index=0, key="unidade_selector"
        )

        if selected_unidade == "Todas":
            u_peso = total_peso
            u_analisado = total_peso_analisado
            u_bobinas = total_bobinas
            u_pct = total_pct_geral
        else:
            row_u = df_unidades[df_unidades['unidade'] == selected_unidade].iloc[0]
            u_bobinas = int(row_u['bobinas'])
            u_peso = float(row_u['peso_total'])
            u_analisado = float(row_u['peso_analisado'])
            u_pct = float(row_u['pct'])

        uk1, uk2, uk3, uk4 = st.columns(4)
        with uk1:
            st.metric("Bobinas", f"{u_bobinas:,}".replace(",", "."))
        with uk2:
            st.metric("Peso Médio Total (MP)", f"{u_peso:,.0f} ton".replace(",", "."))
        with uk3:
            st.metric("Peso Médio Analisado (MP)", f"{u_analisado:,.0f} ton".replace(",", "."))
        with uk4:
            st.metric("% Concluído", f"{u_pct:.1f}%")

    st.markdown("  ", unsafe_allow_html=True)

    # ============================================================
    # ABAS
    # ============================================================
    tab1, tab2, tab3 = st.tabs(["📊 Visão Geral", "🔍 Análises", "🛠️ Acompanhamento"])

    # ── ABA 1: VISÃO GERAL ──
    with tab1:
        col_a, col_b = st.columns([2, 1])
        with col_a:
            render_chart(create_area_chart(df, col_names))
        with col_b:
            fig_tipo = create_tipo_pie_chart(df, col_media)
            if not render_chart(fig_tipo):
                st.info("Coluna 'Tipo' não encontrada.")

        col_c, col_d = st.columns(2)
        with col_c:
            fig_esp = create_thickness_chart(df, col_media)
            if not render_chart(fig_esp):
                st.info("Coluna de espessura não encontrada.")
        with col_d:
            fig_unid = create_unidade_pie_chart(df, col_media)
            if not render_chart(fig_unid):
                st.info("Coluna 'Unidade Delga' não encontrada.")

        fig_usinas = create_usinas_chart(df_usinas, 15)
        if not render_chart(fig_usinas):
            st.info("Dados de usinas não encontrados na aba Formulas.")

    # ── ABA 2: ANÁLISES ──
    with tab2:
        if len(df_unidades) > 0:
            fig_prog = create_progress_chart(df_unidades)
            if not render_chart(fig_prog):
                st.info("Sem dados de progresso.")

            st.markdown("### Progresso de Análise por Unidade")

            df_display = df_unidades[['unidade', 'bobinas', 'peso_total', 'peso_analisado', 'pct']].copy()
            df_display.columns = ['Unidade', 'Bobinas', 'Peso Total (ton)', 'Peso Analisado (ton)', '% Concluído']
            df_display['Peso Total (ton)'] = df_display['Peso Total (ton)'].round(1)
            df_display['Peso Analisado (ton)'] = df_display['Peso Analisado (ton)'].round(1)
            df_display['% Concluído'] = df_display['% Concluído'].apply(lambda x: f"{x:.1f}%")
            st.markdown(build_light_table_html(df_display), unsafe_allow_html=True)
        else:
            st.info("Dados de análise não encontrados na aba Formulas.")

        st.markdown("### Necessidade por Unidade e Beneficiador")
        col_g, col_h = st.columns(2)
        with col_g:
            fig_unid2 = create_unidade_bar_chart(df, col_media)
            if not render_chart(fig_unid2):
                st.info("Coluna 'Unidade Delga' não encontrada.")
        with col_h:
            benef_col = [c for c in df.columns if 'Beneficiador' in c]
            if benef_col:
                fig_benef = create_bar_chart(df, col_media, "Necessidade por Beneficiador (ton)", benef_col[0], 10, COLORS["teal"])
                if not render_chart(fig_benef):
                    st.info("Sem dados de beneficiador.")
            else:
                st.info("Coluna 'Beneficiador' não encontrada.")

        abc_col = [c for c in df.columns if c.strip().upper() == 'ABC']
        if abc_col:
            st.markdown("### Classificação ABC")
            df_abc = df[df[abc_col[0]].notna() & (df[abc_col[0]].astype(str).str.strip() != '')].copy()
            if len(df_abc) > 0:
                abc_dist = df_abc.groupby(abc_col[0])[col_media].agg(['sum', 'count']).sort_values('sum', ascending=False)
                abc_dist.columns = ['Necessidade Total (ton)', 'Qtd Bobinas']
                abc_dist['Necessidade Total (ton)'] = abc_dist['Necessidade Total (ton)'].round(1)
                abc_display = abc_dist.reset_index().rename(columns={abc_dist.index.name or 'index': 'ABC'})
                st.markdown(build_light_table_html(abc_display), unsafe_allow_html=True)

    # ── ABA 3: ACOMPANHAMENTO (Propostas BSW) ──
    with tab3:
        if df_propostas is None or len(df_propostas) == 0:
            st.markdown("""
            <div style="text-align:center; padding:60px 20px; background:linear-gradient(135deg, #FFFFFF 0%, #EEF1F8 100%); border:2px dashed #E2E6F0; border-radius:16px; margin:20px auto; max-width:600px;">
                <span style="font-size:48px;">🛠️</span>
                <h3 style="color:#1F2937 !important; margin:16px 0 8px 0;">Aba "A.Propostas" não encontrada</h3>
                <p style="color:#64748B; font-size:14px;">
                    Envie um arquivo Excel que contenha a aba <b style="color:#64748B;">A.Propostas</b>
                    para visualizar o acompanhamento das propostas de redução BSW.
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("### Filtros")
            fcol1, fcol2 = st.columns(2)
            plantas_disp = sorted(df_propostas['_PLANTA'].unique().tolist())
            fontes_disp = sorted(df_propostas['_FONTE'].unique().tolist())

            with fcol1:
                sel_plantas = st.multiselect("Planta Delga:", plantas_disp, default=plantas_disp, key="prop_planta")
            with fcol2:
                sel_fontes = st.multiselect("Fonte:", fontes_disp, default=fontes_disp, key="prop_fonte")

            df_f = df_propostas[
                df_propostas['_PLANTA'].isin(sel_plantas) & df_propostas['_FONTE'].isin(sel_fontes)
            ].copy()

            st.markdown("  ", unsafe_allow_html=True)

            total_prop = len(df_f)
            formalizadas = int(df_f['_STAGES'].apply(
                lambda stages: bool(stages) and stages[0]['col'] == 'FORMALIZADO COM COMPRAS' and stages[0]['status'] == 'done'
            ).sum())
            enviadas = int(df_f['_PASSADO'].str.contains('SIM', na=False).sum())
            concluidas = int((df_f['_PCT'] == 100).sum())
            pct_medio = float(df_f['_PCT'].mean()) if total_prop else 0

            pc1, pc2, pc3, pc4, pc5 = st.columns(5)
            with pc1:
                st.metric("Total de Propostas", f"{total_prop:,}".replace(",", "."))
            with pc2:
                st.metric("Formalizado com Compras", f"{formalizadas:,}".replace(",", "."))
            with pc3:
                st.metric("Enviadas à Usina", f"{enviadas:,}".replace(",", "."))
            with pc4:
                st.metric("Concluídas (100%)", f"{concluidas:,}".replace(",", "."))
            with pc5:
                st.metric("Progresso Médio", f"{pct_medio:.0f}%")

            st.markdown("  ", unsafe_allow_html=True)

            if total_prop == 0:
                st.info("Nenhuma proposta encontrada para os filtros selecionados.")
            else:
                fig_prop_prog = create_propostas_progress_chart(df_f)
                if fig_prop_prog is not None:
                    render_chart(fig_prop_prog)

                st.markdown("### Linha do Tempo por Proposta")

                # Toggles logo abaixo do título da timeline
                tcol1, tcol2, _tcol3 = st.columns([1, 1, 2])
                with tcol1:
                    only_pend_compras = st.toggle(
                        "Pendente Formalização c/ Compras",
                        key="toggle_pendente_compras",
                        help="Mostra apenas propostas ainda não formalizadas com Compras.",
                    )
                with tcol2:
                    only_pend_usina = st.toggle(
                        "Pendente Envio à Usina",
                        key="toggle_pendente_usina",
                        help="Mostra apenas propostas ainda não enviadas à usina.",
                    )

                df_tl = df_f.copy()
                if only_pend_compras:
                    df_tl = df_tl[df_tl['_STAGES'].apply(
                        lambda stages: bool(stages) and stages[0]['col'] == 'FORMALIZADO COM COMPRAS' and stages[0]['status'] != 'done'
                    )]
                if only_pend_usina:
                    df_tl = df_tl[df_tl['_STAGES'].apply(
                        lambda stages: bool(stages) and len(stages) > 1
                        and stages[1]['col'] == 'DATA ENVIO P/ USINA' and stages[1]['status'] not in ('done', 'na')
                    )]

                st.markdown(
                    '<p style="color:#64748B; font-size:12px; margin-top:4px;">'
                    'Cada bolinha representa uma das 8 etapas do processo. '
                    '<span style="color:#1400FF;">●</span> concluída / não se aplica &nbsp; '
                    '<span style="color:#FFB800;">○</span> pendente &nbsp; '
                    '<span style="color:#4DA3FF;">○</span> prevista (data futura) &nbsp; '
                    '<span style="color:#D1D7E3;">○</span> não iniciada'
                    '</p>',
                    unsafe_allow_html=True,
                )

                if len(df_tl) == 0:
                    st.info("Nenhuma proposta corresponde aos filtros de pendência selecionados.")
                else:
                    # Ordena: planta na ordem padrão Delga primeiro, depois alfabética
                    ordem_preferida = ['FERRAZ', 'DIADEMA', 'JARINU', 'SUL']
                    plantas_ordenadas = sorted(
                        df_tl['_PLANTA'].unique().tolist(),
                        key=lambda p: (ordem_preferida.index(p) if p in ordem_preferida else 99, p)
                    )

                full_html = ""
                for planta in plantas_ordenadas:
                    df_grupo = df_tl[df_tl['_PLANTA'] == planta].sort_values('_PCT', ascending=True)
                    full_html += render_acompanhamento_block(planta, df_grupo)

                st.markdown(full_html, unsafe_allow_html=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("O dashboard encontrou um erro e foi protegido para não ficar em tela branca.")
        st.exception(e)
