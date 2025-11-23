import streamlit as st
import pandas as pd
import sqlite3

DB_PATH = "/content/tp2.db"  # caminho do seu banco no Colab

@st.cache_data
def load_table(query, params=None):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(query, conn, params=params or {})
    conn.close()
    return df

st.set_page_config(page_title="AMB – Produção Bruta", layout="wide")
st.title("AMB – Produção Bruta (ANM) — Painel Interativo")

# ------------ carregar dimensões para filtros ------------
ufs = load_table("SELECT id_sigla, sigla_uf FROM UF ORDER BY sigla_uf;")
anos = load_table("SELECT id_ano, ano FROM ANO ORDER BY ano;")
classes = load_table("SELECT id_classe, nome_classe FROM CLASSE_SUBSTANCIA ORDER BY nome_classe;")
subst = load_table("""
    SELECT s.id_substancia, s.nome_substancia, c.nome_classe
    FROM SUBSTANCIA_MINERAL s
    JOIN CLASSE_SUBSTANCIA c ON c.id_classe = s.id_classe
    ORDER BY s.nome_substancia;
""")

# ------------ sidebar filtros ------------
st.sidebar.header("Filtros")

uf_sel = st.sidebar.multiselect(
    "UF",
    options=ufs["sigla_uf"].tolist(),
    default=[]
)

classe_sel = st.sidebar.multiselect(
    "Classe",
    options=classes["nome_classe"].tolist(),
    default=[]
)

subst_sel = st.sidebar.multiselect(
    "Substância",
    options=subst["nome_substancia"].tolist(),
    default=[]
)

ano_sel = st.sidebar.multiselect(
    "Ano",
    options=anos["ano"].tolist(),
    default=[]
)

def build_where():
    where = []
    params = {}

    if uf_sel:
        where.append("u.sigla_uf IN ({})".format(",".join([":uf"+str(i) for i in range(len(uf_sel))])))
        for i,v in enumerate(uf_sel):
            params["uf"+str(i)] = v

    if classe_sel:
        where.append("c.nome_classe IN ({})".format(",".join([":cl"+str(i) for i in range(len(classe_sel))])))
        for i,v in enumerate(classe_sel):
            params["cl"+str(i)] = v

    if subst_sel:
        where.append("s.nome_substancia IN ({})".format(",".join([":sb"+str(i) for i in range(len(subst_sel))])))
        for i,v in enumerate(subst_sel):
            params["sb"+str(i)] = v

    if ano_sel:
        where.append("a.ano IN ({})".format(",".join([":an"+str(i) for i in range(len(ano_sel))])))
        for i,v in enumerate(ano_sel):
            params["an"+str(i)] = v

    return ("WHERE " + " AND ".join(where)) if where else "", params

where_sql, params = build_where()

# ------------ visão geral filtrada ------------
st.subheader("Tabela filtrada (UF × Substância × Ano × Unidade)")

q_base = f"""
SELECT u.sigla_uf, a.ano, c.nome_classe, s.nome_substancia,
       uc.unidade,
       rp.quantidade_rom, rp.quantidade_contido, rp.quantidade_venda,
       rp.valor_venda
FROM REGISTRO_PRODUCAO rp
JOIN UF u ON u.id_sigla = rp.id_sigla
JOIN ANO a ON a.id_ano = rp.id_ano
JOIN SUBSTANCIA_MINERAL s ON s.id_substancia = rp.id_substancia
JOIN CLASSE_SUBSTANCIA c ON c.id_classe = s.id_classe
JOIN UNIDADE_CONTIDO uc ON uc.id_unidade_contido = rp.id_unidade_contido
{where_sql}
ORDER BY a.ano DESC, u.sigla_uf, s.nome_substancia
LIMIT 500;
"""
df_base = load_table(q_base, params)
st.dataframe(df_base, use_container_width=True, height=320)

# ------------ gráficos ------------
st.subheader("Gráficos")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Produção ROM por ano (filtros aplicados)**")
    q_rom_ano = f"""
    SELECT a.ano, SUM(rp.quantidade_rom) AS rom_total
    FROM REGISTRO_PRODUCAO rp
    JOIN ANO a ON a.id_ano = rp.id_ano
    JOIN UF u ON u.id_sigla = rp.id_sigla
    JOIN SUBSTANCIA_MINERAL s ON s.id_substancia = rp.id_substancia
    JOIN CLASSE_SUBSTANCIA c ON c.id_classe = s.id_classe
    {where_sql}
    GROUP BY a.ano
    ORDER BY a.ano;
    """
    df_rom_ano = load_table(q_rom_ano, params)
    st.line_chart(df_rom_ano.set_index("ano"))

with col2:
    st.markdown("**Valor de venda por classe (filtros aplicados)**")
    q_val_classe = f"""
    SELECT c.nome_classe, SUM(rp.valor_venda) AS valor_total
    FROM REGISTRO_PRODUCAO rp
    JOIN SUBSTANCIA_MINERAL s ON s.id_substancia = rp.id_substancia
    JOIN CLASSE_SUBSTANCIA c ON c.id_classe = s.id_classe
    JOIN UF u ON u.id_sigla = rp.id_sigla
    JOIN ANO a ON a.id_ano = rp.id_ano
    {where_sql}
    GROUP BY c.nome_classe
    ORDER BY valor_total DESC;
    """
    df_val_classe = load_table(q_val_classe, params)
    st.bar_chart(df_val_classe.set_index("nome_classe"))

# ------------ rankings ------------
st.subheader("Rankings")

tab1, tab2 = st.tabs(["Top substâncias (ROM)", "Top UFs (Valor Venda)"])

with tab1:
    q_top_subst = f"""
    SELECT s.nome_substancia, SUM(rp.quantidade_rom) AS rom_total
    FROM REGISTRO_PRODUCAO rp
    JOIN SUBSTANCIA_MINERAL s ON s.id_substancia = rp.id_substancia
    JOIN UF u ON u.id_sigla = rp.id_sigla
    JOIN ANO a ON a.id_ano = rp.id_ano
    JOIN CLASSE_SUBSTANCIA c ON c.id_classe = s.id_classe
    {where_sql}
    GROUP BY s.nome_substancia
    ORDER BY rom_total DESC
    LIMIT 20;
    """
    st.dataframe(load_table(q_top_subst, params), use_container_width=True)

with tab2:
    q_top_uf = f"""
    SELECT u.sigla_uf, SUM(rp.valor_venda) AS valor_total
    FROM REGISTRO_PRODUCAO rp
    JOIN UF u ON u.id_sigla = rp.id_sigla
    JOIN ANO a ON a.id_ano = rp.id_ano
    JOIN SUBSTANCIA_MINERAL s ON s.id_substancia = rp.id_substancia
    JOIN CLASSE_SUBSTANCIA c ON c.id_classe = s.id_classe
    {where_sql}
    GROUP BY u.sigla_uf
    ORDER BY valor_total DESC
    LIMIT 20;
    """
    st.dataframe(load_table(q_top_uf, params), use_container_width=True)

st.caption("TP2 Banco de Dados — painel Streamlit extra.")
