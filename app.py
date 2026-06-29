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

# Força o Python a usar a convenção de números e moedas do Brasil
try:
    locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_ALL, "Portuguese_Brazil.1252")
    except:
        pass 

# Inversão de pontos e vírgulas para o formato brasileiro padrão
def formatar_br(valor):
    try:
        txt = f"{valor:,.2f}"
        return txt.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return f"{valor}"

# Remove acentos temporariamente para ordenação alfabética
def remover_acentos(texto):
    if not isinstance(texto, str):
        return ""
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

# --- FUNÇÕES ADAPTADAS PARA O GOOGLE SHEETS ---
def carregar_transacoes():
    colunas = ["Data", "Tipo", "Categoria", "Subcategoria", "Conta", "Valor", "Observacoes"]
    df = carregar_aba_sheets("transacoes", colunas)
    
    if df.empty:
        return df
        
    mapeamento = {}
    for col in df.columns:
        col_normalizada = col.lower()
        if "data" in col_normalizada: mapeamento[col] = "Data"
        elif "tipo" in col_normalizada: mapeamento[col] = "Tipo"
        elif "sub" in col_normalizada: mapeamento[col] = "Subcategoria"
        elif "categ" in col_normalizada: mapeamento[col] = "Categoria"
        elif "cont" in col_normalizada: mapeamento[col] = "Conta"
        elif "val" in col_normalizada or "preço" in col_normalizada or "total" in col_normalizada: mapeamento[col] = "Valor"
        elif "obs" in col_normalizada: mapeamento[col] = "Observacoes"
    
    df = df.rename(columns=mapeamento)
    
    for col_obrigatoria in colunas:
        if col_obrigatoria not in df.columns:
            df[col_obrigatoria] = ""
            
    for col in ["Tipo", "Categoria", "Subcategoria", "Conta", "Observacoes"]:
        df[col] = df[col].astype(str).str.replace(r'\r+|\n+', ' ', regex=True).str.strip().replace("nan", "")
        
    df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0.0).apply(abs)
    
    def formatar_data_antiga(txt):
        txt_limpo = str(txt).split()[0].strip()
        for formato in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                dt = datetime.strptime(txt_limpo, formato)
                return dt.strftime("%d/%m/%Y")
            except ValueError:
                continue
        return txt_limpo
        
    df["Data"] = df["Data"].apply(formatar_data_antiga)
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
    return {
        "Receita": ["Freela", "Investimentos", "Outros", "Salário"],
        "Despesa": ["Alimentação", "Lazer", "Moradia", "Outros", "Transporte"]
    }

def salvar_categorias(dict_cats):
    dict_ordenado = {
        "Receita": ordenar_lista_sem_acentos(dict_cats["Receita"]),
        "Despesa": ordenar_lista_sem_acentos(dict_cats["Despesa"])
    }
    df_cats = pd.DataFrame(dict([ (k, pd.Series(v)) for k, v in dict_ordenado.items() ]))
    salvar_aba_sheets(df_cats, "categorias")

def carregar_subcategorias():
    df_sub = carregar_aba_sheets("subcategorias", ["Subcategoria"])
    if not df_sub.empty and "Subcategoria" in df_sub.columns:
        return ordenar_lista_sem_acentos(df_sub["Subcategoria"].dropna().astype(str).tolist())
    return ordenar_lista_sem_acentos(["Aluguel", "Combustível", "Farmácia", "Internet", "Restaurante", "Supermercado"])

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
        return df_prev[["Descrição", "Valor", "Débito em Conta?", "Valor Pago?"]]
    return pd.DataFrame(columns=["Descrição", "Valor", "Débito em Conta?", "Valor Pago?"])

def salvar_previsoes(df_prev):
    salvar_aba_sheets(df_prev, "previsoes")


# --- INICIALIZAÇÃO DO ESTADO ---
if "transacoes" not in st.session_state: st.session_state.transacoes = carregar_transacoes()
if "categorias" not in st.session_state: st.session_state.categorias = carregar_categorias()
if "subcategorias" not in st.session_state: st.session_state.subcategorias = carregar_subcategorias()
if "contas" not in st.session_state: st.session_state.contas = carregar_contas()
if "previsoes" not in st.session_state: st.session_state.previsoes = carregar_previsoes()

# --- TÍTULO DO SISTEMA ---
st.title("Controle Financeiro")

tab_dash, tab_lançamentos, tab_analise, tab_historico, tab_categorias, tab_subcategorias, tab_contas, tab_previsao = st.tabs([
    "🏠 Tela Inicial", "💸 Novo Lançamento", "📊 Análise dos dados", "📋 Histórico", "🗂️ Categorias", "📂 Subcategorias", "🏦 Contas", "🔮 Previsão de Gastos"
])

df = st.session_state.transacoes.copy()
df["Valor"] = pd.to_numeric(df["Valor"], errors='coerce').fillna(0.0)
df["Subcategoria"] = df["Subcategoria"].fillna("").str.strip()
df["Observacoes"] = df["Observacoes"].fillna("")

# --- ABA 1: TELA INICIAL ---
with tab_dash:
    sub_tab_contas, sub_tab_cartao = st.tabs(["🏦 Contas e Patrimônio", "💳 Cartão de Crédito"])
    
    with sub_tab_contas:
        st.header("Resumo Geral de Contas")
        lista_saldos_contas = []
        soma_dinheiro_bancos = 0.0
        
        contas_para_saldos = sorted([c for c in st.session_state.contas if str(c).strip() != "" and "cartão" not in str(c).lower() and "cred" not in str(c).lower()])

        for conta in contas_para_saldos:
            rec_conta = df[(df["Tipo"] == "Receita") & (df["Conta"] == conta)]["Valor"].sum()
            des_conta = df[(df["Tipo"] == "Despesa") & (df["Conta"] == conta)]["Valor"].sum()
            saldo_conta = rec_conta - des_conta
            soma_dinheiro_bancos += saldo_conta
            
            if saldo_conta > 0:
                lista_saldos_contas.append({"Conta": conta, "Saldo": saldo_conta})
                
        if df.empty:
            st.info("Nenhuma transação cadastrada ainda.")
        else:
            col_total, _ = st.columns([1, 2])
            with col_total:
                st.metric("Patrimônio Líquido Disponível", f"R$ {formatar_br(soma_dinheiro_bancos)}")
            
            st.markdown("---")
            col_graf, col_saldos = st.columns([1.2, 1])
            
            with col_saldos:
                st.markdown("### 🏦 Saldo Atual por Conta")
                for conta in contas_para_saldos:
                    rec_conta = df[(df["Tipo"] == "Receita") & (df["Conta"] == conta)]["Valor"].sum()
                    des_conta = df[(df["Tipo"] == "Despesa") & (df["Conta"] == conta)]["Valor"].sum()
                    saldo_real_conta = rec_conta - des_conta
                    
                    if saldo_real_conta >= 0:
                        st.write(f"• **{conta}:** <span style='color:#2ecc71'>R$ {formatar_br(saldo_real_conta)}</span>", unsafe_allow_html=True)
                    else:
                        st.write(f"• **{conta}:** <span style='color:#e74c3c'>R$ {formatar_br(saldo_real_conta)}</span>", unsafe_allow_html=True)
            
            with col_graf:
                st.markdown("### Distribuição dos Saldos")
                if lista_saldos_contas:
                    df_saldos_graf = pd.DataFrame(lista_saldos_contas)
                    fig = px.pie(df_saldos_graf, values="Saldo", names="Conta", hole=0.3, color_discrete_sequence=px.colors.qualitative.Safe)
                    st.plotly_chart(fig, use_container_width=True)

    with sub_tab_cartao:
        st.header("💳 Controle do Cartão")
        df_cartao = df[df["Conta"] == "Cartão créd. Nubank"].copy()
        
        if df_cartao.empty:
            st.info("Nenhuma movimentação para o Cartão de Crédito Nubank.")
        else:
            fatura_atual = df_cartao[df_cartao["Tipo"] == "Despesa"]["Valor"].sum() - df_cartao[df_cartao["Tipo"] == "Receita"]["Valor"].sum()
            st.metric(label="Fatura Atual Estimada", value=f"R$ {formatar_br(fatura_atual)}")
            st.dataframe(df_cartao[["Data", "Tipo", "Categoria", "Valor", "Observacoes"]], use_container_width=True)

# --- ABA 2: NOVO LANÇAMENTO ---
with tab_lançamentos:
    st.header("Cadastrar Transação")
    if not st.session_state.contas:
        st.warning("⚠️ Você precisa de contas cadastradas!")
    else:
        col_t, col_c = st.columns(2)
        tipo = col_t.selectbox("Tipo de Movimentação", ["Despesa", "Receita"])
        conta_selecionada = col_c.selectbox("Conta", st.session_state.contas)
        
        with st.form("form_transacao", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            data_selecionada = col_f1.date_input("Data", datetime.now(), format="DD/MM/YYYY")
            categoria = col_f2.selectbox("Categoria", st.session_state.categorias[tipo])
            valor = col_f1.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", value=None)
            subcategoria_sel = col_f2.selectbox("Subcategoria (Opcional)", ["(Nenhuma)"] + st.session_state.subcategorias)
            observacao = st.text_input("Observações (Opcional)").strip()
            
            if st.form_submit_button("Salvar Transação"):
                if valor and valor > 0:
                    sub_final = "" if subcategoria_sel == "(Nenhuma)" else subcategoria_sel
                    nova_linha = pd.DataFrame([[data_selecionada.strftime('%d/%m/%Y'), tipo, categoria, sub_final, conta_selecionada, valor, observacao]], columns=colunas_padrao)
                    st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_linha], ignore_index=True)
                    salvar_transacoes(st.session_state.transacoes)
                    st.success("Salvo com sucesso!")
                    st.rerun()

# --- ABA 4: HISTÓRICO ---
with tab_historico:
    st.header("📋 Histórico de Lançamentos")
    if df.empty:
        st.info("Nenhum lançamento encontrado.")
    else:
        df["ID"] = df.index
        st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

# --- ABAS DE GERENCIAMENTO (SIMPLIFICADAS PARA NUVEM) ---
with tab_categorias:
    st.header("🗂️ Categorias Ativas")
    st.write(st.session_state.categorias)

with tab_subcategorias:
    st.header("📂 Subcategorias Ativas")
    st.write(st.session_state.subcategorias)

with tab_contas:
    st.header("🏦 Contas Ativas")
    st.write(st.session_state.contas)

with tab_previsao:
    st.header("🔮 Previsão de Gastos Futuros")
    st.dataframe(st.session_state.previsoes, use_container_width=True)
