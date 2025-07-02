

import streamlit as st

# Configurare pagină
st.set_page_config(
    page_title="BRENADO Dashboard",
    page_icon="🏢",
    layout="wide"
)

# Funcțiile pentru fiecare pagină
def brenado_for_house():
    st.title("🏠 BrenadoForHouse")
    st.write("Pagina pentru BrenadoForHouse")

def brenado_construct():
    st.title("🏗️ BrenadoConstruct") 
    st.write("Pagina pentru BrenadoConstruct")

def brenado_steel():
    st.title("⚙️ BrenadoSteel")
    st.write("Pagina pentru BrenadoSteel")

# Sidebar cu logo
with st.sidebar:
    st.title("🏢 BRENADO")
    st.caption("Multi-Business Dashboard")

# Configurare navigație
pages = {
    "Companii": [
        st.Page(brenado_for_house, title="BrenadoForHouse", icon="🏠"),
        st.Page(brenado_construct, title="BrenadoConstruct", icon="🏗️"),
        st.Page(brenado_steel, title="BrenadoSteel", icon="⚙️"),
    ]
}

# Navigație și rulare
pg = st.navigation(pages, position="sidebar")
pg.run()
