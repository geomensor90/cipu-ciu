import streamlit as st
import requests
from pyproj import Transformer

# Configuração do conversor de coordenadas
transformer = Transformer.from_crs("EPSG:31983", "EPSG:4326", always_xy=True)

# Título do app
st.title("Consulta de Cadastro Territorial")

# Formulário de pesquisa
with st.form("search_form"):
    search_field = st.selectbox("Pesquisar por", ["CIU", "CIPU"])
    search_value = st.text_input("Digite o valor para pesquisa")
    submitted = st.form_submit_button("Pesquisar")

if submitted:
    if not search_value.strip():
        st.warning("Por favor, insira um valor para a pesquisa.")
    else:
        st.info("Pesquisando...")

        # Monta a cláusula WHERE
        if search_field == "CIU":
            where_clause = f"pu_ciu LIKE '{search_value}%'"
        else:  # CIPU
            if not search_value.isdigit():
                st.error("Para pesquisa por CIPU, insira um número válido.")
                st.stop()
            where_clause = f"pu_cipu = {int(search_value)}"

        # Parâmetros da API
        api_url = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/10/query"
        params = {
            "where": where_clause,
            "outFields": "pu_ciu,pu_cipu,pu_projeto,pu_situacao,pn_norma_vg,x,y",
            "returnGeometry": "false",
            "f": "json"
        }

        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data.get("features"):
                st.warning("Nenhum resultado encontrado para sua pesquisa.")
            else:
                st.success(f"{len(data['features'])} resultado(s) encontrado(s).")

                # Processa e exibe cada resultado
                for idx, feature in enumerate(data["features"], start=1):
                    attrs = feature["attributes"]
                    x = attrs.get("x")
                    y = attrs.get("y")

                    if x is not None and y is not None:
                        lon, lat = transformer.transform(x, y)
                        lon = round(lon, 6)
                        lat = round(lat, 6)
                    else:
                        lon, lat = "N/A", "N/A"

                    # Exibe o resultado como ficha
                    st.write(f"**CIU**: {attrs.get('pu_ciu', 'N/A')}")
                    st.write(f"**CIPU**: {attrs.get('pu_cipu', 'N/A')}")
                    st.write(f"**Projeto**: {attrs.get('pu_projeto', 'N/A')}")
                    st.write(f"**Situação**: {attrs.get('pu_situacao', 'N/A')}")
                    st.write(f"**Norma VG**: {attrs.get('pn_norma_vg', 'N/A')}")
                    st.write(f"**Latitude (WGS84)**: {lat}")
                    st.write(f"**Longitude (WGS84)**: {lon}")

        except requests.RequestException as e:
            st.error(f"Erro ao buscar dados: {e}")
