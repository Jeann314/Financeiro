import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale
import unicodedata
from streamlit_gsheets import GSheetsConnection

# Configuração da página
st.set_page_config(page_title="Controle Financeiro", page_icon="💰", layout="wide")

# --- AJUSTE ESTÉTICO ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
        [data-testid="stHeader"] { z-index: 99; }
    </style>
""", unsafe_allow_html=True)

# Força a convenção de moedas do Brasil
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except:
        pass 

def formatar_br(valor):
    try:
        txt = f"{valor:,.2f}"
        return txt.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"{valor}"

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def ordenar_lista_sem_acentos(lista):
    return sorted(lista, key=remover_acentos)

# --- CONEXÃO COM O GOOGLE SHEETS VIA SECRETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_aba_sheets(nome_aba, colunas_padrao):
    try:
        df = conn.read(worksheet=nome_aba, ttl=5)
        if df.empty:
            return pd.DataFrame(columns=colunas_padrao)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame(columns=colunas_padrao)

def salvar_aba_sheets(df, nome_aba):
    try:
        conn.update(worksheet=nome_aba, data=df)
    except Exception as e:
        st.error(f"Erro ao salvar na nuvem (Aba {nome_aba}): {e}")

# --- FUNÇÕES DE CARREGAMENTO ADAPTADAS ---
def carregar_transacoes():
    colunas = ["Data", "Tipo", "Categoria", "Subcategoria", "Conta", "Valor", "Observacoes"]
    df = carregar_aba_sheets("transacoes", colunas)
    if df.empty: return df
    
    mapeamento = {}
    for col in df.columns:
        col_normalizada = col.lower()
        if "data" in col_normalizada: mapeamento[col] = "Data"
        elif "tipo" in col_normalizada: mapeamento[col] = "Tipo"
        elif "sub" in col_normalizada: mapeamento[col] = "Subcategoria"
        elif "categ" in col_normalizada: mapeamento[col] = "Categoria"
        elif "cont" in col_normalizada: mapeamento[col] = "Conta"
        elif "val" in col_normalizada: mapeamento[col] = "Valor"
        elif "obs" in col_normalizada: mapeamento[col] = "Observacoes"
    
    df = df.rename(columns=mapeamento)
    for c in colunas:
        if c not in df.columns: df[c] = ""
        
    for col in ["Tipo", "Categoria", "Subcategoria", "Conta", "Observacoes"]:
        df[col] = df[col].astype(str).str.replace(r'\r+|\n+', ' ', regex=True).str.strip().replace("nan", "")
    df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0.0).apply(abs)
    return df[colunas]

def salvar_transacoes(df_transacoes):
    salvar_aba_sheets(df_transacoes, "transacoes")

def carregar_categorias():
    df_cats = carregar_aba_sheets("categorias", ["Receita", "Despesa"])
    if not df_cats.empty and "Receita" in df_cats.columns and "Despesa" in df_cats.columns:
        return {
            "Receita": ordenar_lista_sem_acentos(df_cats["Receita"].dropna().astype(str).tolist()),
            "Despesa": ordenar_lista_sem_acentos(df_cats["Despesa"].dropna().astype(str).tolist())
        }
    return {"Receita": ["Freela", "Investimentos", "Outros", "Salário"], "Despesa": ["Alimentação", "Lazer", "Moradia", "Outros", "Transporte"]}

def salvar_categorias(dict_cats):
    df_cats = pd.DataFrame(dict([ (k, pd.Series(v)) for k, v in dict_cats.items() ]))
    salvar_aba_sheets(df_cats, "categorias")

def carregar_subcategorias():
    df_sub = carregar_aba_sheets("subcategorias", ["Subcategoria"])
    if not df_sub.empty and "Subcategoria" in df_sub.columns:
        return ordenar_lista_sem_acentos(df_sub["Subcategoria"].dropna().astype(str).tolist())
    return ["Aluguel", "Combustível", "Farmácia", "Internet", "Restaurante", "Supermercado"]

def salvar_subcategorias(lista_subs):
    df_sub = pd.DataFrame({"Subcategoria": ordenar_lista_sem_acentos(lista_subs)})
    salvar_aba_sheets(df_sub, "subcategorias")

def carregar_contas():
    df_contas = carregar_aba_sheets("contas", ["Conta"])
    if not df_contas.empty and "Conta" in df_contas.columns:
        return df_contas["Conta"].dropna().astype(str).tolist()
    return ["Cartão créd. Nubank", "CEF", "Conta Nubank", "dinheiro em espécie", "Itaú"]

def salvar_contas(lista_contas):
    df_contas = pd.DataFrame({"Conta": lista_contas})
    salvar_aba_sheets(df_contas, "contas")

def carregar_previsoes():
    df_prev = carregar_aba_sheets("previsoes", ["Descrição", "Valor", "Débito em Conta?", "Valor Pago?"])
    if not df_prev.empty:
        df_prev["Valor"] = pd.to_numeric(df_prev["Valor"], errors='coerce').fillna(0.0)
        df_prev["Débito em Conta?"] = df_prev["Débito em Conta?"].fillna(False).astype(bool)
        df_prev["Valor Pago?"] = df_prev["Valor Pago?"].fillna(False).astype(bool)
        return df_prev
    return pd.DataFrame(columns=["Descrição", "Valor", "Débito em Conta?", "Valor Pago?"])

def salvar_previsoes(df_prev):
    salvar_aba_sheets(df_prev, "previsoes")

# --- INICIALIZAÇÃO ---
if "transacoes" not in st.session_state: st.session_state.transacoes = carregar_transacoes()
if "categorias" not in st.session_state: st.session_state.categorias = carregar_categorias()
if "subcategorias" not in st.session_state: st.session_state.subcategorias = carregar_subcategorias()
if "contas" not in st.session_state: st.session_state.contas = carregar_contas()
if "previsoes" not in st.session_state: st.session_state.previsoes = carregar_previsoes()

# --- INTERFACE ---
st.title("Controle Financeiro")

tab_dash, tab_lançamentos, tab_analise, tab_historico, tab_categorias, tab_subcategorias, tab_contas, tab_previsao = st.tabs([
    "🏠 Tela Inicial", "💸 Novo Lançamento", "📊 Análise", "📋 Histórico", "🗂️ Categorias", "📂 Subcategorias", "🏦 Contas", "🔮 Previsão"
])

df = st.session_state.transacoes.copy()

with tab_dash:
    st.subheader("Resumo de Patrimônio")
    soma_geral = df[df["Tipo"] == "Receita"]["Valor"].sum() - df[df["Tipo"] == "Despesa"]["Valor"].sum()
    st.metric("Saldo Estimado Geral", f"R$ {formatar_br(soma_geral)}")
    if not df.empty:
        st.dataframe(df.tail(10), use_container_width=True)

with tab_lançamentos:
    with st.form("form_transacao", clear_on_submit=True):
        col1, col2 = st.columns(2)
        tipo = col1.selectbox("Tipo", ["Despesa", "Receita"])
        conta = col2.selectbox("Conta", st.session_state.contas)
        cat = col1.selectbox("Categoria", st.session_state.categorias[tipo])
        val = col2.number_input("Valor", min_value=0.0, step=1.0)
        obs = st.text_input("Observação")
        
        if st.form_submit_button("Salvar"):
            nova_linha = pd.DataFrame([[datetime.now().strftime('%d/%m/%Y'), tipo, cat, "", conta, val, obs]], columns=df.columns)
            st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_linha], ignore_index=True)
            salvar_transacoes(st.session_state.transacoes)
            st.success("Salvo!")
            st.rerun()

with tab_historico:
    st.dataframe(df, use_container_width=True)
    if st.button("Limpar Tudo (Cuidado!)"):
        st.session_state.transacoes = pd.DataFrame(columns=df.columns)
        salvar_transacoes(st.session_state.transacoes)
        st.rerun()

with tab_categorias:
    st.write("Categorias Atuais:", st.session_state.categorias)

with tab_subcategorias:
    st.write("Subcategorias:", st.session_state.subcategorias)

with tab_contas:
    st.write("Contas Ativas:", st.session_state.contas)

with tab_previsao:
    st.write("Previsões de Gastos:")
    st.dataframe(st.session_state.previsoes, use_container_width=True)
