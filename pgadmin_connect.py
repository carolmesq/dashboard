import streamlit as st
import pandas as pd
import psycopg2

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

# Run the query to fetch data from the PostgreSQL database
rows = run_query("SELECT nome_munic, pop_2010::bigint, pop_2022 FROM t_analises.dados_gerais LIMIT 20")

# Convert the results into a DataFrame and set the column names
data = pd.DataFrame(rows, columns=['nome_munic', 'pop_2010', 'pop_2022'])

# Display the data in a table format
st.table(data)
