import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale
import unicodedata

# Configuração da página - DEVE SER A PRIMEIRA COISA DO CÓDIGO
st.set_page_config(page_title="Controle Financeiro", page_icon="💰", layout="wide")

# --- AJUSTE ESTÉTICO: REMOVER ESPAÇO E FIXAR MENU NO TOPO ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
        [data-testid="stHeader"] { z-index: 99; }
    </style>
""", unsafe_allow_html=True)

# Força o Python a usar a convenção de números e moedas
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

# --- CONEXÃO ROBUSTA COM GOOGLE SHEETS ---
try:
    from streamlit_gsheets import GSheetsConnection
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("❌ Erro crítico ao carregar o conector do Google Sheets.")
    st.info("Certifique-se de que o arquivo 'requirements.txt' contém exatamente a linha: st-gsheets-connection")
    st.exception(e)
    st.stop()

def carregar_transacoes():
    try:
        df = conn.read(worksheet="transacoes", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Subcategoria", "Conta", "Valor", "Observacoes"])
        
        df.columns = [str(c).strip() for c in df.columns]
        if "Valor" in df.columns:
            df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0.0).apply(abs)
        if "Data" in df.columns:
            df["Data"] = df["Data"].astype(str)
        return df
    except Exception as e:
        # Se der erro ou a aba não existir, evita tela branca e cria o DataFrame vazio
        return pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Subcategoria", "Conta", "Valor", "Observacoes"])

def salvar_transacoes(df):
    try:
        conn.update(worksheet="transacoes", data=df)
    except Exception as e:
        st.error(f"Erro ao salvar transações no Google Sheets: {e}")

def carregar_categorias():
    try:
        df_cats = conn.read(worksheet="categorias", ttl=0)
        if df_cats is None or df_cats.empty:
            return {"Receita": ["Freela", "Salário"], "Despesa": ["Alimentação", "Lazer", "Moradia"]}
        return {
            "Receita": ordenar_lista_sem_acentos(df_cats["Receita"].dropna().tolist()) if "Receita" in df_cats.columns else ["Freela", "Salário"],
            "Despesa": ordenar_lista_sem_acentos(df_cats["Despesa"].dropna().tolist()) if "Despesa" in df_cats.columns else ["Alimentação", "Lazer", "Moradia"]
        }
    except:
        return {"Receita": ["Freela", "Salário"], "Despesa": ["Alimentação", "Lazer", "Moradia"]}

def salvar_categorias(dict_cats):
    try:
        dict_ordenado = {
            "Receita": ordenar_lista_sem_acentos(dict_cats["Receita"]),
            "Despesa": ordenar_lista_sem_acentos(dict_cats["Despesa"])
        }
        df_cats = pd.DataFrame(dict([ (k, pd.Series(v)) for k, v in dict_ordenado.items() ]))
        conn.update(worksheet="categorias", data=df_cats)
    except Exception as e:
        st.error(f"Erro ao salvar categorias: {e}")

def carregar_subcategorias():
    try:
        df_sub = conn.read(worksheet="subcategorias", ttl=0)
        if df_sub is not None and "Subcategoria" in df_sub.columns:
            return ordenar_lista_sem_acentos(df_sub["Subcategoria"].dropna().tolist())
    except:
        pass
    return ordenar_lista_sem_acentos(["Combustível", "Supermercado"])

def salvar_subcategorias(lista_subs):
    try:
        df_sub = pd.DataFrame({"Subcategoria": ordenar_lista_sem_acentos(lista_subs)})
        conn.update(worksheet="subcategorias", data=df_sub)
    except Exception as e:
        st.error(f"Erro ao salvar subcategorias: {e}")

def carregar_contas():
    try:
        df_contas = conn.read(worksheet="contas", ttl=0)
        if df_contas is not None and "Conta" in df_contas.columns:
            return df_contas["Conta"].dropna().tolist()
    except:
        pass
    return ["Cartão créd. Nubank", "Conta Nubank", "Itaú"]

def salvar_contas(lista_contas):
    try:
        df_contas = pd.DataFrame({"Conta": lista_contas})
        conn.update(worksheet="contas", data=df_contas)
    except Exception as e:
        st.error(f"Erro ao salvar contas: {e}")

def carregar_previsoes():
    try:
        df_prev = conn.read(worksheet="previsoes", ttl=0)
        if df_prev is None or df_prev.empty:
            return pd.DataFrame(columns=["Descrição", "Valor", "Débito em Conta?", "Valor Pago?"])
        df_prev["Valor"] = pd.to_numeric(df_prev["Valor"], errors='coerce').fillna(0.0)
        df_prev["Débito em Conta?"] = df_prev["Débito em Conta?"].fillna(False).astype(bool)
        df_prev["Valor Pago?"] = df_prev["Valor Pago?"].fillna(False).astype(bool)
        return df_prev[["Descrição", "Valor", "Débito em Conta?", "Valor Pago?"]]
    except:
        return pd.DataFrame(columns=["Descrição", "Valor", "Débito em Conta?", "Valor Pago?"])

def salvar_previsoes(df_prev):
    try:
        conn.update(worksheet="previsoes", data=df_prev)
    except Exception as e:
        st.error(f"Erro ao salvar previsões: {e}")

# --- INICIALIZAÇÃO DO ESTADO ---
if "transacoes" not in st.session_state: st.session_state.transacoes = carregar_transacoes()
if "categorias" not in st.session_state: st.session_state.categorias = carregar_categorias()
if "subcategorias" not in st.session_state: st.session_state.subcategorias = carregar_subcategorias()
if "contas" not in st.session_state: st.session_state.contas = carregar_contas()
if "previsoes" not in st.session_state: st.session_state.previsoes = carregar_previsoes()

# O restante do código visual das abas continua aqui abaixo...
