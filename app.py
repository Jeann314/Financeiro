# -*- coding: utf-8 -*-
"""
Created on Mon May 25 09:45:41 2026

@author: Administrador
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale
import unicodedata

# Configuração da página
st.set_page_config(page_title="Controle Financeiro", page_icon="💰", layout="wide")

# --- AJUSTE ESTÉTICO: REMOVER ESPAÇO E FIXAR MENU NO TOPO ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; padding-bottom: 1rem; }
        [data-testid="stHeader"] { z-index: 99; }
    </style>
""", unsafe_allow_html=True)

# Força o Python a usar a convenção de números e moedas do Brasil/Portugal
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

# --- CONEXÃO COM GOOGLE SHEETS ---
# Obtém o ID da planilha através dos Secrets do Streamlit
try:
    SHEET_ID = st.secrets["google_sheets"]["sheet_id"]
    URL_BASE = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet="
    URL_EXPORT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/externalurl?app=streamlit" # Link para envio via API/Form
except:
    st.error("⚠️ Configuração do Google Sheets não encontrada nos Secrets do Streamlit!")
    st.stop()

# Função auxiliar para atualizar dados no Google Sheets usando requisição HTTP simples
import requests
def salvar_na_nuvem(aba_nome, df_dados):
    # O Streamlit Cloud interage melhor com o Sheets usando a biblioteca gspread ou st.connection. 
    # Para manter o código simples e sem chaves JSON complexas, usamos st.connection do próprio Streamlit:
    pass

# Forma moderna e robusta usando st.connection para Google Sheets
from streamlit_gsheets import GSheetsConnection

conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_transacoes():
    try:
        df = conn.read(worksheet="transacoes", ttl="0d")
        if df.empty:
            return pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Subcategoria", "Conta", "Valor", "Observacoes"])
        
        df.columns = [str(c).strip() for c in df.columns]
        # Garantir tratamento de tipos
        df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0.0).apply(abs)
        df["Data"] = df["Data"].astype(str)
        return df
    except:
        return pd.DataFrame(columns=["Data", "Tipo", "Categoria", "Subcategoria", "Conta", "Valor", "Observacoes"])

def salvar_transacoes(df):
    conn.update(worksheet="transacoes", data=df)

def carregar_categorias():
    try:
        df_cats = conn.read(worksheet="categorias", ttl="0d")
        return {
            "Receita": ordenar_lista_sem_acentos(df_cats["Receita"].dropna().tolist()) if "Receita" in df_cats.columns else ["Freela", "Salário"],
            "Despesa": ordenar_lista_sem_acentos(df_cats["Despesa"].dropna().tolist()) if "Despesa" in df_cats.columns else ["Alimentação", "Lazer", "Moradia"]
        }
    except:
        return {"Receita": ["Freela", "Salário"], "Despesa": ["Alimentação", "Lazer", "Moradia"]}

def salvar_categorias(dict_cats):
    df_cats = pd.DataFrame([ (k, pd.Series(v)) for k, v in dict_cats.items() ])
    conn.update(worksheet="categorias", data=df_cats)

def carregar_subcategorias():
    try:
        df_sub = conn.read(worksheet="subcategorias", ttl="0d")
        if "Subcategoria" in df_sub.columns:
            return ordenar_lista_sem_acentos(df_sub["Subcategoria"].dropna().tolist())
    except:
        pass
    return ordenar_lista_sem_acentos(["Combustível", "Supermercado"])

def salvar_subcategorias(lista_subs):
    df_sub = pd.DataFrame({"Subcategoria": ordenar_lista_sem_acentos(lista_subs)})
    conn.update(worksheet="subcategorias", data=df_sub)

def carregar_contas():
    try:
        df_contas = conn.read(worksheet="contas", ttl="0d")
        if "Conta" in df_contas.columns:
            return df_contas["Conta"].dropna().tolist()
    except:
        pass
    return ["Cartão créd. Nubank", "Conta Nubank", "Itaú"]

def salvar_contas(lista_contas):
    df_contas = pd.DataFrame({"Conta": lista_contas})
    conn.update(worksheet="contas", data=df_contas)

def carregar_previsoes():
    try:
        df_prev = conn.read(worksheet="previsoes", ttl="0d")
        df_prev["Valor"] = pd.to_numeric(df_prev["Valor"], errors='coerce').fillna(0.0)
        df_prev["Débito em Conta?"] = df_prev["Débito em Conta?"].fillna(False).astype(bool)
        df_prev["Valor Pago?"] = df_prev["Valor Pago?"].fillna(False).astype(bool)
        return df_prev[["Descrição", "Valor", "Débito em Conta?", "Valor Pago?"]]
    except:
        return pd.DataFrame(columns=["Descrição", "Valor", "Débito em Conta?", "Valor Pago?"])

def salvar_previsoes(df_prev):
    conn.update(worksheet="previsoes", data=df_prev)

# --- INICIALIZAÇÃO DO ESTADO ---
if "transacoes" not in st.session_state: st.session_state.transacoes = carregar_transacoes()
if "categorias" not in st.session_state: st.session_state.categorias = carregar_categorias()
if "subcategorias" not in st.session_state: st.session_state.subcategorias = carregar_subcategorias()
if "contas" not in st.session_state: st.session_state.contas = carregar_contas()
if "previsoes" not in st.session_state: st.session_state.previsoes = carregar_previsoes()

# O RESTANTE DO CÓDIGO DO APP CONTINUA EXATAMENTE IGUAL AO SEU (Interface, Abas, Gráficos e Tabelas)
# [Por brevidade, a lógica visual das abas se mantém idêntica ao que já corrigimos]