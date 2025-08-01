import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
from PIL import Image
import os
import base64
from io import BytesIO

# Configuração da página - DEVE SER O PRIMEIRO COMANDO
st.set_page_config(
    layout="wide",
    page_title="Dados Municipais do Brasil",
    page_icon="🌎"
)


# Cores personalizadas
CORES = ["#2C95C1", "#EC3E95", "#8CC869", "#FEBE10", "#A8459A"]


# Função para converter imagem para base64
def image_to_base64(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


# Função para adicionar background
def add_bg_image():
    try:
        img_path = os.path.join('images', 'logo.png')
        img = Image.open(img_path)

        # Reduzindo o tamanho pela metade diretamente na imagem
        width, height = img.size
        img = img.resize((width // 2, height // 2))

        st.markdown(
            f"""
               <style>
                   .logo-container {{
                       position: fixed;
                       top: 60px;
                       right: 60px;
                       z-index: 100;
                   }}
                   .logo-img {{
                       width: {width // 1.7}px;
                       height: {height // 1.7}px;
                       opacity: 0.5;
                   }}
               </style>
               <div class="logo-container">
                   <img class="logo-img" src="data:image/png;base64,{image_to_base64(img)}">
               </div>
               """,
            unsafe_allow_html=True
        )
    except Exception as e:
        st.warning(f"Logo não carregada: {str(e)}")


# Adiciona o background (após o set_page_config)
add_bg_image()


# Inicialização da conexão com o PostgreSQL
@st.cache_resource
def init_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["host"],
            port=st.secrets["port"],
            database=st.secrets["database"],
            user=st.secrets["user"],
            password=st.secrets["password"]
        )
        return conn
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None


conn = init_connection()


# Função para executar consultas SQL
@st.cache_data(ttl=600)
def run_query(query):
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            return pd.DataFrame(data, columns=columns)
    except Exception as e:
        st.error(f"Erro ao executar consulta: {e}")
        return pd.DataFrame()


def main():
    # Carregar dados
    df = run_query("""
        SELECT cod_mun, uf, nome_mun, pop_2010, pop_2015, pop_2016, pop_2022, 
               auto_2023, moto_2023, outr_veic_2023, faixa_pop_2022, tx_mortalidade_100mil_hab, ibeu 
        FROM t_analises.dados_gerais
    """)

    if df.empty:
        st.error("Não foi possível carregar os dados. Verifique a conexão com o banco de dados.")
        return

    # Inicializa variáveis com valores padrão
    municipio = "Selecione um município"
    uf = "Selecione um estado"
    df_fil_mun = pd.DataFrame()

    # Sidebar - Filtros
    with st.sidebar:
        st.title("Filtros")

        # Opção 1: Busca por código IBGE (independente)
        cod_mun = st.text_input("Digite o Código IBGE:", help="Digite o código completo do município")

        if cod_mun:
            try:
                df_fil_mun = df[df['cod_mun'].astype(str).str.strip() == cod_mun.strip()]
                if not df_fil_mun.empty:
                    municipio = df_fil_mun.iloc[0]['nome_mun']
                    uf = df_fil_mun.iloc[0]['uf']
                else:
                    st.warning("Nenhum município encontrado com este código!")
            except Exception as e:
                st.error(f"Erro ao filtrar por código: {e}")

        # Opção 2: Filtros tradicionais (se não digitou código ou não encontrou)
        if not cod_mun or df_fil_mun.empty:
            uf = st.selectbox("Selecione o Estado (UF)", sorted(df["uf"].unique()))
            df_filtered = df[df["uf"] == uf]

            municipio = st.selectbox("Selecione o Município", sorted(df_filtered["nome_mun"].unique()))
            df_fil_mun = df_filtered[df_filtered["nome_mun"] == municipio]

    # Título da página
    st.title(f"Dados Municipais - {municipio}/{uf}")

    # Layout principal
    col1, col2, col3 = st.columns(3)

    # Coluna 1 - Informações básicas e população
    with col1:
        st.subheader("Informações Básicas")

        if not df_fil_mun.empty:
            st.metric(label="Faixa Populacional (2022)", value=df_fil_mun.iloc[0]['faixa_pop_2022'])

            # Gráfico de evolução populacional
            df_melted = df_fil_mun.melt(
                id_vars=["uf", "nome_mun"],
                value_vars=["pop_2010", "pop_2015", "pop_2016", "pop_2022"],
                var_name="Ano",
                value_name="População"
            )

            # Mapear os rótulos personalizados
            rotulos_eixo_x = {
                "pop_2010": "Censo 2010",
                "pop_2015": "Estimativa Pop 2015",
                "pop_2016": "Estimativa Pop 2016",
                "pop_2022": "Censo 2022"
            }

            df_melted["Ano_rotulo"] = df_melted["Ano"].map(rotulos_eixo_x)

            fig_pop = px.line(
                df_melted,
                x="Ano_rotulo",
                y="População",
                title="Evolução da População",
                markers=True,
                text="População",
                color_discrete_sequence=[CORES[0]]  # Usando a primeira cor (#2C95C1)
            ).update_layout(
                xaxis_title="",
                yaxis_title="População",
                hovermode="x unified"
            ).update_traces(
                textposition="top center",
                texttemplate="%{y:,.0f}",
                line=dict(width=3, color=CORES[0]),
                marker=dict(size=10, color=CORES[0])
            )

            # Ajustar ordem dos rótulos no eixo x
            fig_pop.update_xaxes(
                categoryorder='array',
                categoryarray=[
                    "Censo 2010",
                    "Estimativa Pop 2015",
                    "Estimativa Pop 2016",
                    "Censo 2022"
                ]
            )

            st.plotly_chart(fig_pop, use_container_width=True)

    # Coluna 2 - Frota de veículos do município
    with col2:
        st.subheader("Frota de Veículos (2023)")
        if not df_fil_mun.empty:
            df_frota = df_fil_mun.melt(
                id_vars=["uf", "nome_mun"],
                value_vars=["auto_2023", "moto_2023", "outr_veic_2023"],
                var_name="Tipo de Veículo",
                value_name="Quantidade"
            ).replace({
                "Tipo de Veículo": {
                    "auto_2023": "Automóveis",
                    "moto_2023": "Motocicletas",
                    "outr_veic_2023": "Outros Veículos"
                }
            })

            fig_frota = px.bar(
                df_frota,
                x="Tipo de Veículo",
                y="Quantidade",
                color="Tipo de Veículo",
                title=f"Frota em {municipio}",
                text="Quantidade",
                color_discrete_sequence=[CORES[0], CORES[1], CORES[2]]  # Usando as três primeiras cores
            ).update_traces(
                texttemplate='%{text:,}',
                textposition='outside'
            ).update_layout(
                yaxis_title="Quantidade de Veículos",
                xaxis_title="",
                showlegend=False
            )
            st.plotly_chart(fig_frota, use_container_width=True)

    # Coluna 3 - COMPARAÇÃO DE FROTAS
    with col3:
        st.subheader("Comparativo de Frota Veicular")

        if not df.empty and not df_fil_mun.empty:
            # Obter dados para cada nível geográfico
            niveis = {
                'Município': df_fil_mun.iloc[0][['auto_2023', 'moto_2023', 'outr_veic_2023']],
                'Faixa Populacional': df[df['faixa_pop_2022'] == df_fil_mun.iloc[0]['faixa_pop_2022']]
                [['auto_2023', 'moto_2023', 'outr_veic_2023']].sum(),
                'Estado': df[df['uf'] == uf][['auto_2023', 'moto_2023', 'outr_veic_2023']].sum(),
                'Brasil': df[['auto_2023', 'moto_2023', 'outr_veic_2023']].sum()
            }

            # Preparar dados para o gráfico
            dados_grafico = []
            for nivel, valores in niveis.items():
                total = valores.sum()
                for tipo, qtd in zip(['Automóveis', 'Motocicletas', 'Outros Veículos'], valores):
                    dados_grafico.append({
                        'Nível': nivel,
                        'Tipo': tipo,
                        'Quantidade': qtd,
                        'Participação': qtd / total  # Proporção dentro do próprio nível
                    })

            df_grafico = pd.DataFrame(dados_grafico)

            # Criar gráfico
            fig = px.bar(
                df_grafico,
                x='Nível',
                y='Participação',
                color='Tipo',
                barmode='group',
                text=df_grafico['Quantidade'].apply(lambda x: f"{x:,.0f}"),
                title=f"Distribuição da Frota por Nível Geográfico",
                labels={'Participação': 'Participação na Frota', 'Nível': ''},
                category_orders={"Nível": ["Município", "Faixa Populacional", "Estado", "Brasil"]},
                color_discrete_sequence=[CORES[0], CORES[1], CORES[2]]  # Usando as três primeiras cores
            )

            # Ajustes de formatação
            fig.update_traces(
                texttemplate='%{text}',
                textposition='outside',
                textfont_size=12
            )

            fig.update_layout(
                yaxis_tickformat=".1%",
                hovermode="x unified",
                legend_title_text='Tipo de Veículo',
                xaxis_title=None,
                yaxis_title="Participação na Frota",
                uniformtext_minsize=8,
                uniformtext_mode='hide'
            )

            st.plotly_chart(fig, use_container_width=True)

            # Tabela com dados detalhados
            with st.expander("Ver dados detalhados"):
                st.dataframe(
                    df_grafico.pivot_table(
                        index='Nível',
                        columns='Tipo',
                        values='Quantidade',
                        aggfunc='sum'
                    ).style.format("{:,.0f}"),
                    use_container_width=True
                )

    # Criando duas colunas
    col_esq, col_dir = st.columns(2)

    with col_esq:
        with st.expander("TAXA DE MORTALIDADE (2022)", expanded=True):
            st.subheader("Taxa por 100 mil Habitantes")

            if 'tx_mortalidade_100mil_hab' in df.columns:
                try:
                    df['tx_mortalidade_100mil_hab'] = pd.to_numeric(df['tx_mortalidade_100mil_hab'], errors='coerce')

                    # Dados comparativos
                    dados_mortalidade = {
                        'Nível': ['Município', 'Faixa', 'Estado', 'Brasil'],
                        'Taxa': [
                            df_fil_mun.iloc[0]['tx_mortalidade_100mil_hab'],
                            df[df['faixa_pop_2022'] == df_fil_mun.iloc[0]['faixa_pop_2022']][
                                'tx_mortalidade_100mil_hab'].mean(),
                            df[df['uf'] == uf]['tx_mortalidade_100mil_hab'].mean(),
                            df['tx_mortalidade_100mil_hab'].mean()
                        ]
                    }

                    df_mortalidade = pd.DataFrame(dados_mortalidade)

                    fig_mortalidade = px.bar(
                        df_mortalidade,
                        x='Nível',
                        y='Taxa',
                        text='Taxa',
                        title=f"Taxa de Mortalidade - {municipio}/{uf}",
                        labels={'Taxa': 'Óbitos/100 mil hab.'}
                    )

                    fig_mortalidade.update_traces(
                        texttemplate='%{y:.1f}',
                        textposition='outside',
                        marker_color=CORES[3]  # Usando a quarta cor (#FEBE10)
                    )

                    fig_mortalidade.update_layout(
                        yaxis_range=[0, df_mortalidade['Taxa'].max() * 1.2],
                        showlegend=False,
                        xaxis_title=None
                    )

                    st.plotly_chart(fig_mortalidade, use_container_width=True)

                except Exception as e:
                    st.error(f"Erro ao processar mortalidade: {str(e)}")

    with col_dir:
        with st.expander("ÍNDICE DE BEM-ESTAR URBANO", expanded=True):
            st.subheader("Comparativo do IBEU")

            if 'ibeu' in df.columns:
                try:
                    df['ibeu'] = pd.to_numeric(df['ibeu'], errors='coerce')

                    # Dados comparativos
                    dados_ibeu = {
                        'Nível': ['Município', 'Faixa', 'Estado', 'Brasil'],
                        'IBEU': [
                            df_fil_mun.iloc[0]['ibeu'],
                            df[df['faixa_pop_2022'] == df_fil_mun.iloc[0]['faixa_pop_2022']]['ibeu'].mean(),
                            df[df['uf'] == uf]['ibeu'].mean(),
                            df['ibeu'].mean()
                        ]
                    }

                    df_ibeu = pd.DataFrame(dados_ibeu)

                    fig_ibeu = px.bar(
                        df_ibeu,
                        x='Nível',
                        y='IBEU',
                        text='IBEU',
                        title=f"Índice de Bem-Estar - {municipio}/{uf}",
                        labels={'IBEU': 'Índice (0-1)'}
                    )

                    fig_ibeu.update_traces(
                        texttemplate='%{y:.3f}',
                        textposition='outside',
                        marker_color=CORES[4]  # Usando a quinta cor (#A8459A)
                    )

                    fig_ibeu.update_layout(
                        yaxis_range=[0, 1.05],
                        showlegend=False,
                        xaxis_title=None
                    )

                    st.plotly_chart(fig_ibeu, use_container_width=True)

                except Exception as e:
                    st.error(f"Erro ao processar IBEU: {str(e)}")

    # Legenda unificada abaixo
    st.markdown("""
    **Legenda:**
    - **Taxa de Mortalidade**: Número de óbitos por 100 mil habitantes
    - **IBEU**: Índice de 0 a 1 (quanto maior, melhor)
    """)

    # Rodapé
    st.markdown("---")
    st.caption("Dados obtidos do banco de dados PostgreSQL. Atualizado em 2023.")


if __name__ == "__main__":
    main()