import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="COVID-19 Dashboard", layout="wide")
st.title("Painel de Monitoramento COVID-19")

# 1. DEFINIÇÃO DA FUNÇÃO (Apenas ensina o Python como buscar os dados)


@st.cache_data(ttl=600)
def load_data():
    conn = st.connection("snowflake")
    df_interno = conn.query("SELECT * FROM COVID_DB.PUBLIC.COVID_DATA", ttl=600)
    df_interno['DATE'] = pd.to_datetime(df_interno['DATE'])
    return df_interno


# 2. EXECUÇÃO DA FUNÇÃO (Aqui é onde a variável 'df' realmente nasce no script)
try:
    df = load_data()
except Exception as e:
    st.error(f"Erro ao conectar com Snowflake: {e}")
    st.stop()  # Para o app aqui se der erro na senha ou no banco

# 3. USO DA VARIÁVEL (Agora o df existe e o Streamlit pode ler a coluna LOCATION)
st.sidebar.header("Filtros")
paises_disponiveis = df['LOCATION'].unique()
pais_selecionado = st.sidebar.multiselect("Selecione os Países", paises_disponiveis, default=paises_disponiveis)

# Aplicação do filtro
df_filtrado = df[df['LOCATION'].isin(pais_selecionado)]

# Paleta de cores otimizada para legibilidade
cores = px.colors.qualitative.Safe

# Abas principais
tab1, tab2 = st.tabs(["Dashboard", "Dados Brutos"])

with tab1:
    # --- KPIs ---
    st.subheader("Métricas Gerais (Último Registro)")
    df_recente = df_filtrado.sort_values('DATE').groupby('LOCATION').tail(1)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Casos", f"{df_recente['TOTAL_CASES'].sum():,.0f}")
    col2.metric("Total de Óbitos", f"{df_recente['TOTAL_DEATHS'].sum():,.0f}")

    taxa_vacinacao = (df_recente['PEOPLE_VACCINATED'].sum() / df_recente['POPULATION'].sum()) * 100
    col3.metric("População Vacinada (Média)", f"{taxa_vacinacao:.1f}%")

    st.markdown("---")

    # --- Visualizações ---
    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        # 1. Linha — Evolução de casos novos por país
        fig_linha = px.line(df_filtrado, x='DATE', y='NEW_CASES', color='LOCATION',
                            title='Evolução de Novos Casos', color_discrete_sequence=cores)
        st.plotly_chart(fig_linha, use_container_width=True)

        # 3. Pizza — Proporção de vacinados (1 dose) vs Não vacinados (Agregado dos selecionados)
        vacinados = df_recente['PEOPLE_VACCINATED'].sum()
        populacao_total = df_recente['POPULATION'].sum()
        nao_vacinados = populacao_total - vacinados

        df_pizza = pd.DataFrame({
            'Status': ['Vacinados (1 dose)', 'Não Vacinados'],
            'Quantidade': [vacinados, nao_vacinados]
        })
        fig_pizza = px.pie(df_pizza, names='Status', values='Quantidade',
                           title='Proporção de Vacinados (Países Selecionados)', color_discrete_sequence=cores)
        st.plotly_chart(fig_pizza, use_container_width=True)

    with col_graf2:
        # 2. Barras — Total de óbitos por país
        fig_bar = px.bar(df_recente, x='LOCATION', y='TOTAL_DEATHS', color='LOCATION',
                         title='Total de Óbitos por País', color_discrete_sequence=cores)
        st.plotly_chart(fig_bar, use_container_width=True)

        # TRATAMENTO DE ERRO: Substitui valores vazios (NaN) por 0
        # para que o Plotly consiga calcular o tamanho da bolha
        df_recente.loc[:, 'TOTAL_DEATHS'] = df_recente['TOTAL_DEATHS'].fillna(0)

        # 4. Dispersão — População × Total de casos
        fig_disp = px.scatter(df_recente, x='POPULATION', y='TOTAL_CASES', color='LOCATION',
                              size='TOTAL_DEATHS', title='População vs Total de Casos (Tamanho: Óbitos)',
                              color_discrete_sequence=cores)
        st.plotly_chart(fig_disp, use_container_width=True)

with tab2:
    st.subheader("Exportação de Dados")
    st.dataframe(df_filtrado)
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Baixar Dados como CSV", data=csv, file_name='dados_covid.csv', mime='text/csv')
