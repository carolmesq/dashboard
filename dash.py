import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

st.set_page_config(layout="wide")

# Initialize connection to the PostgreSQL database
@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=st.secrets["host"],
        port=st.secrets["port"],
        database=st.secrets["database"],
        user=st.secrets["user"],
        password=st.secrets["password"]
    )

conn = init_connection()

# Function to run a SQL query with caching
@st.cache_data(ttl=600)
def run_query(query):
    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()

rows = run_query("SELECT uf, nome_munic, pop_2022 FROM t_analises.dados_gerais")
df = pd.DataFrame(rows, columns=['uf', 'nome_munic','pop_2022'])

#df = pd.read_excel("C:/Users/Carol/Documents/GitHub/Carol/dados_gerais.xls")

uf = st.sidebar.selectbox("UF", df["uf"].unique())

df_filtered = df[df["uf"] == uf]

municipio = st.sidebar.selectbox("Município", df_filtered["nome_munic"].unique())

df_fil_mun = df_filtered[df_filtered["nome_munic"] == municipio]

col1, col2 = st.columns(2)

# Faz uma linha horizontal
st.divider()

col3, col4, col5 = st.columns(3)

# Grafico linha população 2022
fig_pop = px.bar(df_fil_mun, x="nome_munic", y="pop_2022", title = "ESTADOS")
col1.plotly_chart(fig_pop, use_container_width=True)



# frota
fig_frota = px.bar(df_fil_mun, x="nome_munic", y="pop_2022", title = "FROTA", orientation="h")
col2.plotly_chart(fig_frota, use_container_width=True)


city_total = df_fil_mun.groupby("FX_POP")[["POP_2022"]].sum().reset_index()
fig_city = px.bar(city_total, x="FX_POP", y="POP_2022", color="POP_2022", title = "GRUPO")
col3.plotly_chart(fig_city, use_container_width=True)

frota_total = df_filtered.groupby("AUTO_2010")[["MOTO_2010"]].sum().reset_index()
fig_frotapie = px.pie(frota_total, values="AUTO_2010", names="MOTO_2010", title = "Frota")
col4.plotly_chart(fig_frotapie, use_container_width=True)

city_total = df_fil_mun.groupby("NOME_MUNIC")[["IBEU"]].sum().reset_index()
fig_ibeu = px.bar(city_total, x="NOME_MUNIC", y="IBEU", title = "IBEU")
col5.plotly_chart(fig_ibeu, use_container_width=True)