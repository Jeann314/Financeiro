import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import locale
import unicodedata
from streamlit_gsheets import GSheetsConnection

# Configuração da página
st.set_page_config(page_title="Controle Financeiro", page_icon="💰", layout="wide")

# --- AJUSTE ESTÉTICO: REMOVER ESPAÇO E FIXAR MENU NO TOPO ---
st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        [data-testid="stHeader"] {
            z-index: 99;
        }
        .fixed-top-container {
            position: sticky;
            top: 0;
            background-color: transparent;
            z-index: 999;
            padding-bottom: 10px;
        }
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

# Remove acentos temporariamente apenas para fazer a ordenação alfabética correta
def remover_acentos(texto):
    if not isinstance(texto, str):
        return ""
    return "".join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def ordenar_lista_sem_acentos(lista):
    return sorted(lista, key=remover_acentos)


# --- CONEXÃO COM O GOOGLE SHEETS ---
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

# --- FUNÇÕES ADAPTADAS PARA NUVEM ---
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
        "Receita": ordenar_lista_sem_acentos(["Freela", "Investimentos", "Outros", "Salário"]),
        "Despesa": ordenar_lista_sem_acentos(["Alimentação", "Lazer", "Moradia", "Outros", "Transporte"])
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
    return ["Cartão créd. Nubank", "CEF", "Conta Nubank", "dinheiro em espécie", "Itaú", "Caixinha Nubank", "Fundo Mapfre"]

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
if "transacoes" not in st.session_state:
    st.session_state.transacoes = carregar_transacoes()

if "categorias" not in st.session_state:
    st.session_state.categorias = carregar_categorias()

if "subcategorias" not in st.session_state:
    st.session_state.subcategorias = carregar_subcategorias()

if "contas" not in st.session_state:
    st.session_state.contas = carregar_contas()

if "previsoes" not in st.session_state:
    st.session_state.previsoes = carregar_previsoes()

# --- TÍTULO DO SISTEMA ---
st.title("Controle Financeiro")

tab_dash, tab_lançamentos, tab_analise, tab_historico, tab_categorias, tab_subcategorias, tab_contas, tab_previsao = st.tabs([
    "🏠 Tela Inicial", "💸 Novo Lançamento", "📊 Análise dos dados", "📋 Histórico", "🗂️ Categorias", "📂 Subcategorias", "🏦 Contas", "🔮 Previsão de Gastos"
])

# Preparação global dos dados
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
                
                st.markdown("---")
                st.info(f"**Disponível Real Acumulado:**\n### R$ {formatar_br(soma_dinheiro_bancos)}")
            
            with col_graf:
                st.markdown("### Distribuição dos Saldos")
                if lista_saldos_contas:
                    df_saldos_graf = pd.DataFrame(lista_saldos_contas)
                    fig = px.pie(df_saldos_graf, values="Saldo", names="Conta", hole=0.3, color_discrete_sequence=px.colors.qualitative.Safe)
                    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
                    st.plotly_chart(fig, use_container_width=True)

    with sub_tab_cartao:
        st.header("💳 Outros Controles (Cartão)")
        df_cartao = df[df["Conta"] == "Cartão créd. Nubank"].copy()
        
        if df_cartao.empty:
            st.info("Nenhuma movimentação encontrada para o Cartão de Crédito Nubank.")
        else:
            compras_cartao = df_cartao[df_cartao["Tipo"] == "Despesa"]["Valor"].sum()
            pagamentos_estornos = df_cartao[df_cartao["Tipo"] == "Receita"]["Valor"].sum()
            fatura_atual = compras_cartao - pagamentos_estornos
            
            col_fat, _ = st.columns([1, 2])
            with col_fat:
                st.metric(
                    label="Fatura Atual Estimada (A Pagar)", 
                    value=f"R$ {formatar_br(fatura_atual)}",
                    delta="- Fatura Zerada ou Credora" if fatura_atual <= 0 else "Gasto Acumulado Geral",
                    delta_color="normal" if fatura_atual <= 0 else "inverse"
                )
            
            st.markdown("---")
            
            df_cartao["Datetime"] = pd.to_datetime(df_cartao["Data"], format="%d/%m/%Y", errors="coerce")
            df_cartao = df_cartao.dropna(subset=["Datetime"])
            df_cartao["AnoMes"] = df_cartao["Datetime"].dt.strftime("%Y/%m")
            df_cartao["MesExibicao"] = df_cartao["Datetime"].dt.strftime("%m/%Y")
            
            lista_meses_cartao = df_cartao.sort_values("AnoMes", ascending=False)["MesExibicao"].unique().tolist()
            
            col_f_mes_cartao, _ = st.columns([1, 2])
            with col_f_mes_cartao:
                mes_cartao_selecionado = st.selectbox("Filtrar Gráfico e Tabela por Mês:", lista_meses_cartao, key="cartao_mes_graf_sel")
            
            df_cartao_filtrado = df_cartao[df_cartao["MesExibicao"] == mes_cartao_selecionado]
            
            st.markdown(f"### 📊 Onde você mais usou o Cartão em {mes_cartao_selecionado}?")
            df_gastos_cartao = df_cartao_filtrado[df_cartao_filtrado["Tipo"] == "Despesa"]
            if not df_gastos_cartao.empty:
                df_cat_cartao = df_gastos_cartao.groupby("Categoria")["Valor"].sum().reset_index()
                fig_cartao = px.bar(
                    df_cat_cartao.sort_values(by="Valor", ascending=True), 
                    x="Valor", 
                    y="Categoria", 
                    orientation='h', 
                    title=f"Gastos no Cartão por Categoria ({mes_cartao_selecionado})", 
                    color_discrete_sequence=["#9b59b6"]
                )
                st.plotly_chart(fig_cartao, use_container_width=True)
            else:
                st.info(f"Nenhuma despesa registrada no cartão para o mês de {mes_cartao_selecionado}.")
            
            st.markdown(f"### 📋 Compras no Cartão em {mes_cartao_selecionado}")
            df_cartao_visualizar = df_cartao_filtrado.sort_values("Datetime", ascending=False).reset_index(drop=True)
            st.dataframe(df_cartao_visualizar[["Data", "Tipo", "Categoria", "Valor", "Observacoes"]], use_container_width=True)

# --- ABA 2: NOVO LANÇAMENTO ---
with tab_lançamentos:
    st.header("Cadastrar Transação")
    
    if not st.session_state.contas:
        st.warning("⚠️ Você precisa ter pelo menos uma Conta cadastrada para fazer lançamentos!")
    else:
        col_t, col_c = st.columns(2)
        tipo = col_t.selectbox("Tipo de Movimentação", ["Despesa", "Receita"])
        conta_selecionada = col_c.selectbox("Origem/Destino Financeiro (Conta)", st.session_state.contas)
        
        lista_categorias = st.session_state.categorias[tipo]
        
        with st.form("form_transacao", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            data_selecionada = col_f1.date_input("Data da transação", datetime.now(), format="DD/MM/YYYY")
            categoria = col_f2.selectbox("Categoria", lista_categorias)
            
            valor = col_f1.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f", value=None)
            
            opcoes_sub = ["(Nenhuma)"] + st.session_state.subcategorias
            subcategoria_sel = col_f2.selectbox("Subcategoria (Opcional)", opcoes_sub)
            observacao = st.text_input("Observações (Opcional, ex: Parcela 1/2, Loja X)").strip()
            
            botao_salvar = st.form_submit_button("Salvar Transação")
            
            if botao_salvar:
                if valor is not None and valor > 0:
                    data_formatada = data_selecionada.strftime('%d/%m/%Y')
                    sub_final = "" if subcategoria_sel == "(Nenhuma)" else subcategoria_sel
                    
                    nova_linha = pd.DataFrame([[data_formatada, tipo, categoria, sub_final, conta_selecionada, valor, observacao]], 
                                               columns=["Data", "Tipo", "Categoria", "Subcategoria", "Conta", "Valor", "Observacoes"])
                    
                    st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_linha], ignore_index=True)
                    salvar_transacoes(st.session_state.transacoes)
                    
                    st.success("Transação salva com sucesso!")
                    st.rerun()
                else:
                    st.error("Por favor, insira um valor válido maior que R$ 0,00.")

# --- ABA 3: ANÁLISE DOS DADOS ---
with tab_analise:
    subtab_extrato, subtab_categoria, subtab_saldo_mensal, subtab_despesa_contas, subtab_saldo_final_acumulado, subtab_relatorio_salarios, subtab_despesas_specificas = st.tabs([
        "📄 Extrato bancário", "🗂️ Resumo por Categoria", "💰 Saldo Mensal", "📉 Valores pagos (Fluxo Mensal)", "📊 Evolução de Saldo Final Coletivo", "💵 Relatório de Salários", "📉 Despesas Específicas"
    ])

    with subtab_extrato:
        st.subheader("Extrato Mensal por Conta")
        if df.empty:
            st.info("Nenhum dado disponível para gerar extrato.")
        else:
            df_extrato = df.copy()
            df_extrato["ID"] = df_extrato.index
            
            df_extrato["Datetime"] = pd.to_datetime(df_extrato["Data"], format="%d/%m/%Y", errors="coerce")
            df_extrato = df_extrato.dropna(subset=["Datetime"])
            df_extrato["AnoMes"] = df_extrato["Datetime"].dt.strftime("%Y/%m")
            df_extrato["MesExibicao"] = df_extrato["Datetime"].dt.strftime("%m/%Y")
            
            lista_meses = df_extrato.sort_values("AnoMes", ascending=False)["MesExibicao"].unique().tolist()
            
            col_f_mes, col_f_conta = st.columns(2)
            mes_selecionado = col_f_mes.selectbox("Selecione o Mês:", lista_meses, key="extrato_mes_sel")
            conta_selecionada = col_f_conta.selectbox("Selecione a Conta:", st.session_state.contas, key="extrato_conta_sel")
            
            df_filtrado = df_extrato[(df_extrato["MesExibicao"] == mes_selecionado) & (df_extrato["Conta"] == conta_selecionada)].sort_values("Datetime", ascending=True)
            
            if df_filtrado.empty:
                st.warning(f"Nenhuma movimentação encontrada para a conta '{conta_selecionada}' em {mes_selecionado}.")
            else:
                df_visualizar = df_filtrado[["ID", "Data", "Categoria", "Subcategoria", "Valor", "Observacoes"]].copy()
                df_visualizar["Valor"] = df_visualizar["Valor"].apply(lambda v: float(v) if v else 0.0)
                
                st.dataframe(
                    df_visualizar.fillna(""),
                    use_container_width=True,
                    column_config={
                        "ID": st.column_config.NumberColumn("ID", format="%d"),
                        "Valor": st.column_config.NumberColumn("Valor Líquido", format="R$ %,.2f")
                    },
                    hide_index=True
                )
                
                rec_periodo = df_filtrado[df_filtrado["Tipo"] == "Receita"]["Valor"].sum()
                des_periodo = df_filtrado[df_filtrado["Tipo"] == "Despesa"]["Valor"].sum()
                saldo_periodo = rec_periodo - des_periodo
                
                st.markdown(" ")
                if saldo_periodo >= 0:
                    st.success(f"**Resultado do Período ({mes_selecionado}):** Sobrou **R$ {formatar_br(saldo_periodo)}** nesta conta.")
                else:
                    st.error(f"**Resultado do Período ({mes_selecionado}):** Ficou negativo em **R$ {formatar_br(abs(saldo_periodo))}** nesta conta.")

    with subtab_categoria:
        st.subheader("Análise de Categorias por Período")
        if df.empty:
            st.info("Nenhum dado disponível para análise.")
        else:
            df_cat_analise = df.copy()
            df_cat_analise["Datetime"] = pd.to_datetime(df_cat_analise["Data"], format="%d/%m/%Y", errors="coerce")
            df_cat_analise = df_cat_analise.dropna(subset=["Datetime"])
            
            df_cat_analise = df_cat_analise.sort_values("Datetime", ascending=True)
            df_cat_analise["AnoMes"] = df_cat_analise["Datetime"].dt.strftime("%Y/%m")
            df_cat_analise["MesExibicao"] = df_cat_analise["Datetime"].dt.strftime("%m/%Y")
            
            todas_categorias_sistema = ordenar_lista_sem_acentos(df_cat_analise["Categoria"].unique().tolist())
            lista_meses_cronologica = df_cat_analise["MesExibicao"].unique().tolist()
            
            col_topo, _ = st.columns([1, 2])
            with col_topo:
                categoria_selecionada = st.selectbox("Escolha a Categoria para Análise:", todas_categorias_sistema, key="cat_unica_sel")
            
            st.markdown(f"### 📈 Evolução Mensal da Categoria: **{categoria_selecionada}**")
            df_historico_cat = df_cat_analise[df_cat_analise["Categoria"] == categoria_selecionada]
            
            if df_historico_cat.empty:
                st.warning("Sem dados históricos suficientes para traçar a evolução desta categoria.")
            else:
                df_evolucao = df_historico_cat.groupby(["AnoMes", "MesExibicao"])["Valor"].sum().reset_index().sort_values("AnoMes")
                tipo_categoria = df_historico_cat["Tipo"].iloc[0]
                cor_linha = ["#2ecc71"] if tipo_categoria == "Receita" else ["#e74c3c"]
                
                fig_linha = px.line(df_evolucao, x="MesExibicao", y="Valor", title=f"Histórico Completo de Ganhos/Gastos com '{categoria_selecionada}' ao longo do Tempo", markers=True, color_discrete_sequence=cor_linha)
                fig_linha.update_layout(xaxis_title="Mês/Ano", yaxis_title="Total por Mês (R$)")
                st.plotly_chart(fig_linha, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 🔍 Detalhamento Otimizado por Período")
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                mes_inicial = st.selectbox("1. Mês Inicial do Intervalo:", lista_meses_cronologica, index=0, key="cat_mes_inicial")
            with col_f2:
                mes_final = st.selectbox("2. Mês Final do Intervalo:", lista_meses_cronologica, index=len(lista_meses_cronologica)-1, key="cat_mes_final")
            
            idx_inicio = lista_meses_cronologica.index(mes_inicial)
            idx_fim = lista_meses_cronologica.index(mes_final)
            
            if idx_inicio > idx_fim:
                st.error("⚠️ O Mês Inicial não pode ser posterior ao Mês Final!")
            else:
                meses_no_intervalo = lista_meses_cronologica[idx_inicio:idx_fim + 1]
                df_filtrado_final = df_historico_cat[df_historico_cat["MesExibicao"].isin(meses_no_intervalo)]
                
                if df_filtrado_final.empty:
                    st.info(f"Não houve nenhuma movimentação em **{categoria_selecionada}** no período de {mes_inicial} a {mes_final}.")
                else:
                    total_da_categoria = df_filtrado_final["Valor"].sum()
                    st.metric(f"Total Acumulado no Período Selecionado ({categoria_selecionada})", f"R$ {formatar_br(total_da_categoria)}")
                    st.markdown(" ")
                    
                    col_tabela_mensal, col_tabela_sub, col_grafico_sub = st.columns([1, 1, 1.2])
                    
                    with col_tabela_mensal:
                        st.markdown("##### 📅 Lançamentos Mensais")
                        df_mensal_tabela = df_filtrado_final.groupby("MesExibicao")["Valor"].sum().reset_index()
                        df_mensal_tabela["Ordem"] = df_mensal_tabela["MesExibicao"].apply(lambda x: lista_meses_cronologica.index(x))
                        df_mensal_tabela = df_mensal_tabela.sort_values("Ordem").drop(columns=["Ordem"])
                        
                        st.dataframe(
                            df_mensal_tabela,
                            use_container_width=True,
                            column_config={
                                "MesExibicao": st.column_config.TextColumn("Mês / Ano"),
                                "Valor": st.column_config.NumberColumn("Total do Mês", format="R$ %,.2f")
                            },
                            hide_index=True
                        )
                    
                    df_sub_grupo = df_filtrado_final.groupby("Subcategoria")["Valor"].sum().reset_index()
                    df_sub_grupo["Subcategoria"] = df_sub_grupo["Subcategoria"].apply(lambda s: "(Sem subcategoria)" if s == "" else s)
                    df_sub_grupo["%"] = (df_sub_grupo["Valor"] / total_da_categoria) * 100
                    df_sub_ordenado = df_sub_grupo.sort_values("Valor", ascending=False)
                    
                    with col_tabela_sub:
                        st.markdown("##### 🗂️ Divisão por Subcategoria")
                        st.dataframe(
                            df_sub_ordenado,
                            use_container_width=True,
                            column_config={
                                "Valor": st.column_config.NumberColumn("Total", format="R$ %,.2f"),
                                "%": st.column_config.NumberColumn("%", format="%.1f %%")
                            },
                            hide_index=True
                        )
                    
                    with col_grafico_sub:
                        st.markdown("##### 📊 Distribuição Interna")
                        fig_sub = px.bar(
                            df_sub_grupo.sort_values("Valor", ascending=True), 
                            x="Valor", 
                            y="Subcategoria", 
                            orientation="h", 
                            text_auto=True, 
                            color_discrete_sequence=cor_linha
                        )
                        fig_sub.update_layout(
                            xaxis_title="Montante (R$)", 
                            yaxis_title=None, 
                            margin=dict(t=10, b=10, l=10, r=10),
                            height=280
                        )
                        st.plotly_chart(fig_sub, use_container_width=True)

    with subtab_saldo_mensal:
        st.subheader("💰 Evolução e Sobra de Caixa Mês a Mês (Contas Correntes)")
        
        if df.empty:
            st.info("Nenhuma transação cadastrada para gerar os relatórios mensais.")
        else:
            df_saldo = df[df["Conta"] != "Cartão créd. Nubank"].copy()
            df_saldo["Datetime"] = pd.to_datetime(df_saldo["Data"], format="%d/%m/%Y", errors="coerce")
            df_saldo = df_saldo.dropna(subset=["Datetime"])
            df_saldo["AnoMes"] = df_saldo["Datetime"].dt.to_period("M")
            
            df_rec = df_saldo[df_saldo["Tipo"] == "Receita"].groupby("AnoMes")["Valor"].sum().reset_index(name="Receitas")
            df_des = df_saldo[df_saldo["Tipo"] == "Despesa"].groupby("AnoMes")["Valor"].sum().reset_index(name="Despesas")
            
            df_consolidado = pd.merge(df_rec, df_des, on="AnoMes", how="outer").fillna(0.0)
            df_consolidado["Sobra (Saldo)"] = df_consolidado["Receitas"] - df_consolidado["Despesas"]
            df_consolidado = df_consolidado.sort_values("AnoMes")
            df_consolidado["Mês"] = df_consolidado["AnoMes"].dt.strftime("%m/%Y")
            
            col_tabela, col_grafico = st.columns([1, 1.3])
            with col_tabela:
                st.markdown("### 📋 Tabela Comparativa Líquida")
                st.dataframe(
                    df_consolidado[["Mês", "Receitas", "Despesas", "Sobra (Saldo)"]].iloc[::-1],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Receitas": st.column_config.NumberColumn("Total Receitas", format="R$ %,.2f"),
                        "Despesas": st.column_config.NumberColumn("Total Despesas", format="R$ %,.2f"),
                        "Sobra (Saldo)": st.column_config.NumberColumn("Sobra Líquida", format="R$ %,.2f")
                    }
                )
                
            with col_grafico:
                st.markdown("### 📈 Gráfico de Linha Chronológico")
                df_graf = df_consolidado.copy()
                df_graf["Período"] = df_graf["AnoMes"].astype(str)
                
                fig_linha = px.line(df_graf, x="Período", y="Sobra (Saldo)", markers=True, labels={"Sobra (Saldo)": "Saldo Líquido (R$)", "Período": "Linha do Tempo"}, title="Tendência de Sobra de Caixa (Excluindo Cartão Nubank)")
                fig_linha.update_traces(line_color="#2ecc71", line_width=3, marker=dict(size=8))
                st.plotly_chart(fig_linha, use_container_width=True)

    with subtab_despesa_contas:
        st.subheader("📉 Valores pagos (Mês x Categoria)")
        st.markdown("> **Nota:** Este relatório exibe apenas saídas em dinheiro (**Despesas**) originadas de contas correntes, poupanças ou espécie. Valores passados no **Cartão de Crédito Nubank** e lançamentos de **Transferência** estão totalmente excluídos desta visão.")
        
        df_fluxo_despesa = df[
            (df["Tipo"] == "Despesa") & 
            (df["Conta"] != "Cartão créd. Nubank") & 
            (~df["Categoria"].str.lower().str.contains("transferencia|transferência", na=False))
        ].copy()
        
        if df_fluxo_despesa.empty:
            st.info("Nenhum registro encontrado para as categorias especificadas nas transações.")
        else:
            df_fluxo_despesa["Datetime"] = pd.to_datetime(df_fluxo_despesa["Data"], format="%d/%m/%Y", errors="coerce")
            df_fluxo_despesa = df_fluxo_despesa.dropna(subset=["Datetime"])
            df_fluxo_despesa["AnoMes"] = df_fluxo_despesa["Datetime"].dt.to_period("M")
            df_fluxo_despesa["Mês"] = df_fluxo_despesa["AnoMes"].dt.strftime("%m/%Y")
            
            df_matriz_cats = df_fluxo_despesa.pivot_table(
                index="Mês",
                columns="Categoria",
                values="Valor",
                aggfunc="sum"
            ).fillna(0.0)
            
            df_matriz_cats["Ordenacao_dt"] = pd.to_datetime(df_matriz_cats.index, format="%m/%Y")
            df_matriz_cats = df_matriz_cats.sort_values(by="Ordenacao_dt", ascending=False).drop(columns=["Ordenacao_dt"])
            
            df_matriz_cats["Valor Total do Mês"] = df_matriz_cats.sum(axis=1)
            df_matriz_cats_exibir = df_matriz_cats.reset_index()
            
            colunas_cats = df_matriz_cats_exibir.columns.tolist()
            colunas_cats.remove("Valor Total do Mês")
            colunas_cats.insert(1, "Valor Total do Mês")
            df_matriz_cats_exibir = df_matriz_cats_exibir[colunas_cats]
            
            config_col_cats = {}
            for col_nome in df_matriz_cats_exibir.columns:
                if col_nome == "Mês":
                    config_col_cats[col_nome] = st.column_config.TextColumn("Mês", pinned=True)
                elif col_nome == "Valor Total do Mês":
                    config_col_cats[col_nome] = st.column_config.NumberColumn("📊 Total do Mês", format="R$ %,.2f", pinned=True)
                else:
                    config_col_cats[col_nome] = st.column_config.NumberColumn(col_nome, format="R$ %,.2f")
            
            st.markdown("### 📋 Visão Geral por Categoria Principal")
            
            selecao_tabela = st.dataframe(
                df_matriz_cats_exibir,
                use_container_width=True,
                hide_index=True,
                column_config=config_col_cats,
                on_select="rerun",           
                selection_mode="single-column" 
            )
            
            st.markdown("---")
            colunas_selecionadas = selecao_tabela.get("selection", {}).get("columns", [])
            
            if colunas_selecionadas:
                categoria_clicada = colunas_selecionadas[0]
                if categoria_clicada not in ["Mês", "Valor Total do Mês"]:
                    st.markdown(f"### 🔍 Detalhes das Subcategorias de: **{categoria_clicada}**")
                    
                    df_filtrado_sub = df_fluxo_despesa[df_fluxo_despesa["Categoria"] == categoria_clicada].copy()
                    df_filtrado_sub["Subcategoria_Limpa"] = df_filtrado_sub["Subcategoria"].apply(
                        lambda x: "Geral" if str(x).strip() == "" else str(x).strip()
                    )
                    
                    df_matriz_subs = df_filtrado_sub.pivot_table(
                        index="Mês",
                        columns="Subcategoria_Limpa",
                        values="Valor",
                        aggfunc="sum"
                    ).fillna(0.0)
                    
                    df_matriz_subs["Ordenacao_dt"] = pd.to_datetime(df_matriz_subs.index, format="%m/%Y")
                    df_matriz_subs = df_matriz_subs.sort_values(by="Ordenacao_dt", ascending=False).drop(columns=["Ordenacao_dt"])
                    df_matriz_subs_exibir = df_matriz_subs.reset_index()
                    
                    config_col_subs = {}
                    for col_nome in df_matriz_subs_exibir.columns:
                        if col_nome == "Mês":
                            config_col_subs[col_nome] = st.column_config.TextColumn("Mês", pinned=True)
                        else:
                            config_col_subs[col_nome] = st.column_config.NumberColumn(col_nome, format="R$ %,.2f")
                    
                    st.dataframe(
                        df_matriz_subs_exibir,
                        use_container_width=True,
                        hide_index=True,
                        column_config=config_col_subs
                    )
                else:
                    st.info("💡 Por favor, clique diretamente sobre os números ou o título de uma Categoria válida para expandir os dados.")
            else:
                st.info("💡 Clique em qualquer valor ou nome de uma Categoria na tabela acima para listar as subcategorias correspondentes aqui neste quadro.")
                
            st.markdown("---")
            st.markdown("### 📊 Gráfico de Barras Mensal por Categoria")
            df_graf_despesa = df_fluxo_despesa.groupby(["AnoMes", "Mês", "Categoria"])["Valor"].sum().reset_index()
            df_graf_despesa = df_graf_despesa.sort_values("AnoMes")
            
            fig_barras_despesa = px.bar(
                df_graf_despesa,
                x="Mês",
                y="Valor",
                color="Categoria",
                labels={"Valor": "Total Gasto (R$)", "Mês": "Período"},
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            
            df_totais_despesa = df_graf_despesa.groupby("Mês")["Valor"].sum().reset_index()
            for _, row in df_totais_despesa.iterrows():
                fig_barras_despesa.add_annotation(
                    x=row["Mês"],
                    y=row["Valor"],
                    text=f"R$ {formatar_br(row['Valor'])}",
                    showarrow=False,
                    yshift=8,
                    font=dict(size=12, color="white", weight="bold")
                )
            
            fig_barras_despesa.update_layout(
                xaxis_type='category',
                barmode='stack',
                yaxis=dict(tickformat="R$ ,.2f"),
                margin=dict(t=20, b=20)
            )
            st.plotly_chart(fig_barras_despesa, use_container_width=True)

    with subtab_saldo_final_acumulado:
        st.subheader("📊 Valor Final Acumulado das Contas (Mês a Mês)")
        st.markdown("> **Nota:** Este balanço consolida a soma de todos os lançamentos de todos as contas correntes/poupanças/investimentos, calculando o **Saldo Acumulado Final** ao término de cada período. O **Cartão de Crédito Nubank** está totalmente desconsiderado.")
        
        df_contas_reais = df[df["Conta"] != "Cartão créd. Nubank"].copy()
        
        if df_contas_reais.empty:
            st.info("Nenhum lançamento de conta corrente ativo para computar o saldo final acumulado.")
        else:
            df_contas_reais["Datetime"] = pd.to_datetime(df_contas_reais["Data"], format="%d/%m/%Y", errors="coerce")
            df_contas_reais = df_contas_reais.dropna(subset=["Datetime"])
            df_contas_reais["AnoMes"] = df_contas_reais["Datetime"].dt.to_period("M")
            
            rec_acum = df_contas_reais[df_contas_reais["Tipo"] == "Receita"].groupby("AnoMes")["Valor"].sum().reset_index(name="Entradas")
            des_acum = df_contas_reais[df_contas_reais["Tipo"] == "Despesa"].groupby("AnoMes")["Valor"].sum().reset_index(name="Saídas")
            
            df_balanco_acum = pd.merge(rec_acum, des_acum, on="AnoMes", how="outer").fillna(0.0)
            df_balanco_acum = df_balanco_acum.sort_values("AnoMes")
            
            df_balanco_acum["Resultado do Mês"] = df_balanco_acum["Entradas"] - df_balanco_acum["Saídas"]
            df_balanco_acum["Valor Final (Saldo Acumulado)"] = df_balanco_acum["Resultado do Mês"].cumsum()
            
            df_balanco_acum["Mês"] = df_balanco_acum["AnoMes"].dt.strftime("%m/%Y")
            df_balanco_acum["Eixo_X"] = df_balanco_acum["AnoMes"].astype(str)
            
            col_tab_acum, col_graf_acum = st.columns([1, 1.3])
            
            with col_tab_acum:
                st.markdown("### 📋 Tabela de Evolução do Patrimônio")
                st.dataframe(
                    df_balanco_acum[["Mês", "Entradas", "Saídas", "Resultado do Mês", "Valor Final (Saldo Acumulado)"]].iloc[::-1],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Entradas": st.column_config.NumberColumn("Total Entradas", format="R$ %,.2f"),
                        "Saídas": st.column_config.NumberColumn("Total Saídas", format="R$ %,.2f"),
                        "Resultado do Mês": st.column_config.NumberColumn("Sobra Líquida", format="R$ %,.2f"),
                        "Valor Final (Saldo Acumulado)": st.column_config.NumberColumn("Valor Final Guardado", format="R$ %,.2f")
                    }
                )
                
            with col_graf_acum:
                st.markdown("### 📈 Curva de Crescimento do Dinheiro em Conta")
                fig_curva_acum = px.line(
                    df_balanco_acum, 
                    x="Eixo_X", 
                    y="Valor Final (Saldo Acumulado)", 
                    markers=True, 
                    labels={"Valor Final (Saldo Acumulado)": "Montante em Conta (R$)", "Eixo_X": "Período"},
                    title="Patrimônio Total Líquido Disponível ao Fim de Cada Mês"
                )
                fig_curva_acum.update_traces(line_color="#00bcd4", line_width=4, marker=dict(size=10, color="#00838f"))
                fig_curva_acum.update_layout(xaxis_type='category', yaxis=dict(tickformat="R$ ,.2f"))
                st.plotly_chart(fig_curva_acum, use_container_width=True)

    with subtab_relatorio_salarios:
        st.subheader("📊 Relatório Detalhado de Salários Mês a Mês")
        df_salarios = df[df["Categoria"].str.lower() == "salário"].copy()
        
        if df_salarios.empty:
            st.info("Nenhum lançamento categorizado como 'Salário' encontrado no histórico.")
        else:
            df_salarios["Datetime"] = pd.to_datetime(df_salarios["Data"], format="%d/%m/%Y", errors="coerce")
            df_salarios = df_salarios.dropna(subset=["Datetime"])
            df_salarios["AnoMes"] = df_salarios["Datetime"].dt.to_period("M")
            df_salarios["Subcategoria"] = df_salarios["Subcategoria"].apply(lambda s: "(Fixo / Principal)" if s == "" else s)
            
            df_pivot_salario = df_salarios.pivot_table(
                index="AnoMes", 
                columns="Subcategoria", 
                values="Valor", 
                aggfunc="sum"
            ).fillna(0.0)
            
            df_pivot_salario["Total Recebido"] = df_pivot_salario.sum(axis=1)
            df_pivot_salario = df_pivot_salario.sort_index(ascending=False).reset_index()
            df_pivot_salario["Mês"] = df_pivot_salario["AnoMes"].dt.strftime("%m/%Y")
            
            colunas_ordenadas = ["Mês"] + [col for col in df_pivot_salario.columns if col not in ["AnoMes", "Mês"]]
            df_pivot_salario = df_pivot_salario[colunas_ordenadas]
            
            st.markdown("### 📋 Distribuição Cronológica por Subcategoria")
            config_colunas = {}
            for col_nome in df_pivot_salario.columns:
                if col_nome == "Mês":
                    config_colunas[col_nome] = st.column_config.TextColumn("Mês", pinned=True)
                else:
                    config_colunas[col_nome] = st.column_config.NumberColumn(col_nome, format="R$ %,.2f")
                        
            st.dataframe(df_pivot_salario, use_container_width=True, hide_index=True, column_config=config_colunas)

    with subtab_despesas_specificas:
        st.subheader("📋 Relatório Dinâmico de Despesas Selecionadas")
        st.markdown("> **Dica de Navegação:** Clique no cabeçalho ou em qualquer célula de uma categoria na tabela abaixo para abrir o detalhamento de suas subcategorias no quadro inferior.")
        
        cats_solicitadas = [
            "financiamento", "outros pagamentos", "saúde", "imposto", "condomínio", 
            "supermercado", "moradia(outros)", "carro", "alimentação", "internet", 
            "educação", "luz", "água", "moradia", "outros"
        ]
        
        df_essenciais = df[
            (df["Tipo"] == "Despesa") & 
            (df["Categoria"].str.lower().str.strip().isin(cats_solicitadas))
        ].copy()
        
        if df_essenciais.empty:
            st.info("Nenhum registro encontrado para as categorias especificadas nas transações.")
        else:
            df_essenciais["Datetime"] = pd.to_datetime(df_essenciais["Data"], format="%d/%m/%Y", errors="coerce")
            df_essenciais = df_essenciais.dropna(subset=["Datetime"])
            df_essenciais["AnoMes"] = df_essenciais["Datetime"].dt.to_period("M")
            df_essenciais["Mês"] = df_essenciais["AnoMes"].dt.strftime("%m/%Y")
            
            df_matriz_cats = df_essenciais.pivot_table(
                index="Mês",
                columns="Categoria",
                values="Valor",
                aggfunc="sum"
            ).fillna(0.0)
            
            df_matriz_cats["Ordenacao_dt"] = pd.to_datetime(df_matriz_cats.index, format="%m/%Y")
            df_matriz_cats = df_matriz_cats.sort_values(by="Ordenacao_dt", ascending=False).drop(columns=["Ordenacao_dt"])
            
            df_matriz_cats["Valor Total do Mês"] = df_matriz_cats.sum(axis=1)
            df_matriz_cats_exibir = df_matriz_cats.reset_index()
            
            colunas_cats = df_matriz_cats_exibir.columns.tolist()
            colunas_cats.remove("Valor Total do Mês")
            colunas_cats.insert(1, "Valor Total do Mês")
            df_matriz_cats_exibir = df_matriz_cats_exibir[colunas_cats]
            
            config_col_cats = {}
            for col_nome in df_matriz_cats_exibir.columns:
                if col_nome == "Mês":
                    config_col_cats[col_nome] = st.column_config.TextColumn("Mês", pinned=True)
                elif col_nome == "Valor Total do Mês":
                    config_col_cats[col_nome] = st.column_config.NumberColumn("📊 Total do Mês", format="R$ %,.2f", pinned=True)
                else:
                    config_col_cats[col_nome] = st.column_config.NumberColumn(col_nome, format="R$ %,.2f")
            
            st.markdown("### 📋 Visão Geral por Categoria Principal")
            selecao_tabela = st.dataframe(
                df_matriz_cats_exibir,
                use_container_width=True,
                hide_index=True,
                column_config=config_col_cats,
                on_select="rerun",           
                selection_mode="single-column" 
            )
            
            st.markdown("---")
            colunas_selecionadas = selecao_tabela.get("selection", {}).get("columns", [])
            
            if colunas_selecionadas:
                categoria_clicada = colunas_selecionadas[0]
                if categoria_clicada not in ["Mês", "Valor Total do Mês"]:
                    st.markdown(f"### 🔍 Detalhes das Subcategorias de: **{categoria_clicada}**")
                    
                    df_filtrado_sub = df_essenciais[df_essenciais["Categoria"] == categoria_clicada].copy()
                    df_filtrado_sub["Subcategoria_Limpa"] = df_filtrado_sub["Subcategoria"].apply(
                        lambda x: "Geral" if str(x).strip() == "" else str(x).strip()
                    )
                    
                    df_matriz_subs = df_filtrado_sub.pivot_table(
                        index="Mês",
                        columns="Subcategoria_Limpa",
                        values="Valor",
                        aggfunc="sum"
                    ).fillna(0.0)
                    
                    df_matriz_subs["Ordenacao_dt"] = pd.to_datetime(df_matriz_subs.index, format="%m/%Y")
                    df_matriz_subs = df_matriz_subs.sort_values(by="Ordenacao_dt", ascending=False).drop(columns=["Ordenacao_dt"])
                    df_matriz_subs_exibir = df_matriz_subs.reset_index()
                    
                    config_col_subs = {}
                    for col_nome in df_matriz_subs_exibir.columns:
                        if col_nome == "Mês":
                            config_col_subs[col_nome] = st.column_config.TextColumn("Mês", pinned=True)
                        else:
                            config_col_subs[col_nome] = st.column_config.NumberColumn(col_nome, format="R$ %,.2f")
                    
                    st.dataframe(df_matriz_subs_exibir, use_container_width=True, hide_index=True, column_config=config_col_subs)
                else:
                    st.info("💡 Por favor, clique diretamente sobre os números ou o título de uma Categoria válida para expandir os dados.")
            else:
                st.info("💡 Clique em qualquer valor ou nome de uma Categoria na tabela acima para listar as subcategorias correspondentes aqui neste quadro.")
                
            st.markdown("---")
            st.markdown("### 📊 Gráfico de Barras Mensal por Categoria")
            df_graf_essenciais = df_essenciais.groupby(["AnoMes", "Mês", "Categoria"])["Valor"].sum().reset_index()
            df_graf_essenciais = df_graf_essenciais.sort_values("AnoMes")
            
            fig_barras_essenciais = px.bar(
                df_graf_essenciais,
                x="Mês",
                y="Valor",
                color="Categoria",
                labels={"Valor": "Total Gasto (R$)", "Mês": "Período"},
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            
            df_totais_essenciais = df_graf_essenciais.groupby("Mês")["Valor"].sum().reset_index()
            for _, row in df_totais_essenciais.iterrows():
                fig_barras_essenciais.add_annotation(
                    x=row["Mês"],
                    y=row["Valor"],
                    text=f"R$ {formatar_br(row['Valor'])}",
                    showarrow=False,
                    yshift=8,
                    font=dict(size=12, color="white", weight="bold")
                )
            
            fig_barras_essenciais.update_layout(xaxis_type='category', barmode='stack', yaxis=dict(tickformat="R$ ,.2f"), margin=dict(t=20, b=20))
            st.plotly_chart(fig_barras_essenciais, use_container_width=True)

# --- ABA 4: HISTÓRICO DE LANÇAMENTOS ---
with tab_historico:
    st.header("📋 Histórico de Lançamentos")
    df_hist = st.session_state.transacoes.copy()
    
    if df_hist.empty:
        st.info("Nenhum lançamento encontrado.")
    else:
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            filtro_conta = st.selectbox("Filtrar por Conta", ["Todos"] + sorted(df_hist["Conta"].unique().tolist()))
        with col_f2:
            filtro_tipo = st.selectbox("Filtrar por Tipo", ["Todos", "Receita", "Despesa"])
        with col_f3:
            filtro_cat = st.selectbox("Filtrar por Categoria", ["Todos"] + sorted(df_hist["Categoria"].unique().tolist()))
        with col_f4:
            subcategorias_existentes = [s for s in df_hist["Subcategoria"].dropna().unique().tolist() if str(s).strip() != ""]
            filtro_sub = st.selectbox("Filtrar por Subcategoria", ["Todos"] + sorted(subcategorias_existentes))
            
        if filtro_conta != "Todos":
            df_hist = df_hist[df_hist["Conta"] == filtro_conta]
        if filtro_tipo != "Todos":
            df_hist = df_hist[df_hist["Tipo"] == filtro_tipo]
        if filtro_cat != "Todos":
            df_hist = df_hist[df_hist["Categoria"] == filtro_cat]
        if filtro_sub != "Todos":
            df_hist = df_hist[df_hist["Subcategoria"] == filtro_sub]
            
        df_hist["ID"] = df_hist.index
        df_visualizar = df_hist.iloc[::-1].reset_index(drop=True)
        
        st.markdown("### Selecione um lançamento para editar ou excluir:")
        
        opcoes_edicao = []
        for idx, row in df_visualizar.iterrows():
            sub_txt = f" [{row['Subcategoria']}]" if row['Subcategoria'] else ""
            opcoes_edicao.append(f"ID: {row['ID']} | {row['Data']} - {row['Tipo']} - {row['Categoria']}{sub_txt} - R$ {row['Valor']} ({row['Conta']})")
            
        selecionado = st.selectbox("Escolha o lançamento que deseja alterar ou apagar:", ["-- Selecione --"] + opcoes_edicao)
        
        if selecionado != "-- Selecione --":
            id_original = int(selecionado.split(" | ")[0].split(": ")[1])
            linha_original = st.session_state.transacoes.loc[id_original]
            
            st.markdown("---")
            st.subheader(f"✏️ Alterar / Excluir Lançamento (ID {id_original})")
            
            with st.form("form_edicao"):
                col1, col2, col3 = st.columns(3)
                try:
                    data_atual_dt = datetime.strptime(str(linha_original["Data"]), "%d/%m/%Y")
                except:
                    data_atual_dt = datetime.today()
                nova_data = st.date_input("Data", data_atual_dt)
                novo_tipo = st.selectbox("Tipo", ["Receita", "Despesa"], index=0 if linha_original["Tipo"] == "Receita" else 1)
                novo_valor = st.number_input("Valor (R$)", min_value=0.0, value=float(linha_original["Valor"]), step=0.01)
                    
                col4, col5 = st.columns(2)
                with col4:
                    cats_disponiveis = st.session_state.categorias.get(novo_tipo, ["Outros"])
                    if linha_original["Categoria"] not in cats_disponiveis:
                        cats_disponiveis = [linha_original["Categoria"]] + cats_disponiveis
                    nova_cat = st.selectbox("Categoria", cats_disponiveis, index=cats_disponiveis.index(linha_original["Categoria"]))
                    
                    opcoes_sub = ["(Nenhuma)"] + st.session_state.subcategorias
                    sub_atual = linha_original["Subcategoria"] if linha_original["Subcategoria"] in st.session_state.subcategorias else "(Nenhuma)"
                    nova_sub_sel = st.selectbox("Subcategoria (Opcional)", opcoes_sub, index=opcoes_sub.index(sub_atual))
                    
                with col5:
                    contas_disp = st.session_state.contas if st.session_state.contas else ["CEF", "Conta Nubank", "Itaú", "dinheiro em espécie"]
                    if linha_original["Conta"] not in contas_disp:
                        contas_disp = [linha_original["Conta"]] + contas_disp
                    nova_conta = st.selectbox("Conta", contas_disp, index=contas_disp.index(linha_original["Conta"]))
                    
                nova_obs = st.text_input("Observações", value=str(linha_original["Observacoes"]))
                
                col_btn_salvar, col_btn_deletar = st.columns([1, 1])
                salvar_alteracoes = col_btn_salvar.form_submit_button("💾 Salvar Alterações")
                deletar_lancamento = col_btn_deletar.form_submit_button("🗑️ Excluir Lançamento")
                
                if salvar_alteracoes:
                    st.session_state.transacoes.at[id_original, "Data"] = nova_data.strftime("%d/%m/%Y")
                    st.session_state.transacoes.at[id_original, "Tipo"] = novo_tipo
                    st.session_state.transacoes.at[id_original, "Categoria"] = nova_cat
                    st.session_state.transacoes.at[id_original, "Subcategoria"] = "" if nova_sub_sel == "(Nenhuma)" else nova_sub_sel
                    st.session_state.transacoes.at[id_original, "Conta"] = nova_conta
                    st.session_state.transacoes.at[id_original, "Valor"] = novo_valor
                    st.session_state.transacoes.at[id_original, "Observacoes"] = nova_obs
                    
                    salvar_transacoes(st.session_state.transacoes)
                    st.success("Lançamento updated!")
                    st.rerun()
                    
                if deletar_lancamento:
                    st.session_state.transacoes = st.session_state.transacoes.drop(id_original).reset_index(drop=True)
                    salvar_transacoes(st.session_state.transacoes)
                    st.success("Lançamento deleted!")
                    st.rerun()
                    
        st.markdown("---")
        st.markdown("### 📋 Visualização Geral dos Dados (Filtrados)")
        colunas_exibicao = ["ID", "Data", "Tipo", "Categoria", "Subcategoria", "Conta", "Valor", "Observacoes"]
        st.dataframe(df_visualizar[colunas_exibicao], use_container_width=True, hide_index=True, column_config={"ID": st.column_config.NumberColumn("ID", format="%d")})

# --- ABA 5: GERENCIAR CATEGORIAS ---
with tab_categorias:
    st.header("🗂️ Gerenciar Minhas Categorias")
    col_lista_rec, col_lista_des, col_add = st.columns([1.2, 1.2, 1.5])
    
    df_rec_editor = pd.DataFrame({"Receitas": st.session_state.categorias["Receita"]})
    df_des_editor = pd.DataFrame({"Despesas": st.session_state.categorias["Despesa"]})
    
    with col_lista_rec:
        st.subheader("🟢 Receitas")
        editado_rec = st.data_editor(df_rec_editor, use_container_width=True, num_rows="dynamic", hide_index=True, key="ed_cat_rec")
        novas_rec = editado_rec["Receitas"].dropna().tolist()
        if ordenar_lista_sem_acentos(novas_rec) != ordenar_lista_sem_acentos(st.session_state.categorias["Receita"]):
            st.session_state.categorias["Receita"] = ordenar_lista_sem_acentos([r.strip() for r in novas_rec if r.strip() != ""])
            salvar_categorias(st.session_state.categorias)
            st.rerun()
            
    with col_lista_des:
        st.subheader("🔴 Despesas")
        editado_des = st.data_editor(df_des_editor, use_container_width=True, num_rows="dynamic", hide_index=True, key="ed_cat_des")
        novas_des = editado_des["Despesas"].dropna().tolist()
        if ordenar_lista_sem_acentos(novas_des) != ordenar_lista_sem_acentos(st.session_state.categorias["Despesa"]):
            st.session_state.categorias["Despesa"] = ordenar_lista_sem_acentos([d.strip() for d in novas_des if d.strip() != ""])
            salvar_categorias(st.session_state.categorias)
            st.rerun()
        
    with col_add:
        st.subheader("✨ Adicionar Nova Categoria")
        with st.form("form_nova_categoria", clear_on_submit=True):
            tipo_nova_cat = st.radio("Tipo da categoria:", ["Receita", "Despesa"])
            nome_nova_cat = st.text_input("Nome da categoria:").strip()
            botao_salvar_cat = st.form_submit_button("Salvar Categoria")
            
            if botao_salvar_cat and nome_nova_cat:
                if nome_nova_cat not in st.session_state.categorias[tipo_nova_cat]:
                    st.session_state.categorias[tipo_nova_cat].append(nome_nova_cat)
                    salvar_categorias(st.session_state.categorias)
                    st.rerun()

# --- ABA 6: GERENCIAR SUBCATEGORIAS ---
with tab_subcategorias:
    st.header("📂 Gerenciar Minhas Subcategorias Globais")
    col_sub_l, col_sub_a = st.columns([2, 1.5])
    df_sub_editor = pd.DataFrame({"Subcategorias Globais": st.session_state.subcategorias})
    
    with col_sub_l:
        st.subheader("Subcategorias Ativas")
        editado_sub = st.data_editor(df_sub_editor, use_container_width=True, num_rows="dynamic", hide_index=True, key="ed_sub_global")
        novas_subs = editado_sub["Subcategorias Globais"].dropna().tolist()
        if ordenar_lista_sem_acentos(novas_subs) != ordenar_lista_sem_acentos(st.session_state.subcategorias):
            st.session_state.subcategorias = ordenar_lista_sem_acentos([s.strip() for s in novas_subs if s.strip() != ""])
            salvar_subcategorias(st.session_state.subcategorias)
            st.rerun()

    with col_sub_a:
        st.subheader("✨ Adicionar Subcategoria Global")
        with st.form("form_nova_subcategoria", clear_on_submit=True):
            nome_nova_sub = st.text_input("Nome da Subcategoria (Ex: Supermercado, Farmácia):").strip()
            botao_salvar_sub = st.form_submit_button("Salvar Subcategoria")
            
            if botao_salvar_sub and nome_nova_sub:
                if nome_nova_sub not in st.session_state.subcategorias:
                    st.session_state.subcategorias.append(nome_nova_sub)
                    salvar_subcategorias(st.session_state.subcategorias)
                    st.rerun()

# --- ABA 7: GERENCIAR CONTAS ---
with tab_contas:
    st.header("🏦 Gerenciar Meus Locais de Dinheiro (Contas)")
    col_l_contas, col_a_contas = st.columns(2)
    
    with col_l_contas:
        st.subheader("Contas Ativas")
        for conta in st.session_state.contas[:]:
            col_txt, col_btn = st.columns([4, 1])
            col_txt.write(f"• {conta}")
            if col_btn.button("🗑️", key=f"del_conta_{conta}"):
                st.session_state.contas.remove(conta)
                salvar_contas(st.session_state.contas)
                st.rerun()
                
    with col_a_contas:
        st.subheader("Adicionar Nova Conta / Local")
        nome_nova_conta = st.text_input("Nome do banco, investimento ou carteira:").strip()
        
        if st.button("Salvar Nova Conta"):
            if nome_nova_conta and nome_nova_conta not in st.session_state.contas:
                st.session_state.contas.append(nome_nova_conta)
                salvar_contas(st.session_state.contas)
                st.rerun()

# --- ABA 8: PREVISÃO DE GASTOS ---
with tab_previsao:
    st.header("🔮 Previsão de Gastos Futuros")
    st.markdown("> **Como funciona:** Digite os itens desejados na planilha interativa abaixo. Todos os campos são editáveis em tempo real. O sistema calcula o somatório total de forma dinâmica e salva os dados automaticamente.")
    
    df_prev_atual = st.session_state.previsoes.copy()
    soma_previsoes = df_prev_atual["Valor"].sum()
    
    col_metric_prev, _ = st.columns([1, 2])
    with col_metric_prev:
        st.metric(label="Total Estimado (Somatório)", value=f"R$ {formatar_br(soma_previsoes)}")
        
    st.markdown("---")
    
    dados_editados_prev = st.data_editor(
        df_prev_atual,
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        key="editor_previsoes_gastos",
        column_config={
            "Descrição": st.column_config.TextColumn("Descrição do Gasto Estimado", width="large", required=True),
            "Valor": st.column_config.NumberColumn("Valor Previsto (R$)", format="R$ %,.2f", min_value=0.0, step=10.0, required=False),
            "Débito em Conta?": st.column_config.CheckboxColumn("Débito em Conta?", default=False),
            "Valor Pago?": st.column_config.CheckboxColumn("Valor Pago?", default=False)
        }
    )
    
    if not dados_editados_prev.equals(df_prev_atual):
        df_limpo_prev = dados_editados_prev.dropna(subset=["Descrição"])
        df_limpo_prev = df_limpo_prev[df_limpo_prev["Descrição"].str.strip() != ""]
        
        df_limpo_prev["Valor"] = df_limpo_prev["Valor"].fillna(0.0)
        df_limpo_prev["Débito em Conta?"] = df_limpo_prev["Débito em Conta?"].fillna(False).astype(bool)
        df_limpo_prev["Valor Pago?"] = df_limpo_prev["Valor Pago?"].fillna(False).astype(bool)
        
        st.session_state.previsoes = df_limpo_prev.reset_index(drop=True)
        salvar_previsoes(st.session_state.previsoes)
        st.rerun()
