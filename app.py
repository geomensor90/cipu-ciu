import streamlit as st
import requests
from pyproj import Transformer
import folium
from streamlit_folium import st_folium, folium_static
from datetime import date
import pandas as pd
from pyproj import Transformer
import time
from math import sqrt, radians, sin, cos, sqrt, atan2
import json
import numpy as np
from scipy import interpolate
import plotly.express as px
import plotly.graph_objects as go
import re
import unicodedata
import simplekml
import plotly.graph_objects as go
from streamlit_geolocation import streamlit_geolocation
import textwrap

st.set_page_config(page_title="Ferramentas para HBT", page_icon="🌍")

# ----------------------------------------------------------------------
# Bloco st.expander
# ----------------------------------------------------------------------
with st.expander("Buscar Lotes e Soleiras por Mapa", expanded=False):
    # Ponto padrão em Brasília
    default_point = [-15.793665, -47.882956]  # (lat, lon)
    #default_point = [-15.827259, -47.979645]  # (lat, lon)
    st.markdown("Consulta de Lotes, Pontos e Alvarás - Raio de 50m")

    # Initialize session state variables if they don't exist
    if "lotes_geojson" not in st.session_state:
        st.session_state.lotes_geojson = None
    if "pontos_geojson" not in st.session_state:
        st.session_state.pontos_geojson = None
    if "clicked_point" not in st.session_state:
        st.session_state.clicked_point = default_point


    
    col_geo, col_text = st.columns([0.07, 1])
    with col_geo:
        # Primeira Coluna: A função que renderiza o botão/componente
        # Chamada simples para evitar o erro de sintaxe
        location2 = streamlit_geolocation() 

    with col_text:
        # Segunda Coluna: O texto de instrução
        # Usando st.markdown para formatar o texto e alinhá-lo
        st.write("<<< Coordenada Atual (GPS)")

            
    # Variáveis para armazenar as coordenadas obtidas (se existirem)
    current_geo_lat = None
    current_geo_lon = None

    # Verifica se a localização foi retornada
    if location2:
        latitude = location2.get('latitude')
        longitude = location2.get('longitude')
        
        if latitude is not None and longitude is not None:
            st.success("✅ Localização Encontrada!")      
            #st.subheader("Coordenadas Atuais:")
            col_lat, col_lon = st.columns(2)           
            #st.write(f"**Latitude:** `{latitude}`")       
            #st.write(f"**Longitude:** `{longitude}`")
            current_geo_lat = latitude
            current_geo_lon = longitude
        #else:
            #st.warning("⚠️ Não foi possível obter a localização. Verifique as permissões do seu navegador.")      
    else:
        st.info("Aguardando o clique no botão e a permissão de localização do navegador...") 


    # --- Botões de Carregamento de Coordenadas ---
    
    # Cria uma coluna para os botões para melhor organização
    col1, col2 = st.columns(2)
    
    with col1:
        # Botão para carregar a coordenada do CIPU
        if st.button("Carregar coordenada CIPU"):
            if "map_coords_list" in st.session_state and st.session_state.map_coords_list:
                selected_coords = st.session_state.map_coords_list[st.session_state.selected_feature_index]
                if selected_coords:
                    st.session_state.clicked_point = selected_coords
                    current_lat, current_lon = selected_coords
                    st.session_state.msg = f"✅ Coordenada CIPU carregada: {current_lat:.6f}, {current_lon:.6f}"
                else:
                    st.session_state.msg = "⚠️ A coordenada CIPU não está disponível."
            else:
                st.session_state.msg = "⚠️ Primeiro busque um CIPU no Parâmetros Urbanísticos."

    with col2:
        # NOVO BOTÃO: Carrega a coordenada obtida pela geolocalização do navegador
        if st.button("Carregar Coordenada Atual"):
            if current_geo_lat is not None and current_geo_lon is not None:
                st.session_state.clicked_point = (current_geo_lat, current_geo_lon)
                st.session_state.msg = f"✅ Coordenada atual carregada: {current_geo_lat:.6f}, {current_geo_lon:.6f}"
            else:
                st.session_state.msg = "⚠️ Primeiro clique no Alvo acima"
            
    # Exibe mensagem persistente
    if "msg" in st.session_state:
        st.info(st.session_state.msg)

    # Get the current latitude and longitude from session state
    current_lat, current_lon = st.session_state.clicked_point

    # Manual input for coordinates (pre-filled with current_lat, current_lon)
    lat_input = st.number_input("Latitude", value=current_lat, format="%.6f")
    lon_input = st.number_input("Longitude", value=current_lon, format="%.6f")


    # If manual inputs change, update the clicked_point
    if (lat_input, lon_input) != st.session_state.clicked_point:
        st.session_state.clicked_point = (lat_input, lon_input)
        current_lat, current_lon = (lat_input, lon_input)

    st.write(f"Coordenada atual: **{current_lat:.6f}, {current_lon:.6f}**")

    # Create a Folium map centered at the current_lat, current_lon
    mapa = folium.Map(location=[current_lat, current_lon], zoom_start=18, tiles="Esri.WorldImagery", max_zoom=25)

    # Add a marker for the selected point
    folium.CircleMarker(
        location=[current_lat, current_lon],
        radius=2,              # raio do ponto (quanto menor, mais discreto)
        color="red",           # cor da borda
        fill=True,
        fill_color="red",      # cor de preenchimento
        fill_opacity=1,        # opacidade total
        tooltip="Ponto Selecionado"
    ).add_to(mapa)

    # Add a 50m radius circle around the selected point
    folium.Circle(
        location=[current_lat, current_lon],
        radius=50,
        color="blue",
        fill=True,
        fill_opacity=0.01,
        tooltip="Raio 50m"
    ).add_to(mapa)

    # Adiciona a camada WMS dos lotes (desligada por padrão)
    folium.raster_layers.WmsTileLayer(
        url="https://www.geoservicos.ide.df.gov.br/arcgis/services/Publico/CADASTRO_TERRITORIAL/MapServer/WMSServer",
        name="Lotes Registrados",
        layers="6",
        fmt="image/png",
        transparent=True,
        max_zoom=23,
        attr="GDF / GeoServiços",
        show=False  # Desligado por padrão
    ).add_to(mapa)

    # Adiciona a camada WMS das quadras (desligada por padrão)
    folium.raster_layers.WmsTileLayer(
        url="https://www.geoservicos.ide.df.gov.br/arcgis/services/Publico/CADASTRO_TERRITORIAL/MapServer/WMSServer",
        name="Quadra",
        layers="3",
        fmt="image/png",
        transparent=True,
        max_zoom=23,
        attr="Quadra",
        show=False  # Desligado por padrão
    ).add_to(mapa)

    # Adiciona a camada WMS das quadras (desligada por padrão)
    folium.raster_layers.WmsTileLayer(
        url="https://www.geoservicos.ide.df.gov.br/arcgis/services/Publico/CADASTRO_TERRITORIAL/MapServer/WMSServer",
        name="Conjuntos",
        layers="4",
        fmt="image/png",
        transparent=False,
        max_zoom=23,
        attr="Conjuntos",
        opacity=0.7,   # <--- 1.0 = máximo
        show=False  # Desligado por padrão
    ).add_to(mapa)    
    
    # --- Camadas GeoJSON ---

    # Se lotes_geojson data exists in session state, add it to the map
    if st.session_state.lotes_geojson:
        folium.GeoJson(
            st.session_state.lotes_geojson,
            name="Lotes em 50m",
            tooltip=folium.features.GeoJsonTooltip(
                fields=['pu_cipu', 'pu_end_usual'],
                aliases=['CIPU:', 'Endereço:']
            ),
            popup=folium.features.GeoJsonPopup(
                fields=['pu_cipu', 'pu_end_usual'],
                aliases=['CIPU:', 'Endereço:']
            )
        ).add_to(mapa)

    # Add the points_geojson layer (Cota)
    if st.session_state.pontos_geojson:
        folium.GeoJson(
            st.session_state.pontos_geojson,
            name="Pontos de Cota",
            marker=folium.Marker(icon=folium.Icon(color="red", icon="info-sign")),
            tooltip=folium.features.GeoJsonTooltip(
                fields=['cs_cota', 'cs_link'],
                aliases=['Cota:', 'Link:'],
                labels=True,
                sticky=False
            ),
            popup=folium.features.GeoJsonPopup(
                fields=['cs_cota', 'cs_link'],
                aliases=['Cota:', 'Link:']
            )
        ).add_to(mapa)


    #folium.TileLayer("OpenStreetMap", name="Mapa de Rua").add_to(mapa)
    # Adiciona controle de camadas
    folium.LayerControl(collapsed=True).add_to(mapa)


    # Display the map and capture clicks
    map_data = st_folium(mapa, height=600, width="100%")


    # Update coordinates if the map was clicked
    if map_data and map_data["last_clicked"]:
        new_lat = map_data["last_clicked"]["lat"]
        new_lon = map_data["last_clicked"]["lng"]
        if (new_lat, new_lon) != st.session_state.clicked_point:
            st.session_state.clicked_point = (new_lat, new_lon)
            st.rerun()

    # --- Botões de Consulta ---

    if st.button("Carregar Lotes (Raio de 50m)"):
        query_lat, query_lon = st.session_state.clicked_point
        url = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/MapServer/10/query"
        params = {
            "geometry": f'{{"x": {query_lon}, "y": {query_lat}, "spatialReference": {{"wkid": 4326}}}}',
            "geometryType": "esriGeometryPoint",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "distance": 50,
            "units": "esriSRUnit_Meter",
            "outFields": "pu_cipu,pu_end_usual",
            "returnGeometry": "true",
            "f": "geojson"
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "features" in data and len(data["features"]) > 0:
                st.session_state.lotes_geojson = data
                st.success(f"🎉 {len(data['features'])} lote(s) encontrado(s).")
                st.rerun()
            else:
                st.session_state.lotes_geojson = None
                st.warning("🧐 Nenhum lote encontrado no raio de 50m.")
                st.rerun()
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erro na consulta ao serviço de lotes: {e}")
        except ValueError:
            st.error("❌ Erro ao decodificar a resposta JSON.")

    if st.button("Carregar Pontos de Cota (Raio de 50m)"):
        query_lat, query_lon = st.session_state.clicked_point
        url = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Aplicacoes/COTA_SOLEIRA/MapServer/0/query"
        params = {
            "geometry": f'{{"x": {query_lon}, "y": {query_lat}, "spatialReference": {{"wkid": 4326}}}}',
            "geometryType": "esriGeometryPoint",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "distance": 50,
            "units": "esriSRUnit_Meter",
            "outFields": "cs_cota,cs_link",
            "returnGeometry": "true",
            "f": "geojson"
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if "features" in data and len(data["features"]) > 0:
                st.session_state.pontos_geojson = data
                st.success(f"🎉 {len(data['features'])} ponto(s) de cota encontrado(s).")
                st.rerun()
            else:
                st.session_state.pontos_geojson = None
                st.warning("🧐 Nenhum ponto de cota encontrado no raio de 50m.")
                st.rerun()
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Erro na consulta ao serviço de pontos: {e}")
        except ValueError:
            st.error("❌ Erro ao decodificar a resposta JSON.")













































# Use um expander para "esconder" o formulário de busca
with st.expander("Encontre o CIPU do imóvel pelo Endereço", expanded=False):
    # URL do serviço ArcGIS REST para consulta de endereços
    ARCGIS_SERVICE_URL = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/10/query"

    # Campos de interesse
    ADDRESS_FIELD_NAME = "pu_end_usual"
    CARTORIAL_NAME = "pu_end_cart"
    CIPU_FIELD_NAME = "pu_cipu" 
    CIU_FIELD_NAME = "pu_ciu"
    END_CARTORIAL = "pu_end_cart"
    END_USUAL = "pu_end_usual"     


    st.markdown("🗺️ **Localizador de Endereços por Quadra - Geoportal DF**")

    st.markdown(
        """
        Digite o nome de uma **quadra** (ex: `SQN 205`, `SCLN 309`) para listar todos os endereços 
        cadastrados dentro dela. Isso ajudará a localizar o prédio exato antes de usar o CIPU/CIU.
        """
    )

    # Campo de entrada para a quadra
    quadra_input = st.text_input("Busca pelo Endereço Usual", "")

    if st.button("Buscar Endereço Usual"):
        if quadra_input:
            with st.spinner("Buscando endereços na quadra..."):
                try:
                    search_term = quadra_input.upper()

                    query_params = {
                        "where": f"UPPER({ADDRESS_FIELD_NAME}) LIKE '%{search_term}%'",
                        "outFields": "*",
                        "f": "json",
                        "resultRecordCount": 5000,
                    }

                    response = requests.get(ARCGIS_SERVICE_URL, params=query_params)
                    response.raise_for_status()
                    data = response.json()

                    if "features" in data and data["features"]:
                        st.success(f"Encontrados {len(data['features'])} endereços relacionados a '{quadra_input}':")
                        
                        results = []
                        for feature in data["features"]:
                            attrs = feature.get("attributes", {})
                            results.append({
                                ADDRESS_FIELD_NAME: attrs.get(ADDRESS_FIELD_NAME, "—"),
                                CARTORIAL_NAME: attrs.get(CARTORIAL_NAME, "—"),
                                CIPU_FIELD_NAME: attrs.get(CIPU_FIELD_NAME, "—"),
                                CIU_FIELD_NAME: attrs.get(CIU_FIELD_NAME, "—"),
                                
                                **attrs  # mantém os demais dados disponíveis
                            })
                        
                        if results:
                            df = pd.DataFrame(results)

                            # Ordena as colunas: endereço, CIPU, CIU primeiro
                            cols_order = [col for col in [ADDRESS_FIELD_NAME, CARTORIAL_NAME, CIPU_FIELD_NAME, CIU_FIELD_NAME] if col in df.columns]
                            other_cols = [col for col in df.columns if col not in cols_order]
                            df = df[cols_order + other_cols]

                            st.dataframe(df[cols_order], use_container_width=True)

                            st.markdown("---")
                            st.info("Você pode copiar o CIPU ou CIU da tabela acima para outras pesquisas.")

                        else:
                            st.warning(f"Nenhum dado encontrado com campos úteis para '{quadra_input}'.")
                    else:
                        st.warning(f"Nenhum endereço encontrado para '{quadra_input}'. Tente ser mais genérico ou verifique a grafia.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Erro ao conectar ao serviço do Geoportal: {e}")
                except KeyError as e:
                    st.error(f"Erro ao processar os dados. Campo faltando: '{e}'")
                    st.info(f"Verifique os nomes dos campos no serviço: https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/10")
                except Exception as e:
                    st.error(f"Ocorreu um erro inesperado: {e}")
        else:
            st.warning("Por favor, digite uma quadra ou parte do endereço para buscar.")

    ### busca pelo endereço cartorial
    st.markdown("---")
    # Campo de entrada para a quadra
    quadra_input2 = st.text_input("Busca pelo Endereço Cartorial", "")

    if st.button("Buscar Endereço Cartorial"):
        if quadra_input2:
            with st.spinner("Buscando endereços na quadra..."):
                try:
                    search_term = quadra_input2.upper()

                    query_params = {
                        "where": f"UPPER({CARTORIAL_NAME}) LIKE '%{search_term}%'",
                        "outFields": "*",
                        "f": "json",
                        "resultRecordCount": 5000,
                    }

                    response = requests.get(ARCGIS_SERVICE_URL, params=query_params)
                    response.raise_for_status()
                    data = response.json()

                    if "features" in data and data["features"]:
                        st.success(f"Encontrados {len(data['features'])} endereços relacionados a '{quadra_input2}':")
                        
                        results = []
                        for feature in data["features"]:
                            attrs = feature.get("attributes", {})
                            results.append({
                                ADDRESS_FIELD_NAME: attrs.get(ADDRESS_FIELD_NAME, "—"),
                                CARTORIAL_NAME: attrs.get(CARTORIAL_NAME, "—"),
                                CIPU_FIELD_NAME: attrs.get(CIPU_FIELD_NAME, "—"),
                                CIU_FIELD_NAME: attrs.get(CIU_FIELD_NAME, "—"),
                                
                                **attrs  # mantém os demais dados disponíveis
                            })
                        
                        if results:
                            df = pd.DataFrame(results)

                            # Ordena as colunas: endereço, CIPU, CIU primeiro
                            cols_order = [col for col in [ADDRESS_FIELD_NAME, CARTORIAL_NAME, CIPU_FIELD_NAME, CIU_FIELD_NAME] if col in df.columns]
                            other_cols = [col for col in df.columns if col not in cols_order]
                            df = df[cols_order + other_cols]

                            st.dataframe(df[cols_order], use_container_width=True)

                            st.markdown("---")
                            st.info("Você pode copiar o CIPU ou CIU da tabela acima para outras pesquisas.")

                        else:
                            st.warning(f"Nenhum dado encontrado com campos úteis para '{quadra_input2}'.")
                    else:
                        st.warning(f"Nenhum endereço encontrado para '{quadra_input2}'. Tente ser mais genérico ou verifique a grafia.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Erro ao conectar ao serviço do Geoportal: {e}")
                except KeyError as e:
                    st.error(f"Erro ao processar os dados. Campo faltando: '{e}'")
                    st.info(f"Verifique os nomes dos campos no serviço: https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/10")
                except Exception as e:
                    st.error(f"Ocorreu um erro inesperado: {e}")
        else:
            st.warning("Por favor, digite uma quadra ou parte do endereço para buscar.")

    st.markdown("Dados do Geoportal IDE/DF.")
# --- Configuração do conversor de coordenadas ---
# Transforma de EPSG:31983 (SIRGAS 2000 / UTM zone 23S - Brasília) para EPSG:4326 (WGS84 - Latitude/Longitude)
transformer = Transformer.from_crs("EPSG:31983", "EPSG:4326", always_xy=True)

# URL base para os arquivos
BASE_FILE_URL = "https://www.geoservicos.ide.df.gov.br/anexos/PLANTAS_URBANAS/"
IMAGEM_JPG = ".jpg"

# --- Inicializar st.session_state para armazenar os dados e a coordenada do mapa ---
if 'all_general_data' not in st.session_state:
    st.session_state.all_general_data = [] # Lista para armazenar todos os resultados gerais
if 'luos_data_map' not in st.session_state:
    st.session_state.luos_data_map = {} # Dicionário para armazenar dados LUOS por CIPU
if 'last_search_cipu' not in st.session_state:
    st.session_state.last_search_cipu = None
if 'map_coords_list' not in st.session_state:
    st.session_state.map_coords_list = [] # Lista de coordenadas para múltiplos marcadores
if 'selected_feature_index' not in st.session_state:
    st.session_state.selected_feature_index = 0
if 'show_luos_data' not in st.session_state: # Novo estado para controlar a exibição do LUOS
    st.session_state.show_luos_data = False
if 'show_map' not in st.session_state: # Novo estado para controlar a exibição do mapa
    st.session_state.show_map = False


if "show_year_selector" not in st.session_state:
    st.session_state.show_year_selector = False
if "selected_year" not in st.session_state:
    st.session_state.selected_year = "2025"  # ou "2022" — escolha um padrão

# # # # # # # # # # # # 
if 'normas_data_map' not in st.session_state:
    st.session_state.normas_data_map = {}  # Cache de normas por CIPU
if 'show_normas_data' not in st.session_state:
    st.session_state.show_normas_data = False
# # # # # # # # # # # # 

# # # # # # # # # # # # 
if 'normas_data_map2' not in st.session_state:
    st.session_state.normas_data_map2 = {}  # Cache de normas por CIPU
if 'show_normas_data2' not in st.session_state:
    st.session_state.show_normas_data2 = False
# # # # # # # # # # # # 




# # # # # # # # # # # # 
# Inicializar o estado da sessão (session_state)
if 'cota_soleira_data_map' not in st.session_state:
    st.session_state.cota_soleira_data_map = {}
if 'show_cota_soleira_data' not in st.session_state:
    st.session_state.show_cota_soleira_data = False
# # # # # # # # # # # # 


# Título do app
st.subheader("Parâmetros Urbanísticos")

# Formulário de pesquisa
with st.form("search_form"):
    search_field = st.selectbox("Pesquisar por", ["CIPU", "CIU"])
    search_value = st.text_input("Digite o valor para pesquisa")
    submitted = st.form_submit_button("Pesquisar")

if submitted:
    st.session_state.show_year_selector = True
    search_value = search_value.replace(".", "").replace(",", "").strip()

    # Reinicia os estados de exibição ao submeter uma nova pesquisa
    st.session_state.show_luos_data = False
    st.session_state.show_map = False

    if not search_value.strip():
        st.warning("Por favor, insira um valor para a pesquisa.")
        st.session_state.all_general_data = []
        st.session_state.luos_data_map = {}
        st.session_state.last_search_cipu = None
        st.session_state.map_coords_list = []
        st.session_state.selected_feature_index = 0
        
    else:
        pass

        # Monta a cláusula WHERE para a API principal
        if search_field == "CIU":
            where_clause = f"pu_ciu LIKE '{search_value}%'"
        elif search_field == "pu_arquivo":
            where_clause = f"pu_arquivo LIKE '%{search_value}%'" # Usar % em ambos os lados para buscar dentro da string
        else:  # CIPU
            if not search_value.isdigit():
                st.error("Para pesquisa por CIPU, insira um número válido.")
                st.session_state.all_general_data = []
                st.session_state.luos_data_map = {}
                st.session_state.last_search_cipu = None
                st.session_state.map_coords_list = []
                st.session_state.selected_feature_index = 0
                st.stop()
                st.session_state.show_year_selector = False
            where_clause = f"pu_cipu = {int(search_value)}"

        # Parâmetros da API principal
        api_url = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/10/query"
        params = {
            "where": where_clause,
            "outFields": "pu_ciu,pu_cipu,pu_projeto,pn_cod_par,pu_end_cart,pu_ra,pu_end_usual,pu_situacao,pn_norma_vg,x,y,pu_arquivo,qd_dim_frente,qd_dim_fundo,qd_dim_lat_dir,qd_dim_lat_esq,qd_dim_chanfro", # Incluindo pu_arquivo
            "returnGeometry": "true",
            "f": "json"
        }
       
        try:
            response = requests.get(api_url, params=params)
            response.raise_for_status() # Levanta um erro para códigos de status HTTP ruins (4xx ou 5xx)
            data = response.json()

            if not data.get("features"):
                st.warning("Nenhum resultado encontrado para sua pesquisa.")
                st.session_state.all_general_data = []
                st.session_state.luos_data_map = {}
                st.session_state.last_search_cipu = None
                st.session_state.map_coords_list = []
                st.session_state.selected_feature_index = 0
                
            else:
                #st.success(f"{len(data['features'])} resultado(s) encontrado(s).")
                
                # Limpa estados anteriores para a nova busca
                st.session_state.all_general_data = []
                st.session_state.luos_data_map = {}
                st.session_state.map_coords_list = []
                st.session_state.selected_feature_index = 0 # Reinicia a seleção para o primeiro item

                for feature in data["features"]:
                    attrs = feature["attributes"]
                    x = attrs.get("x")
                    y = attrs.get("y")
                    pu_cipu = attrs.get("pu_cipu")

                    current_lat, current_lon = "N/A", "N/A"
                    if x is not None and y is not None:
                        current_lon, current_lat = transformer.transform(x, y) # pyproj retorna (longitude, latitude)
                        current_lon = round(current_lon, 6)
                        current_lat = round(current_lat, 6)
                        st.session_state.map_coords_list.append([current_lat, current_lon])
                    else:
                        st.session_state.map_coords_list.append(None) # Adiciona None se não houver coordenada

                    # Salva os dados gerais na lista
                    general_entry = {
                        "ciu": attrs.get('pu_ciu', 'N/A'),
                        "cipu": pu_cipu if pu_cipu is not None else 'N/A',
                        "end_cartorial": attrs.get('pu_end_cart', 'N/A'),
                        "end_usual": attrs.get('pu_end_usual', 'N/A'),
                        "projeto": attrs.get('pu_projeto', 'N/A'),
                        "situacao_codigo": attrs.get('pu_situacao'),
                        "norma_vigente": attrs.get('pn_norma_vg', 'N/A'),
                        "latitude": current_lat,
                        "longitude": current_lon,
                        "pu_ra": attrs.get('pu_ra', 'N/A'), 
                        "pu_arquivo": attrs.get('pu_arquivo', 'N/A'), 
                        "codigo_parametro": attrs.get('pn_cod_par', 'N/A'), 
                        "dimensao_frente": attrs.get('qd_dim_frente', 'N/A'), 
                        "dimensao_fundo": attrs.get('qd_dim_fundo', 'N/A'), 
                        "dimensao_direita": attrs.get('qd_dim_lat_dir', 'N/A'), 
                        "dimensao_esquerda": attrs.get('qd_dim_lat_esq', 'N/A'), 
                        "dimensao_chanfro": attrs.get('qd_dim_chanfro', 'N/A'),
                        "geometry": feature.get("geometry"), # <-- Novo campo para armazenar a geometria,
                    }
                    st.session_state.all_general_data.append(general_entry)

                    # A consulta LUOS será feita apenas quando o botão "Carregar dados LUOS" for clicado
                    # e o CIPU ainda não estiver no cache.
                    # Não precisamos consultar aqui, apenas garantir que o CIPU existe para o botão
        except requests.RequestException as e:
            st.error(f"Ocorreu um erro ao buscar os dados: {e}")
            st.session_state.all_general_data = []
            st.session_state.luos_data_map = {}
            st.session_state.map_coords_list = []
            st.session_state.selected_feature_index = 0

# --- Exibir os Dados Gerais para cada resultado ---
if st.session_state.all_general_data:
    st.subheader("Resultados da Pesquisa")

    

    # Criar um seletor para navegar entre os resultados
    if len(st.session_state.all_general_data) > 1:
        options = [
            f"Item {i+1}: CIPU {data['cipu']} | CIU {data['ciu']} | Arquivo {data['pu_arquivo']}"
            for i, data in enumerate(st.session_state.all_general_data)
        ]
        # Atualiza o índice de seleção e reseta a exibição do LUOS e mapa ao mudar a seleção
        current_selected_index = st.session_state.selected_feature_index
        st.session_state.selected_feature_index = st.selectbox(
            "Selecione um resultado para ver os detalhes:",
            options=range(len(st.session_state.all_general_data)),
            format_func=lambda x: options[x],
            index=st.session_state.selected_feature_index,
            key="feature_selector"
        )
        if current_selected_index != st.session_state.selected_feature_index:
            st.session_state.show_luos_data = False
            st.session_state.show_map = False
    
    selected_data = st.session_state.all_general_data[st.session_state.selected_feature_index]
    selected_cipu = selected_data.get('cipu')

    # --- Dados Gerais ---
    with st.expander(f"**Dados Gerais do Imóvel**"):
        st.write(f"**CIU**: {selected_data.get('ciu', 'N/A')}")
        cipu = selected_data.get('cipu', 'N/A')
        if cipu != 'N/A':
            st.write(f"**CIPU**: {int(round(cipu))}")
        else:
            st.write(f"**CIPU**: {cipu}")
        
        # --- Lógica para múltiplos links do pu_arquivo ---
        pu_arquivo_raw = selected_data.get('pu_arquivo')
        if pu_arquivo_raw and pu_arquivo_raw.strip() != 'N/A':
            # Divide a string em múltiplos arquivos
            file_names = [name.strip() for name in pu_arquivo_raw.split(';') if name.strip()]
            
            st.write(f"**Arquivo(s)**:")
            for file_name in file_names:
                full_file_url = f"{BASE_FILE_URL}{file_name}{IMAGEM_JPG}"
                st.markdown(f"- [{file_name}]({full_file_url})")
        else:
            st.write(f"**Arquivo(s)**: N/A")
        # --- Fim da lógica para múltiplos links ---
        # Mapeia os códigos de pu_ra para os nomes das regiões administrativas
        regioes_administrativas = {
            1: "Plano Piloto",
            2: "Gama",
            3: "Taguatinga",
            4: "Brazlândia",
            5: "Sobradinho",
            6: "Planaltina",
            7: "Paranoá",
            8: "Núcleo Bandeirante",
            9: "Ceilândia",
            10: "Guará",
            11: "Cruzeiro",
            12: "Samambaia",
            13: "Santa Maria",
            14: "São Sebastião",
            15: "Recanto das Emas",
            16: "Lago Sul",
            17: "Riacho Fundo",
            18: "Lago Norte",
            19: "Candangolândia",
            20: "Águas Claras",
            21: "Riacho Fundo II",
            22: "Sudoeste/Octogonal",
            23: "Varjão",
            24: "Park Way",
            25: "SCIA",
            26: "Sobradinho II",
            27: "Jardim Botânico",
            28: "Itapoã",
            29: "SIA",
            30: "Vicente Pires",
            31: "Fercal",
            32: "Sol Nascente e Por do Sol",
            33: "Arniqueira",
            34: "Arapoanga",
            35: "Água Quente",
            # Adicione mais mapeamentos conforme necessário
        }

        # Obtém o código de pu_ra, com 'N/A' como valor padrão
        codigo_ra = selected_data.get('pu_ra', 'N/A')
        nome_ra = regioes_administrativas.get((codigo_ra), 'N/A')

        #st.write(f"**Endereço Cartorial:**: {selected_data.get('end_cartorial', 'N/A')}")
        st.write(f"**Endereço Cartorial:** {selected_data.get('end_cartorial', 'N/A')} ({nome_ra})")
        st.write(f"**Endereço Usual**: {selected_data.get('end_usual', 'N/A')} ({nome_ra})")
        st.write(f"**Projeto**: {selected_data.get('projeto', 'N/A')}")
        
        #st.write(f"**Norma Vigente**: {selected_data.get('norma_vigente', 'N/A')}")
        norma_vigente = selected_data.get('norma_vigente', 'N/A')

        
        linkppcub = 'https://sistemas.df.gov.br/PPCUB_SEDUH/Geoportal?File='
        codigo_parametro = selected_data.get('codigo_parametro')

        st.write(f"**Código do Parâmetro**: {codigo_parametro}")
        # Adiciona texto adicional conforme o caso
        # Adiciona texto adicional conforme o caso
        if norma_vigente == "LC 1041/2024":
            norma_vigente += " (PPCUB) "
            url_completa = linkppcub + codigo_parametro
            st.markdown(f'**Parâmetro**: <a href="{url_completa}" target="_blank">{url_completa}</a>', unsafe_allow_html=True)

        elif norma_vigente == "LC 948/2019 alterada pela LC 1007/2022":
            norma_vigente += " (LUOS)"

        st.write(f"**Norma Vigente**: {norma_vigente}")

        # --- Geração automática do link do croqui para Lago Sul e Lago Norte ---
        if nome_ra in ["Lago Sul", "Lago Norte"]:
            end_usual = selected_data.get('end_usual', '')
            if end_usual:
                # Divide o endereço em partes separadas por espaço
                partes = end_usual.split()

                # Garante que há pelo menos 3 partes (ex: SHIN QI 7 CJ 16 LT 8)
                if len(partes) >= 3:
                    var1 = partes[0]  # SHIN, SHIS etc.
                    var2 = partes[1]  # QI, QL, QE...
                    var3 = partes[2]  # número da quadra

                    # Procura o índice do "CJ" e captura o número do conjunto
                    cj_index = None
                    for i, p in enumerate(partes):
                        if p == "CJ":
                            cj_index = i
                            break

                    if cj_index is not None and cj_index + 1 < len(partes):
                        var4 = partes[cj_index + 1]  # número do conjunto
                        url_padrao = f"https://www.geoservicos.ide.df.gov.br/anexos/CROQUIS/{var1}_{var2}_{var3}_CJ_{var4}.pdf"
                        st.markdown(f"**Lago Sul ou Lago Norte - Croqui dos Afastamentos:** [Abrir croqui]({url_padrao})")
                    else:
                        st.info("Não foi possível identificar o conjunto (CJ) no endereço usual.")
                else:
                    st.info("Endereço usual não está no formato esperado para gerar o croqui.")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Latitude:** {selected_data.get('latitude', 'N/A')}")

        with col2:
            st.write(f"**Longitude:** {selected_data.get('longitude', 'N/A')}")

        link_google_maps = f"https://www.google.com/maps?q={selected_data.get('latitude', 'N/A')},{selected_data.get('longitude', 'N/A')}"
        st.write(f"[🗺️ Abrir no Google Maps 🗺️]({link_google_maps})", unsafe_allow_html=True)
        st.divider()

        ################## script para gerar invasão de área pública
        # 1º - Lista de RAs para pesquisa
        ras_lista = [
            "Guará",
            "Samambaia",
            "Ceilândia",
            "Gama",
            "Taguatinga",
            "Lago Sul",
            "Lago Norte",
            "Cruzeiro",
            "Núcleo Bandeirante",
            "Paranoá",
            "Park Way",
            "Brazlândia",
            "Planaltina",
            "Riacho Fundo I",
            "Riacho Fundo II",
            "Sobradinho"
        ]

        # Textos associados (por enquanto só 2 exemplos)
        textos_por_ra = {
        "Guará": """**Lei n° 249/1992** - Não foi promulgada pelo governador mas teve sanção tácita pela Câmara Legislativa (ESTÁ VIGENTE) \n Autoriza a construção de cobertura e fechamento com grades  as áreas verdes frontais aos lotes residenciais do Guará.\n - Para lotes com área de 90m², 120m² e 200m², fica autorizado cercar com grades as áreas verdes frontais, laterais e posteriores, limítrofes ao imóvel.\n - A área frontal poderá ser coberta para utilização como garagem ou varanda, vedando-se o seu fechamento como cômodo do imóvel.\n - A cerca frontal ao lote não poderá ultrapassar a linha demarcatória do passeio público.""",
        "Samambaia": """**Lei n° 1096/1996** \n - Autoriza o proprietário de lote de terreno localizado na Região Administrativa de Samambaia a realizar o fechamento com grades das áreas frontais, laterais e posteriores limítrofes aos imóveis. \n - As áreas frontais e laterais poderão ser cobertas em até cinquenta por cento para utilização, exclusivamente, como garagem ou varanda. \n - A grade frontal do lote de terreno é limitada à linha demarcatória do passeio público. \n - A grade de área lateral do terreno de esquina não poderá superar a distância de 3m de afastamento do imóvel, respeitando-se o limite da linha demarcatória do passeio público. \n - As áreas posteriores dos lotes poderão ter utilização diversa da especificada no § 1° deste artigo, respeitada a regulamentação específica a ser baixada pelo órgão competente do Governo do Distrito Federal. \n - É vedado o desmembramento das áreas citadas nesta Lei do seu lote principal, ficando proibida a sua transformação em unidade autônoma de lote de terreno. """,
        "Ceilândia": """**Lei n°1079/1996** \n - P SUL E P NORTE \n - Autoriza o fechamento com grades e a construção de cobertura das áreas verdes frontais e laterais dos Setores P Sul e P Norte da Região Administrativa de Ceilândia. \n - A área frontal pode ser coberta para utilização como garagem ou varanda, vedado seu fechamento para constituir cômodo do imóvel. \n - As cercas frontais e laterais não podem ultrapassar a linha demarcatória do passeio público. \n - QNM - Lei n° 1520/1997 - julgada inconstitucional ADI. """,
        "Gama": """**Lei n° 858/1995** \n - Autoriza o fechamento com grades das áreas verdes de frente, dos fundos e das laterais limítrofes ao imóvel dos lotes residenciais da Região Administrativa do Gama. \n - A área frontal não poderá ultrapassar a linha demarcatória do passeio público. \n - A cerca da área lateral não poderá ultrapassar o limite de 03 (três) metros de afastamento do imóvel de acordo com limites estabelecidos pela Administração Regional. \n - A área cercada poderá ser utilizada pelo proprietário, vedando-se seu fechamento como cômodo, destinando, no mínimo 50% (cinquenta por cento) da mesma para área verde. """,
        "Taguatinga": """**Leis n° 1597/1997; LC n° 192/1999; Lei n° 965/1995** - todas julgadas inconstitucionais ADI. """,
        "Lago Sul": """**LC n° 1055/2025** \n - Autoriza a concessão de direito real de uso para ocupação de áreas públicas intersticiais contíguas aos lotes (becos) destinados ao uso residencial das Unidades de Uso e Ocupação do Solo - UOS RE 1 previstas na Lei Complementar nº 948, de 16 de janeiro de 2019, localizados nas Regiões Administrativas do Lago Sul e do Lago Norte. \n - Para efeito de aplicação desta Lei Complementar, consideram-se contíguas as áreas públicas intersticiais restritas ao espaço situado entre as dimensões dos lotes do mesmo conjunto, indicadas no Anexo I desta Lei Complementar. \n - A concessão de que trata o caput se dá para as ocupações comprovadamente existentes até a data da publicação desta Lei Complementar. \n - A concessão de direito real de uso de que trata esta Lei Complementar é vedada, ou condicionada ao atendimento de condicionantes previstas em regulamento, quando a área pública for imprescindível para: \n I - garantir o acesso de pedestres a equipamentos públicos comunitários, áreas comerciais e institucionais, \n bem como paradas de transporte coletivo; \n II - garantir a circulação para rotas acessíveis; \n III - acessar as redes de infraestrutura e demais equipamentos urbanos existentes; e \n IV - evitar sobreposição aos espaços definidos como Áreas de Preservação Permanente - APP. \n\n - Lei n° 1519/1997 - julgada inconstitucional ADI. """,
        "Lago Norte": """**LC n° 1055/2025** \n - Autoriza a concessão de direito real de uso para ocupação de áreas públicas intersticiais contíguas aos lotes (becos) destinados ao uso residencial das Unidades de Uso e Ocupação do Solo - UOS RE 1 previstas na Lei Complementar nº 948, de 16 de janeiro de 2019, localizados nas Regiões Administrativas do Lago Sul e do Lago Norte. \n - Para efeito de aplicação desta Lei Complementar, consideram-se contíguas as áreas públicas intersticiais restritas ao espaço situado entre as dimensões dos lotes do mesmo conjunto, indicadas no Anexo I desta Lei Complementar. \n - A concessão de que trata o caput se dá para as ocupações comprovadamente existentes até a data da publicação desta Lei Complementar. \n - A concessão de direito real de uso de que trata esta Lei Complementar é vedada, ou condicionada ao atendimento de condicionantes previstas em regulamento, quando a área pública for imprescindível para: \n I - garantir o acesso de pedestres a equipamentos públicos comunitários, áreas comerciais e institucionais, \n bem como paradas de transporte coletivo; \n II - garantir a circulação para rotas acessíveis; \n III - acessar as redes de infraestrutura e demais equipamentos urbanos existentes; e \n IV - evitar sobreposição aos espaços definidos como Áreas de Preservação Permanente - APP. \n\n - Lei n° 1519/1997 - julgada inconstitucional ADI. """,
        "Cruzeiro": """**Lei n° 1063/1996** - julgada inconstitucional ADI. """,
        "Núcleo Bandeirante": """**Lei n° 533/1993** \n - Não foi promulgada pelo governador mas teve sanção tácita pela Câmara Legislativa (ESTÁ VIGENTE) - Autoriza o fechamento com grades aos lotes residenciais da Região Administrativa VIII - Núcleo Bandeirante. \n - O proprietário ao utilizar-se dos benefícios desta Lei, deverá observar os seguintes aspectos: \n I - as melhorias permitidas se limitam a construção de varanda e garagem; \n II - deverá ser respeitada a linha demarcatória do passeio público; \n III - a utilização da área verde lateral não poderá se estender a 03 (três) metros de afastamento do imóvel. """,
        "Paranoá": """**Lei n° 1924/1998** - julgada inconstitucional ADI. """,
        "Park Way": """**Lei n° 1519/1997** - julgada inconstitucional ADI. """,
        "Brazlândia": """**Lei n° 1055/1996** \n - Autoriza o cercamento e a cobertura parcial das áreas verdes em lotes residenciais das Regiões Administrativas de Brazlândia (RA IV) e Planaltina (RA VI). \n - A área permitida para cercamento com grades obedecerá à distância mínima de 1,50m (um metro e cinquenta centímetros) do passeio público e de, no máximo, 3m (três metros) na lateral, para lotes de esquina, respeitada a distância estabelecida para o passeio público, bem como o limite de 2,50m (dois metros e cinquenta centímetros) de altura. \n - As áreas autorizadas para cercamento com grade poderão ser cobertas em até 50% (cinquenta por cento) para utilização como garagem ou varanda, vedado o seu fechamento para ampliação ou construção de cômodo adicional da edificação. """,
        "Planaltina": """**Lei n° 1055/1996** \n - Autoriza o cercamento e a cobertura parcial das áreas verdes em lotes residenciais das Regiões Administrativas de Brazlândia (RA IV) e Planaltina (RA VI). \n - A área permitida para cercamento com grades obedecerá à distância mínima de 1,50m (um metro e cinquenta centímetros) do passeio público e de, no máximo, 3m (três metros) na lateral, para lotes de esquina, respeitada a distância estabelecida para o passeio público, bem como o limite de 2,50m (dois metros e cinquenta centímetros) de altura. \n - As áreas autorizadas para cercamento com grade poderão ser cobertas em até 50% (cinquenta por cento) para utilização como garagem ou varanda, vedado o seu fechamento para ampliação ou construção de cômodo adicional da edificação. """,
        "Riacho Fundo I": """**Lei n° 1152/1996** \n Autoriza os proprietários de lotes residenciais da Região Administrativa do Riacho Fundo a cercar com grades as áreas verdes laterais e frontais dos imóveis, observadas as seguintes condições: \n I - seja respeitada a linha demarcatória do passeio público; \n II - as melhorias se limitem ao uso da área como garagem ou varanda; \n III - estejam instalados os equipamentos urbanos de: \n a) abastecimento de água; \n b) serviços de esgoto; \n c) coleta de águas pluviais; \n d) energia elétrica; \n e) rede telefônica. \n Nenhuma cerca poderá ir além de três metros do imóvel. """,
        "Riacho Fundo II": """**Lei n° 1152/1996** \n - Autoriza os proprietários de lotes residenciais da Região Administrativa do Riacho Fundo a cercar com grades as áreas verdes laterais e frontais dos imóveis, observadas as seguintes condições: \n I - seja respeitada a linha demarcatória do passeio público; \n II - as melhorias se limitem ao uso da área como garagem ou varanda; \n III - estejam instalados os equipamentos urbanos de: \n a) abastecimento de água; \n b) serviços de esgoto; \n c) coleta de águas pluviais; \n d) energia elétrica; \n e) rede telefônica. \n Nenhuma cerca poderá ir além de três metros do imóvel. """,
        "Sobradinho": """**Lei n° 1902/1998** - julgada inconstitucional ADI. """,
        }



        # Simulando o dado vindo do sistema
        # RA vinda do sistema
        


        ras_nome = nome_ra.strip() if nome_ra else ""



        if ras_nome in ras_lista:
            st.write("**---- Área pública contígua ao lote ----**")
            st.write(f"**Região selecionada:** {ras_nome or 'Não informada'}")
            if st.button("Legislação Aplicável"):
                texto = textwrap.dedent(
                    textos_por_ra.get(
                        ras_nome,
                        "Há legislação específica para esta Região Administrativa, porém o texto ainda não foi cadastrado no sistema."
                    )
                )
                st.write(texto)
            st.divider()

        




        ################## certidão dos parâmetros
        # Mostrar os resultados gerais
        if st.session_state.all_general_data:
            st.write(" ---- **Certidão dos Parâmetros Urbanísticos** ---- ")
            
            for idx, result in enumerate(st.session_state.all_general_data):
                with st.container():
                    st.write(f"**Resultado {idx + 1}**")
                    st.write("Atenção: Não é possível Gerar Certidão para os lotes localizados no PPCUB")
                    # Botão para gerar certidão - só aparece se houver CIPU
                    if result['cipu'] != 'N/A':
                        if st.button(f"Gerar Certidão para CIPU {result['cipu']}", key=f"cert_{result['cipu']}_{idx}"):
                            st.info("Enviando requisição...  - **Pode demorar até 10 segundos**")
                            
                            url_submit = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Geoprocessing/certidaoparametrosurb/GPServer/certidao_parametros_urb/submitJob"
                            payload = {"codigo": str(result['cipu']), "f": "json"}

                            
                            try:
                                response = requests.post(url_submit, data=payload)
                                response.raise_for_status()
                                res_json = response.json()
                            except Exception as e:
                                st.error(f"Erro ao enviar requisição: {e}")
                                st.stop()
                            
                            # Restante do código de processamento da certidão...
                            job_id = res_json.get("jobId")
                            if not job_id:
                                st.error("Job ID não retornado.")
                                st.stop()
                            
                            status_url = f"https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Geoprocessing/certidaoparametrosurb/GPServer/certidao_parametros_urb/jobs/{job_id}?f=json"
                            while True:
                                status_resp = requests.get(status_url).json()
                                job_status = status_resp.get("jobStatus", "")
                                if job_status == "esriJobSucceeded":
                                    break
                                elif job_status in ["esriJobFailed", "esriJobCancelled"]:
                                    st.error("Job falhou ou foi cancelado.")
                                    st.stop()
                                time.sleep(2)
                            
                            job_info = requests.get(status_url).json()
                            pdf_url = None
                            
                            if "results" in job_info:
                                for key, val in job_info["results"].items():
                                    if key == "arquivo":
                                        result_url = f"https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Geoprocessing/certidaoparametrosurb/GPServer/certidao_parametros_urb/jobs/{job_id}/{val['paramUrl']}?f=json"
                                        result = requests.get(result_url).json()
                                        value = result.get("value")

                                        # Se for link direto (caso da certidão), usa como está
                                        if value and value.startswith("http"):
                                            file_url = value
                                        # Se for apenas o nome do arquivo, monta a URL no diretório correto do job
                                        elif value:
                                            file_url = f"https://www.geoservicos.ide.df.gov.br/arcgis/rest/directories/arcgisjobs/geoprocessing/certidaoparametrosurb_gpserver/{job_id}/scratch/{value}"
                                        else:
                                            file_url = None

                            if not file_url:
                                st.warning("Link do arquivo não encontrado.")
                                st.stop()


                            st.write("Arquivo Gerado")
                            st.markdown(f"[🧾 Clique aqui para baixar 🧾]({file_url})", unsafe_allow_html=True)







        #################################
        





    # --- Botão para carregar Detalhes LUOS ---
    if selected_cipu != 'N/A':
        if st.button("  **Carregar LUOS**  "):
            st.session_state.show_luos_data = True
            if selected_cipu not in st.session_state.luos_data_map:
                st.info(f"Buscando dados LUOS para CIPU {selected_cipu}...")
                where_clause_luos = f"lu_cipu = {int(selected_cipu)}"
                api_url_LUOS = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/LUOS/MapServer/11/query"
                params_LUOS = {
                    "where": where_clause_luos,
                    "outFields": "lu_area_proj,lu_cfa_b,lu_cfa_m,lu_tx_ocu,lu_tx_perm,lu_alt_max,lu_afr,lu_afu,lu_aft_lat_dir,lu_aft_lat_esq,lu_aft_obs,lu_marquise,lu_galeria,lu_cota_sol,lu_notas,lu_subsol,lu_cipu",
                    "returnGeometry": "false",
                    "f": "json"
                }
                try:
                    response_LUOS = requests.get(api_url_LUOS, params=params_LUOS)
                    response_LUOS.raise_for_status()
                    data_LUOS = response_LUOS.json()
                    if data_LUOS.get("features"):
                        st.session_state.luos_data_map[selected_cipu] = data_LUOS["features"][0]["attributes"]
                    else:
                        st.session_state.luos_data_map[selected_cipu] = None
                except requests.RequestException as e:
                    st.warning(f"Erro ao buscar dados LUOS para CIPU {selected_cipu}: {e}")
                    st.session_state.luos_data_map[selected_cipu] = None
                st.rerun() # Recarregar para exibir os dados LUOS

    # --- Detalhes LUOS (Exibir apenas se o botão foi clicado e dados existem) ---
    if st.session_state.show_luos_data:
        luos_attrs = st.session_state.luos_data_map.get(selected_cipu)
        if luos_attrs:
            with st.expander(f"**Detalhes LUOS**", expanded=True): # Começa expandido quando carregado
                # Função auxiliar para tratar None e retornar 0 para numéricos
                def get_numeric_value(data_dict, key):
                    value = data_dict.get(key)
                    return value if value is not None else 0

                st.write(f"**Área de Projeto (m²)**: {get_numeric_value(luos_attrs, 'lu_area_proj')}")
                st.write(f"**Coef. de aprov. básico**: {get_numeric_value(luos_attrs, 'lu_cfa_b')}")
                st.write(f"**Coef. aprov. máximo**: {get_numeric_value(luos_attrs, 'lu_cfa_m')}")
                st.write(f"**Taxa de ocupação**: {get_numeric_value(luos_attrs, 'lu_tx_ocu')}")
                st.write(f"**Taxa de permeabilidade**: {get_numeric_value(luos_attrs, 'lu_tx_perm')}")
                st.write(f"**Altura máxima (m)**: {get_numeric_value(luos_attrs, 'lu_alt_max')}")
                
                # Afastamentos
                st.write(f"**Afast. de frente (m)**: {get_numeric_value(luos_attrs, 'lu_afr')}")
                st.write(f"**Afast. de fundo (m)**: {get_numeric_value(luos_attrs, 'lu_afu')}")
                st.write(f"**Afast. lat. direito (m)**: {get_numeric_value(luos_attrs, 'lu_aft_lat_dir')}")
                st.write(f"**Afast. lat. esquerdo (m)**: {get_numeric_value(luos_attrs, 'lu_aft_lat_esq')}")
                st.write(f"**Obs. de afastamento (m)**: {get_numeric_value(luos_attrs, 'lu_aft_obs')}")
                
                # Mapeamento para lu_marquise
                marquise_map = {
                    0: "Não Informado",
                    1: "Obrigatório",
                    2: "Proibido",
                    3: "Não Se Aplica",
                    4: "Optativo",
                    5: "Definido em Estudo Específico",
                    6: "Sujeito a Aplicação Para Uso Residencial",
                    7: "Sujeito a Aplicação (ver Exceção)",
                    8: "Permitido Tipo 1",
                    9: "Permitido Tipo 2"
                }
                marquise_codigo = luos_attrs.get('lu_marquise')
                marquise_texto = marquise_map.get(marquise_codigo, 'N/A')
                st.write(f"**Marquise em área pública**: {marquise_texto}")

                # Mapeamento para lu_galeria
                galeria_map = {
                    0: "Não",
                    1: "Sim"
                }
                galeria_codigo = luos_attrs.get('lu_galeria')
                galeria_texto = galeria_map.get(galeria_codigo, 'N/A')
                st.write(f"**Galeria**: {galeria_texto}")

                # Mapeamento para lu_cota_sol
                cota_sol_map = {
                    0: "Não Informado",
                    1: "Cota Altimétrica Média Do Lote",
                    2: "Ponto Médio Da Edificação",
                    3: "Ponto Médio Da Testada Frontal"
                }
                cota_sol_codigo = luos_attrs.get('lu_cota_sol')
                cota_sol_texto = cota_sol_map.get(cota_sol_codigo, 'N/A')
                st.write(f"**Cota de soleira**: {cota_sol_texto}")

                # Mapeamento para lu_notas
                notas_map = {
                    0: "Não",
                    1: "Sim"
                }
                notas_codigo = luos_attrs.get('lu_notas')
                notas_texto = notas_map.get(notas_codigo, 'N/A')
                st.write(f"**Notas específicas**: {notas_texto}")
                
                # Mapeamento para lu_subsol
                subsol_map = {
                    0: "Não Informado",
                    1: "Obrigatório",
                    2: "Proibido",
                    3: "Não Se Aplica",
                    4: "Optativo",
                    5: "Definido em Estudo Específico",
                    6: "Sujeito a Aplicação Para Uso Residencial",
                    7: "Sujeito a Aplicação (ver Exceção)",
                    8: "Permitido Tipo 1",
                    9: "Permitido Tipo 2"
                }
                subsol_codigo = luos_attrs.get('lu_subsol')
                subsol_texto = subsol_map.get(subsol_codigo, 'N/A')
                st.write(f"**Subsolo**: {subsol_texto}")

                # Cálculos de área
                area_lote = get_numeric_value(luos_attrs, 'lu_area_proj')
                coeficiente_basico = get_numeric_value(luos_attrs, 'lu_cfa_b')
                coeficiente_maximo = get_numeric_value(luos_attrs, 'lu_cfa_m')
                taxa_ocupacao = get_numeric_value(luos_attrs, 'lu_tx_ocu')
                taxa_permeabilidade = get_numeric_value(luos_attrs, 'lu_tx_perm')

                try:
                    area_lote_float = float(area_lote)
                    coeficiente_basico_float = float(coeficiente_basico)
                    coeficiente_maximo_float = float(coeficiente_maximo)
                    taxa_ocupacao_float = float(taxa_ocupacao)
                    taxa_permeabilidade_float = float(taxa_permeabilidade)

                    st.info(f"""
                    **📐 Cálculos automáticos**

                    **Área básica de construção (m²):** {area_lote_float * coeficiente_basico_float:.2f}  
                    **Área máxima de construção (m²):** {area_lote_float * coeficiente_maximo_float:.2f}  
                    **Taxa de ocupação máxima (m²):** {area_lote_float * (taxa_ocupacao_float/100):.2f}  
                    **Área permeável mínima (m²):** {area_lote_float * (taxa_permeabilidade_float/100):.2f}
                    """)

                except (ValueError, TypeError):
                    st.warning("Não foi possível calcular as áreas de construção e permeabilidade devido a valores inválidos.")
        else:
            st.warning(f"Nenhum dado LUOS encontrado para este CIPU: {selected_cipu}.")
    
    ##########################
    # --- Botão para carregar Informações de Normas ---
    if selected_cipu != 'N/A':
        if st.button("**Carregar Norma Anterior - NGBs**"):
            st.session_state.show_normas_data = True
            st.session_state.show_normas_data2 = True
            if selected_cipu not in st.session_state.normas_data_map:
                st.info(f"Buscando informações de Normas para CIPU {selected_cipu}...")
                where_clause_normas = f"pn_cipu = {int(selected_cipu)}"
                cipu_utilizado = f"qd_cipu = {int(selected_cipu)}"
                api_url_normas = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/18/query"
                api_url_normas2 = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/17/query"
                params_normas = {
                    "where": where_clause_normas,
                    "outFields": "pn_uos_par,pn_uso,pn_tx_ocu,pn_cfa_b,pn_cfa_m,pn_alt_max,pn_tx_perm,pn_cota_sol,pn_subsol,pn_notas,pn_afr,pn_afu,pn_aft_lat_dir,pn_aft_lat_esq,pn_aft_obs,pn_marquise",
                    "returnGeometry": "false",
                    "f": "json"
                }
                params_normas2 = {
                    "where": cipu_utilizado,
                    "outFields": "qd_area",
                    "returnGeometry": "false",
                    "f": "json"
                }
                

                try:
                    response_normas = requests.get(api_url_normas, params=params_normas)
                    response_normas.raise_for_status()
                    data_normas = response_normas.json()
                    if data_normas.get("features"):
                        st.session_state.normas_data_map[selected_cipu] = data_normas["features"][0]["attributes"]
                    else:
                        st.session_state.normas_data_map[selected_cipu] = None
                except requests.RequestException as e:
                    st.warning(f"Erro ao buscar informações de Normas para CIPU {selected_cipu}: {e}")
                    st.session_state.normas_data_map[selected_cipu] = None

                try:
                    response_normas2 = requests.get(api_url_normas2, params=params_normas2)
                    response_normas2.raise_for_status()
                    data_normas2 = response_normas2.json()
                    if data_normas2.get("features"):
                        st.session_state.normas_data_map2[selected_cipu] = data_normas2["features"][0]["attributes"]
                    else:
                        st.session_state.normas_data_map2[selected_cipu] = None
                except requests.RequestException as e:
                    st.warning(f"Erro ao buscar informações de Normas para CIPU {selected_cipu}: {e}")
                    st.session_state.normas_data_map2[selected_cipu] = None
                st.rerun()



    # --- Exibir Informações de Normas ---
    if st.session_state.show_normas_data:
        normas_attrs = st.session_state.normas_data_map.get(selected_cipu)
        normas_attrs2 = st.session_state.normas_data_map2.get(selected_cipu)



        # Criamos a função get_value2 fora do expander para ser acessível
        def get_value2(val2):
            return val2 if val2 is not None else "N/A"
        if normas_attrs:
            with st.expander("**Informações de Normas**", expanded=True):
                def get_value(val):
                    return val if val is not None else "N/A"
                st.write(f"**Uso**: {get_value(normas_attrs.get('pn_uso'))}")
                st.write(f"**Código do Parâmetro**: {get_value(normas_attrs.get('pn_cod_par'))}")
                st.write(f"**Coeficiente de aproveitamento básico**: {get_value(normas_attrs.get('pn_cfa_b'))}")
                st.write(f"**Coeficiente de aproveitamento máximo**: {get_value(normas_attrs.get('pn_cfa_m'))}")
                st.write(f"**Taxa de ocupação (%)**: {get_value(normas_attrs.get('pn_tx_ocu'))}")
                st.write(f"**Taxa de permeabilidade (%)**: {get_value(normas_attrs.get('pn_tx_perm'))}")
                st.write(f"**Altura máxima (m)**: {get_value(normas_attrs.get('pn_alt_max'))}")


                # Mapeamento para cota de soleira
                cota_sol_map2 = {
                    0: "Não Informado",
                    1: "Cota Altimétrica Média Do Lote",
                    2: "Ponto Médio Da Edificação",
                    3: "Ponto Médio Da Testada Frontal"
                }
                cota_sol_codigo2 = normas_attrs.get('pn_cota_sol')
                cota_sol_texto2 = cota_sol_map2.get(cota_sol_codigo2, 'N/A')
                st.write(f"**Cota de soleira**: {cota_sol_texto2}")


                # Mapeamento para lu_subsol
                subsol_map2 = {
                    0: "Não Informado",
                    1: "Obrigatório",
                    2: "Proibido",
                    3: "Não Se Aplica",
                    4: "Optativo",
                    5: "Definido em Estudo Específico",
                    6: "Sujeito a Aplicação Para Uso Residencial",
                    7: "Sujeito a Aplicação (ver Exceção)",
                    8: "Permitido Tipo 1",
                    9: "Permitido Tipo 2"
                }
                subsol_codigo2 = normas_attrs.get('pn_subsol')
                subsol_texto2 = subsol_map2.get(subsol_codigo2, 'N/A')
                st.write(f"**Subsolo**: {subsol_texto2}")
 
                # Mapeamento para notas
                notas_map2 = {
                    0: "Não",
                    1: "Sim"
                }
                notas_codigo2 = normas_attrs.get('pn_notas')
                notas_texto2 = notas_map2.get(notas_codigo2, 'N/A')
                st.write(f"**Notas específicas**: {notas_texto2}")

                st.write(f"**Afastamento frente (m)**: {get_value(normas_attrs.get('pn_afr'))}")
                st.write(f"**Afastamento fundo (m)**: {get_value(normas_attrs.get('pn_afu'))}")
                st.write(f"**Afastamento lateral direito (m)**: {get_value(normas_attrs.get('pn_aft_lat_dir'))}")
                st.write(f"**Afastamento lateral esquerdo (m)**: {get_value(normas_attrs.get('pn_aft_lat_esq'))}")
                st.write(f"**Observações afastamento**: {get_value(normas_attrs.get('pn_aft_obs'))}")

                # Mapeamento para lu_marquise marquise
                marquise_map2 = {
                    0: "Não Informado",
                    1: "Obrigatório",
                    2: "Proibido",
                    3: "Não Se Aplica",
                    4: "Optativo",
                    5: "Definido em Estudo Específico",
                    6: "Sujeito a Aplicação Para Uso Residencial",
                    7: "Sujeito a Aplicação (ver Exceção)",
                    8: "Permitido Tipo 1",
                    9: "Permitido Tipo 2"
                }
                marquise_codigo2 = normas_attrs.get('pn_marquise')
                marquise_texto2 = marquise_map2.get(marquise_codigo2, 'N/A')
                st.write(f"**Marquise em área pública**: {marquise_texto2}")

                        # do 17 aqui   
                
                
                if normas_attrs2:

                    #st.write(f"**Dimensão de frente**: {get_value2(normas_attrs2.get('qd_dim_frente'))}")
                    #st.write(f"**Dimensão de fundo**: {get_value2(normas_attrs2.get('qd_dim_fundo'))}")
                    #st.write(f"**Dimensão do chanfro**: {get_value2(normas_attrs2.get('qd_dim_chanfro'))}")
                    def to_float_or_zero(value):
                        try:
                            return float(value)
                        except (TypeError, ValueError):
                            return 0.0
                    st.write(f"**Dimensão de Frente:** {selected_data.get('dimensao_frente', 'N/A')}")
                    st.write(f"**Dimensão de Fundo:** {selected_data.get('dimensao_fundo', 'N/A')}")
                    st.write(f"**Dimensão Lateral Direita:** {selected_data.get('dimensao_direita', 'N/A')}")
                    st.write(f"**Dimensão Lateral Esquerda:** {selected_data.get('dimensao_esquerda', 'N/A')}")
                    st.write(f"**Dimensão Chanfro:** {selected_data.get('dimensao_chanfro', 'N/A')}")
                    st.write(f"**Área do projeto (m²)**: {get_value2(normas_attrs2.get('qd_area'))}")             

                    ngb_area = get_value2(normas_attrs2.get('qd_area'))
                    ngb_coeficiente_basico = get_value(normas_attrs.get('pn_cfa_b'))
                    ngb_coeficiente_maximo = get_value(normas_attrs.get('pn_cfa_m'))
                    ngb_taxa_ocupacao = get_value(normas_attrs.get('pn_tx_ocu'))
                    ngb_taxa_permeabilidade = get_value(normas_attrs.get('pn_tx_perm'))

                    # Conversão segura para float
                    area_lote_float2 = to_float_or_zero(ngb_area)
                    coeficiente_basico_float2 = to_float_or_zero(ngb_coeficiente_basico)
                    coeficiente_maximo_float2 = to_float_or_zero(ngb_coeficiente_maximo)
                    taxa_ocupacao_float2 = to_float_or_zero(ngb_taxa_ocupacao)
                    taxa_permeabilidade_float2 = to_float_or_zero(ngb_taxa_permeabilidade)

                    st.info(f"""
                    **📐 Cálculos automáticos**
                            
                    **Área básica de construção (m²):** {area_lote_float2 * coeficiente_basico_float2:.2f}  
                    **Área máxima de construção (m²):** {area_lote_float2 * coeficiente_maximo_float2:.2f}  
                    **Taxa de ocupação máxima (m²):** {area_lote_float2 * (taxa_ocupacao_float2/100):.2f}  
                    **Área permeável mínima (m²):** {area_lote_float2 * (taxa_permeabilidade_float2/100):.2f}
                    """)
        else:
            st.warning(f"Nenhuma informação de Normas encontrada para CIPU {selected_cipu}.")


                
    
    # # # # # # # # # # # # 
    # Supondo que 'selected_cipu' seja a variável com o valor de entrada (CIPU/CIU).
    if selected_cipu != 'N/A':

        # ---- CLICOU NO BOTÃO → ativa o estado ----
        if st.button("**Carregar Cotas de Soleira**"):
            st.session_state.show_cota_soleira_data = True

        # ---- SÓ RODA SE O ESTADO ESTIVER ATIVO ----
        if st.session_state.get("show_cota_soleira_data", False):

            api_url = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Aplicacoes/COTA_SOLEIRA/MapServer/0/query"
            cotas_encontradas = []

            # --- TENTATIVA 1: Buscar por CIPU ---
            st.info("Tentando buscar por CIPU...")
            try:
                params_cipu = {
                    "where": f"cs_cipu = {int(selected_cipu)}",
                    "outFields": "cs_cota, cs_link, cs_cipu, cs_ciu",
                    "returnGeometry": "false",
                    "f": "json"
                }
                response = requests.get(api_url, params=params_cipu)
                response.raise_for_status()
                data = response.json()
                if data.get("features"):
                    cotas_encontradas = [f["attributes"] for f in data["features"]]
            except Exception as e:
                st.warning(f"Erro na busca por CIPU: {e}")

            # --- TENTATIVA 2 ---
            if not cotas_encontradas:
                ciu_value = selected_data.get('ciu', '').strip()
                st.info("Nenhum resultado para CIPU. Tentando buscar por CIU...")
                if ciu_value:
                    try:
                        params_ciu = {
                            "where": f"cs_ciu = '{ciu_value}'",
                            "outFields": "cs_cota, cs_link, cs_cipu, cs_ciu",
                            "returnGeometry": "false",
                            "f": "json"
                        }
                        response = requests.get(api_url, params=params_ciu)
                        response.raise_for_status()
                        data = response.json()
                        if data.get("features"):
                            cotas_encontradas = [f["attributes"] for f in data["features"]]
                    except Exception as e:
                        st.warning(f"Erro na busca por CIU: {e}")

            # --- Salva no cache ---
            st.session_state.cota_soleira_data_map[selected_cipu] = cotas_encontradas

            # ---- EXIBE ----
            if cotas_encontradas:
                st.success(f"Encontradas {len(cotas_encontradas)} cota(s) de soleira para o lote.")
                for idx, cota in enumerate(cotas_encontradas, start=1):
                    st.markdown(f"**Cota {idx}:** {cota.get('cs_cota', 'N/A')}")
                    link = cota.get("cs_link")
                    if link:
                        st.markdown(f"[📄 Ver Documento]({link})")
                    else:
                        st.markdown("⚠️ **Não tem LINK desse documento no GeoPortal**")
                    st.markdown("---")
            else:
                st.warning("Nenhuma cota de soleira encontrada para este lote.")

    # --- Botão para carregar o Mapa ---
    if st.button("**Carregar Mapa**"):
        st.session_state.show_map = True

    # --- Exibir o mapa Folium (Exibir apenas se o botão foi clicado) ---
    if st.session_state.show_map:
        st.subheader("Localização no Mapa")

        # Obtém os dados do resultado selecionado
        selected_data = st.session_state.all_general_data[st.session_state.selected_feature_index]
        selected_coords = st.session_state.map_coords_list[st.session_state.selected_feature_index] if st.session_state.map_coords_list else None
        
        # Define o centro do mapa com base no polígono ou na coordenada do marcador
        center_coords = selected_coords if selected_coords else [-15.7797, -47.9297]  # Centro de Brasília como fallback

        # Cria o mapa base (satélite)
        m = folium.Map(location=center_coords, zoom_start=19, tiles="Esri.WorldImagery", max_zoom=21)

        # Adiciona a camada WMS dos lotes (desligada por padrão)
        folium.raster_layers.WmsTileLayer(
            url="https://www.geoservicos.ide.df.gov.br/arcgis/services/Publico/CADASTRO_TERRITORIAL/MapServer/WMSServer",
            name="Lotes Registrados",
            layers="6",
            fmt="image/png",
            transparent=True,
            max_zoom=23,
            attr="GDF / GeoServiços",
            show=False  # Desligado por padrão
        ).add_to(m)


        # Adiciona a 2021_50CM
        wms_layer = folium.raster_layers.WmsTileLayer(
            url="https://www.geoservicos.ide.df.gov.br/arcgis/services/Imagens/2021_50CM/ImageServer/WMSServer",
            name="2021 - GeoPortal",
            layers="0",
            fmt="image/png",
            transparent=True,
            max_zoom=23,
            attr="IDE-DF / GeoServiços",
            show=False  # Mude para True se quiser que carregue por padrão
        )
        wms_layer.add_to(m)

        # Adiciona 2016
        wms_layer = folium.raster_layers.WmsTileLayer(
            url="https://www.geoservicos.ide.df.gov.br/arcgis/services/Imagens/FOTO_2016/ImageServer/WMSServer",
            name="2016 - GeoPortal",
            layers="0",
            fmt="image/png",
            transparent=True,
            max_zoom=23,
            attr="IDE-DF / GeoServiços",
            show=False  # Mude para True se quiser que carregue por padrão
        )
        wms_layer.add_to(m)

        # Adiciona 2017
        wms_layer = folium.raster_layers.WmsTileLayer(
            url="https://www.geoservicos.ide.df.gov.br/arcgis/services/Imagens/PLEIADES_2017/ImageServer/WMSServer",
            name="2017 - GeoPortal",
            layers="0",
            fmt="image/png",
            transparent=True,
            max_zoom=23,
            attr="IDE-DF / GeoServiços",
            show=False  # Mude para True se quiser que carregue por padrão
        )
        wms_layer.add_to(m)

        url_template_2022 = (
            "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/44873/{z}/{y}/{x}"
        )
        url_template_2023 = (
            "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/56450/{z}/{y}/{x}"
        )

        folium.TileLayer(
            tiles=url_template_2022,
            attr="World Imagery Wayback 2022",
            name="2022 - Arcgis",
            overlay=True,
            max_zoom=23,
            control=True,
            show=False
        ).add_to(m)

        folium.TileLayer(
            tiles=url_template_2023,
            attr="World Imagery Wayback 2023",
            name="2023 - Arcgis",
            overlay=True,
            max_zoom=23,
            control=True,
            show=False
        ).add_to(m)


        # Adiciona o polígono do lote selecionado
        selected_geometry = selected_data.get("geometry")

        if selected_geometry and selected_geometry.get('rings'):
            # Transforma as coordenadas do polígono de UTM (31983) para Lat/Lon (4326)
            transformed_rings = []
            for ring in selected_geometry.get('rings'):
                transformed_ring = []
                for x, y in ring:
                    lon, lat = transformer.transform(x, y)  # Usa o transformer que você já tem
                    transformed_ring.append([lon, lat])
                transformed_rings.append(transformed_ring)

            # Cria uma feature GeoJSON a partir da geometria convertida
            geojson_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": transformed_rings
                },
                "properties": {
                    "cipu": selected_data.get("cipu"),
                    "ciu": selected_data.get("ciu")
                }
            }
            
            # Texto do pop-up para o polígono
            popup_text = f"""
            <b>CIPU:</b> {selected_data.get("cipu")}<br>
            <b>CIU:</b> {selected_data.get("ciu")}<br>
            """

            # Adiciona o polígono ao mapa com estilo e pop-up
            folium.GeoJson(
                geojson_feature,
                name="Lote Selecionado",
                tooltip="Clique para mais informações",
                popup=folium.Popup(popup_text, max_width=300),
                style_function=lambda feature: {
                    "fillColor": "blue",
                    "color": "red",
                    "weight": 3,
                    "fillOpacity": 0.05
                }
            ).add_to(m)
            
            # Adiciona marcador no centro do polígono (opcional)
            # if selected_coords:
             #    folium.Marker(
              #       location=selected_coords,
               #      icon=folium.Icon(icon="home", color="blue", prefix='fa')
                # ).add_to(m)

        # Adiciona o controle de camadas
        folium.LayerControl().add_to(m)

        # Exibe o mapa no Streamlit
        st_folium(m, width=700, height=500)

        
else:
    pass





# --- Iniciar estado da sessão ---
if 'relatorio_gerado' not in st.session_state:
    st.session_state.relatorio_gerado = False
if 'rampa' not in st.session_state:
    st.session_state.rampa = 'Não'
if 'telhado' not in st.session_state:
    st.session_state.telhado = 'Não'
if 'observacoes_selecionadas' not in st.session_state:
    st.session_state.observacoes_selecionadas = None
if 'texto_livre' not in st.session_state:
    st.session_state.texto_livre = ""

#################################################
with st.expander("**Busca automática nos PDFs do Anexo III - LUOS**", expanded=False):
    
    #st.write("Data: Santa Maria e Minuta Lago Sul = LC1047/2025, restante = LC 1007/2022")
    if st.session_state.get("show_year_selector"):
        st.session_state.selected_year = st.radio(
            "Ano:", ["2022", "2025"], horizontal=True
        )

    # Função para extrair e buscar observação
    def parse_e_busca_observacao(linha_encontrada, df_observacao):
        if linha_encontrada.empty:
            st.warning('Nenhuma linha encontrada para processar.')
            return None

        try:
            valor_uos = linha_encontrada.iloc[0, 1]
            match = re.search(r'\((.*?)\)', str(valor_uos))

            if match:
                numero_observacao = match.group(1).strip()
                df_observacao.iloc[:, 0] = df_observacao.iloc[:, 0].astype(str).str.strip()
                df_observacao.iloc[:, 0] = df_observacao.iloc[:, 0].str.replace(r'\.0$', '', regex=True)

                observacao_encontrada = df_observacao[df_observacao.iloc[:, 0] == numero_observacao]

                if not observacao_encontrada.empty:
                    texto_observacao = ' '.join(
                        str(x) for x in observacao_encontrada.iloc[0, 1:].dropna() if str(x) != 'nan'
                    )
                    return texto_observacao
                else:
                    st.warning(f'Nenhuma observação encontrada para o número: {numero_observacao}')
                    return None
            else:
                return None
        except Exception as e:
            st.error(f"Erro ao processar observação: {e}")
            return None


    # Função para exibir dados organizados
    def exibir_dados_organizados(linha_encontrada):
        if linha_encontrada.empty:
            return
        linha = linha_encontrada.iloc[0].values
        mapeamento_indices = {
            0: 'Código',
            1: 'UOS',
            2: 'Faixa Área(m²)',
            3: 'Coeficiente Básico',
            4: 'Coeficiente Máximo',
            5: 'Taxa de Ocupação (%)',
            6: 'Taxa de permeabilidade (%)',
            7: 'Altura Máxima',
            8: 'Afastamento Frontal',
            9: 'Afastamento Fundos',
            10: 'Afastamento Lateral',
            11: 'Observação do Afastamento',
            12: 'Marquise',
            13: 'Galeria',
            14: 'Cota de Soleira',
            15: 'Subsolo'
        }
        for indice, nome_exibicao in mapeamento_indices.items():
            if indice < len(linha) and pd.notna(linha[indice]) and str(linha[indice]).strip() != '':
                st.write(f"**{nome_exibicao}:** {linha[indice]}")
            else:
                st.write(f"**{nome_exibicao}:** -" )

    def normalizar_texto(txt):
        if txt is None:
            return ""
        txt = str(txt).strip().lower()
        txt = unicodedata.normalize("NFD", txt)
        txt = "".join(ch for ch in txt if unicodedata.category(ch) != "Mn")
        return txt


    # --- Execução principal ---
    if st.session_state.get("all_general_data"):
        resultado = st.session_state.all_general_data[st.session_state.selected_feature_index]

        # 🔹 Garante que o CIPU fique salvo corretamente no estado global
        cipu_valor = resultado.get("cipu") or resultado.get("CIPU") or resultado.get("lu_cipu")
        if cipu_valor:
            st.session_state.selected_cipu = str(cipu_valor).strip()
        else:
            st.warning("⚠️ CIPU não encontrado no resultado inicial.")

        # --- Botão de busca ---
        if st.button("🔍 Buscar", key="buscar_parametros"):
            nome_ra_norm = normalizar_texto(nome_ra)

            regioes_implementadas = [
                "Plano Piloto", "Gama", "Taguatinga", "Brazlândia", "Sobradinho", "Planaltina",
                "Paranoá", "Núcleo Bandeirante", "Ceilândia", "Guará", "Cruzeiro", "Samambaia",
                "Santa Maria", "São Sebastião", "Recanto das Emas", "Lago Sul", "Riacho Fundo",
                "Lago Norte", "Candangolândia", "Águas Claras", "Riacho Fundo II",
                "Sudoeste/Octogonal", "Varjão", "Park Way", "SCIA", "Sobradinho II",
                "Jardim Botânico", "Itapoã", "SIA", "Vicente Pires", "Fercal"
            ]

            regioes_implementadas_norm = [normalizar_texto(r) for r in regioes_implementadas]

            def nome_arquivo_seguro(nome_ra):
                nome = unicodedata.normalize("NFD", nome_ra)
                nome = "".join(ch for ch in nome if unicodedata.category(ch) != "Mn")
                nome = nome.replace(" ", "_")
                return nome

            if nome_ra_norm in regioes_implementadas_norm:
                try:
                    nome_arquivo_base = nome_arquivo_seguro(nome_ra)

                    # -------------------------------------------------------
                    #   🔥 LÓGICA DE SELEÇÃO DE ARQUIVOS POR ANO — FINAL
                    # -------------------------------------------------------

                    ra_duas_normas = ["santa maria", "lago sul"]
                    nome_ra_norm_sem_acento = normalizar_texto(nome_ra)
                    nome_arquivo_base = nome_arquivo_seguro(nome_ra)

                    # CASO 1 — RA COM 2 NORMAS (Santa Maria / Lago Sul)
                    if nome_ra_norm_sem_acento in ra_duas_normas:

                        ano_escolhido = st.session_state.get("selected_year", "2025")

                        if ano_escolhido == "2022":
                            arquivo_lista = f"{nome_arquivo_base}_lista_2022.csv"
                            arquivo_observacao = f"{nome_arquivo_base}_observacao_2022.csv"

                        else:  # 2025
                            arquivo_lista = f"{nome_arquivo_base}_lista.csv"
                            arquivo_observacao = f"{nome_arquivo_base}_observacao.csv"

                    # CASO 2 — RAs NORMAIS (somente 2022)
                    else:
                        ano_escolhido = st.session_state.get("selected_year", "2022")

                        # 🚫 Se o usuário tentar escolher 2025 em uma RA que não tem 2025
                        if ano_escolhido == "2025":
                            st.error("❌ Esta Região Administrativa não possui modificação em 2025.")
                            st.stop()  # impede carregar arquivos e impede a busca

                        # Arquivos padrão sem ano
                        arquivo_lista = f"{nome_arquivo_base}_lista.csv"
                        arquivo_observacao = f"{nome_arquivo_base}_observacao.csv"


                    # DEBUG OPCIONAL
                    #st.write(f"📁 Arquivo lista = {arquivo_lista}")
                    #st.write(f"📁 Arquivo observação = {arquivo_observacao}")


                    # --- Tenta buscar código de parâmetro se estiver vazio ---
                    if not codigo_parametro or str(codigo_parametro).strip().lower() in ["none", "nan", "0", "n/a", ""]:
                        selected_cipu = st.session_state.get("selected_cipu")
                        st.write("🔎 DEBUG: selected_cipu =", selected_cipu)

                        if selected_cipu:
                            st.info(f"Buscando código de parâmetro (LUOS) para CIPU {selected_cipu}...")

                            api_url_LUOS = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/LUOS/MapServer/11/query"
                            params_LUOS = {
                                "where": f"lu_cipu = '{str(selected_cipu).strip()}'",
                                "outFields": "lu_cod_par",
                                "returnGeometry": "false",
                                "f": "json"
                            }

                            try:
                                response_LUOS = requests.get(api_url_LUOS, params=params_LUOS)
                                response_LUOS.raise_for_status()
                                data_LUOS = response_LUOS.json()

                                if data_LUOS.get("features"):
                                    codigo_parametro = data_LUOS["features"][0]["attributes"].get("lu_cod_par")
                                    if codigo_parametro:
                                        st.success(f"Código de parâmetro encontrado automaticamente: {codigo_parametro}")
                                    else:
                                        st.warning("⚠️ Nenhum código de parâmetro retornado pelo serviço LUOS.")
                                else:
                                    st.warning(f"⚠️ Nenhum resultado encontrado no serviço LUOS para CIPU {selected_cipu}.")
                            except Exception as e:
                                st.error(f"Erro ao buscar código de parâmetro no serviço LUOS: {e}")
                        else:
                            st.warning("⚠️ Não foi possível buscar o código: CIPU inválido ou ausente.")

                    st.write(f"**🏙️ Região Administrativa:** {nome_ra or 'N/A'}")
                    st.write(f"**📘 Código do Parâmetro:** {codigo_parametro or 'N/A'}")

                    # --- Carrega e exibe ---
                    df_lista = pd.read_csv(arquivo_lista, sep=';', header=None)
                    df_observacao = pd.read_csv(
                        arquivo_observacao,
                        sep=';',
                        header=None,
                        on_bad_lines='skip',
                        dtype=str
                    )

                    linha_encontrada = df_lista[df_lista.iloc[:, 0].astype(str) == str(codigo_parametro)]

                    if not linha_encontrada.empty:
                        exibir_dados_organizados(linha_encontrada)
                        st.write("**📝 Observação:**")
                        observacao = parse_e_busca_observacao(linha_encontrada, df_observacao)
                        if observacao:
                            st.markdown(observacao)
                        else:
                            st.info("Nenhuma observação encontrada para este parâmetro.")
                    else:
                        st.error(f"❌ Código de parâmetro '{codigo_parametro}' não encontrado nas listas de {nome_ra}.")
                except FileNotFoundError:
                    st.error(f"❌ Arquivo não encontrado. Verifique se '{arquivo_lista}' e '{arquivo_observacao}' existem.")
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro: {e}")
            else:
                st.warning(f"⚠️ Região {nome_ra or 'N/A'} ainda não implementada.")
    else:
        st.info("Primeiro realize a pesquisa do imóvel na etapa anterior para carregar os dados.")



    st.markdown("---")
    st.subheader("Buscar diretamente pelo CIPU")
    st.write("Busca sempre a LUOS atualizada. Data: Santa Maria e Minuta Lago Sul = LC1047/2025, restante = LC 1007/2022")
    # Entrada do CIPU
    cipu_input = st.text_input("Digite o número do CIPU", placeholder="Exemplo: 4515323")

    # Limpeza da entrada (remove espaços, pontos, vírgulas e ponto e vírgula)
    cipu_input = cipu_input.replace(" ", "").replace(".", "").replace(",", "").replace(";", "")

    # Dicionário de RAs (LUOS)
    regioes_administrativas_luos = {
        1: "Plano Piloto",
        2: "Gama",
        3: "Taguatinga",
        4: "Brazlândia",
        5: "Sobradinho",
        6: "Planaltina",
        7: "Paranoá",
        8: "Núcleo Bandeirante",
        9: "Ceilândia",
        10: "Guará",
        11: "Cruzeiro",
        12: "Samambaia",
        13: "Santa Maria",
        14: "São Sebastião",
        15: "Recanto das Emas",
        16: "Lago Sul",
        17: "Riacho Fundo",
        18: "Lago Norte",
        19: "Candangolândia",
        20: "Águas Claras",
        21: "Riacho Fundo II",
        22: "Sudoeste/Octogonal",
        23: "Varjão",
        24: "Park Way",
        25: "SCIA",
        26: "Sobradinho II",
        27: "Jardim Botânico",
        28: "Itapoã",
        29: "SIA",
        30: "Vicente Pires",
        31: "Fercal",
        32: "Sol Nascente e Por do Sol",
        33: "Arniqueira",
        34: "Arapoanga",
        35: "Água Quente",
    }

    # --- Botão principal ---
    if st.button("Buscar informações LUOS do CIPU"):
        if not cipu_input.strip().isdigit():
            st.warning("Por favor, insira um CIPU numérico válido.")
        else:
            try:
                # Consulta o serviço LUOS
                api_url = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/LUOS/MapServer/11/query"
                params = {
                    "where": f"lu_cipu = {cipu_input}",
                    "outFields": "lu_cod_par,lu_ra_luos",
                    "returnGeometry": "false",
                    "f": "json"
                }

                response = requests.get(api_url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data.get("features"):
                    st.error(f"Nenhum resultado encontrado para o CIPU {cipu_input}.")
                else:
                    attrs = data["features"][0]["attributes"]
                    codigo_parametro = attrs.get("lu_cod_par")
                    cod_ra = attrs.get("lu_ra_luos")
                    nome_ra = regioes_administrativas_luos.get(cod_ra, f"RA {cod_ra} (não mapeada)")

                    st.write(f"**📘 Código de Parâmetro:** {codigo_parametro or '-'}")
                    st.write(f"**🏙️ Região Administrativa:** {nome_ra}")

                    # Guarda no session_state
                    st.session_state["selected_cipu"] = cipu_input
                    st.session_state["codigo_parametro"] = codigo_parametro
                    st.session_state["nome_ra"] = nome_ra

                    # ===============================
                    # === BUSCA NAS TABELAS CSV ===
                    # ===============================

                    def nome_arquivo_seguro(nome_ra):
                        nome = unicodedata.normalize("NFD", nome_ra)
                        nome = "".join(ch for ch in nome if unicodedata.category(ch) != "Mn")
                        nome = nome.replace(" ", "_")
                        return nome

                    try:
                        nome_arquivo_base = nome_arquivo_seguro(nome_ra)
                        arquivo_lista = f"{nome_arquivo_base}_lista.csv"
                        arquivo_observacao = f"{nome_arquivo_base}_observacao.csv"

                        df_lista = pd.read_csv(arquivo_lista, sep=';', header=None)
                        df_observacao = pd.read_csv(
                            arquivo_observacao,
                            sep=';',
                            header=None,
                            on_bad_lines='skip',
                            dtype=str
                        )

                        # Filtra pela coluna 0 (código do parâmetro)
                        linha_encontrada = df_lista[df_lista.iloc[:, 0].astype(str) == str(codigo_parametro)]

                        if not linha_encontrada.empty:
                            st.write("Parâmetros Urbanísticos")
                            # Exibe os dados
                            mapeamento_indices = {
                                0: 'Código',
                                1: 'UOS',
                                2: 'Faixa Área(m²)',
                                3: 'Coeficiente Básico',
                                4: 'Coeficiente Máximo',
                                5: 'Taxa de Ocupação (%)',
                                6: 'Taxa de Permeabilidade (%)',
                                7: 'Altura Máxima',
                                8: 'Afastamento Frontal',
                                9: 'Afastamento Fundos',
                                10: 'Afastamento Lateral',
                                11: 'Observação do Afastamento',
                                12: 'Marquise',
                                13: 'Galeria',
                                14: 'Cota de Soleira',
                                15: 'Subsolo'
                            }

                            linha = linha_encontrada.iloc[0].values
                            for indice, nome_exibicao in mapeamento_indices.items():
                                if indice < len(linha) and pd.notna(linha[indice]) and str(linha[indice]).strip() != '':
                                    st.write(f"**{nome_exibicao}:** {linha[indice]}")
                                else:
                                    st.write(f"**{nome_exibicao}:** -")

                            # Observação
                            st.write("### 📝 Observação")
                            valor_uos = linha_encontrada.iloc[0, 1]
                            match = re.search(r'\((.*?)\)', str(valor_uos))
                            if match:
                                numero_obs = match.group(1).strip()
                                df_observacao.iloc[:, 0] = df_observacao.iloc[:, 0].astype(str).str.strip()
                                df_observacao.iloc[:, 0] = df_observacao.iloc[:, 0].str.replace(r'\.0$', '', regex=True)
                                obs = df_observacao[df_observacao.iloc[:, 0] == numero_obs]
                                if not obs.empty:
                                    texto_obs = ' '.join(
                                        str(x) for x in obs.iloc[0, 1:].dropna() if str(x) != 'nan'
                                    )
                                    st.write(texto_obs)
                                else:
                                    st.info("Nenhuma observação encontrada para este parâmetro.")
                            else:
                                st.info("Nenhuma observação associada.")
                        else:
                            st.error(f"Código de parâmetro '{codigo_parametro}' não encontrado nas listas de {nome_ra}.")

                    except FileNotFoundError:
                        st.error(f"❌ Arquivo não encontrado. Verifique se '{arquivo_lista}' e '{arquivo_observacao}' existem.")
                    except Exception as e:
                        st.error(f"Erro ao processar os arquivos CSV: {e}")

            except Exception as e:
                st.error(f"Erro ao consultar o serviço LUOS: {e}")


############################################################################################################

############################################################################################################

#######################
#SEDUH
with st.expander("**PDFs do Anexo II e III (LUOS) de forma manual**"):
    # Dados das regiões e links (no formato: Região;Link1;Link2)
    st.write("Data: Santa Maria e Minuta Lago Sul = LC1047/2025, restante = LC 1007/2022")
    dados_regioes = """
    Gama;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-1A_Gama.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-1A_Gama.pdf
    Taguatinga;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-2A_Taguatinga.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-2A_Taguatinga.pdf
    Brazlândia;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-3A_Brazlandia.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-3A_Brazlandia.pdf
    Sobradinho;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-4A_Sobradinho.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-4A_Sobradinho.pdf
    Planaltina;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-5A-Planaltina.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-5A_Planaltina.pdf
    Paranoá;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-6A_Paranoa.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-6A_Paranoa.pdf
    Núcleo Bandeirante;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-7A_Nucleo-Bandeirante.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-7A_Nucleo-Bandeirante.pdf
    Ceilândia;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-8A_Ceilandia.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-8A_Ceilandia.pdf
    Guará;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-9A_Guara.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-9A_Guara.pdf
    Samambaia;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-10A_Samambaia.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-10A_Samambaia.pdf
    Santa Maria 2022;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-11A_Santa-Maria.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-11A_Santa-Maria.pdf
    Santa Maria 2025;https://www.seduh.df.gov.br/documents/d/seduh/anexo-ii-mapa-11a-regiao-administrativa-de-santa-maria-ra-xiii-pdf;https://www.seduh.df.gov.br/documents/d/seduh/anexo-iii-quadro-11a-regiao-administrativa-de-santa-maria-ra-xiii-pdf
    Sao Sebastiao;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-12A_Sao-Sebastiao.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-12A_Sao-Sebastiao.pdf
    Recanto das Emas;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-13A_Recanto-das-Emas.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-13A_Recanto-das-Emas.pdf
    Lago Sul 2022;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-14A_Lago-Sul.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-14A_Lago-Sul.pdf
    Lago Sul 2025;https://www.seduh.df.gov.br/documents/d/seduh/anexo-ii-mapa-14a-regiao-administrativa-do-lago-sul-ra-xvi-pdf;https://www.seduh.df.gov.br/documents/d/seduh/anexo-iii-quadro-14a-regiao-administrativa-do-lago-sul-ra-xvi-pdf
    Riacho Fundo;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-15A_Riacho-Fundo.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-15A_Riacho-Fundo.pdf
    Lago Norte;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-16A_Lago-Norte.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-16A_Lago-Norte.pdf
    Aguas Claras;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-17A_Aguas-Claras.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-17A_Aguas-Claras.pdf
    Riacho Fundo II;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-18A_Riacho-Fundo-II.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-18A_Riacho-Fundo-II.pdf
    Varjao;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-19A_Varjao.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-19A_Varjao.pdf
    Park Way;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-20A_Park-Way.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-20A_Park-Way.pdf
    SCIA;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-21A_SCIA.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-21A_SCIA.pdf
    Sobradinho II;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-22A_Sobradinho-II.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-22A_Sobradinho.pdf
    Jardim Botanico;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-23A_Jardim-Botanico.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-23A_Jardim-Botanico.pdf
    Itapoa;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-24A_Itapoa.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-24A_Itapoa.pdf
    SIA;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-25A_SIA.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-25A_SIA.pdf
    Vicente Pires;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-26A_Vicente-Pires.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-26A_Vicente-Pires.pdf
    Fercal;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-27A_Fercal.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-27A_Fercal.pdf
    Sol Nascente;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-28A_Por-do-Sol_Sol-Nascente.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-28A_Sol-Nascente_Por-do-Sol.pdf
    Arniqueira;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-29A_Arniqueira.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-29A_Arniqueira.pdf
    """

    # Processar os dados
    regioes = {}
    for linha in dados_regioes.strip().split('\n'):
        partes = linha.split(';')
        if len(partes) == 3:
            regiao = partes[0]
            link1 = partes[1]
            link2 = partes[2]
            regioes[regiao] = {'Mapa': link1, 'Quadro': link2}

    # Interface do Streamlit
    st.markdown('🗺️ **Consulta dos parâmetros urbanísticos - Mapas e Quadros do DF**')
    st.markdown('Selecione uma região administrativa do Distrito Federal para acessar os documentos relacionados.')

    # Seleção da região
    regiao_selecionada = st.selectbox(
        'Selecione a região:',
        sorted(regioes.keys()),
        index=0,
        help='Escolha uma região administrativa do DF'
    )

    # Exibir os links
    if regiao_selecionada:
        st.markdown(f'Documentos para {regiao_selecionada}')
        
        st.markdown(f'**Mapa:** [Abrir Mapa PDF]({regioes[regiao_selecionada]["Mapa"]})', unsafe_allow_html=True)
        st.markdown(f'**Quadro:** [Abrir Quadro PDF]({regioes[regiao_selecionada]["Quadro"]})', unsafe_allow_html=True)




##############



############################################################################################################


############################################################################################################


if 'endereco' not in st.session_state:
    st.session_state.endereco = 'Não'
if 'obs_area_verde' not in st.session_state:
    st.session_state.obs_area_verde = 'Não'
if 'falta_calcada' not in st.session_state:
    st.session_state.falta_calcada = 'Não'

if 'calcada_pequena' not in st.session_state:
    st.session_state.calcada_pequena = "Não"
if 'calcada_verde' not in st.session_state:
    st.session_state.calcada_verde = "Não"
if 'calcada_parway' not in st.session_state:
    st.session_state.calcada_parway = "Não"
if 'obs_metragem' not in st.session_state:
    st.session_state.obs_metragem = "Sim"
if 'obs_poda' not in st.session_state:
    st.session_state.obs_poda = "Não"



def consultar_cipu(cipu):
    api_url = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/10/query"
    params = {
        "where": f"pu_cipu = {int(cipu)}",
        "outFields": "pu_cipu,x,y,pu_end_cart,pu_end_usual,pn_norma_vg",
        "returnGeometry": "true",
        "f": "json"
    }
    r = requests.get(api_url, params=params).json()
    results = []
    for f in r.get("features", []):
        x, y = f["attributes"].get("x"), f["attributes"].get("y")
        if x and y:
            lon, lat = transformer.transform(x, y)
            results.append({
                "cipu": f["attributes"].get("pu_cipu"),
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "end_cart": f["attributes"].get("pu_end_cart", ""),
                "end_usual": f["attributes"].get("pu_end_usual", ""),
                "norma_vg": f["attributes"].get("pn_norma_vg", "")
            })
    return results


# --- Gerar KML simples (somente CIPU) ---
def gerar_kml(dados):
    kml = simplekml.Kml()
    for d in dados:
        ponto = kml.newpoint(
            name=str(int(d["cipu"])),
            coords=[(d["lon"], d["lat"])]
        )

        ponto.description = (
            f"Endereço cartográfico: {d.get('end_cart', '')}\n"
            f"Endereço usual: {d.get('end_usual', '')}\n"
            f"Norma VG: {d.get('norma_vg', '')}"
        )
    return kml.kml()


# --- Gerar KML com nome ---
def gerar_kml_com_nome(coordenadas):
    kml = simplekml.Kml()
    for coord in coordenadas:
        nome_marcador = coord.get("nome", f"CIPU {coord['cipu']}")
        ponto = kml.newpoint(
            name=nome_marcador,
            coords=[(coord["lon"], coord["lat"])]
        )
        ponto.description = (
            f"CIPU: {coord['cipu']}\n"
            f"Nome: {coord.get('nome', 'N/A')}\n"
            f"Endereço cartográfico: {coord.get('end_cart', '')}\n"
            f"Endereço usual: {coord.get('end_usual', '')}\n"
            f"Norma VG: {coord.get('norma_vg', '')}"
        )
    return kml.kml()


# --- Interface Streamlit ---
with st.expander("**Exportar lista CIPU para Google Earth e Google Maps**", expanded=False):
    st.markdown("**Exportar para o Google Earth somente com o CIPU:**")
    cipu_list = st.text_area("Insira uma lista de CIPUs (Um por linha)").splitlines()

    if st.button("Consultar coordenadas"):
        todos = []
        for c in cipu_list:
            if c.strip().isdigit():
                todos.extend(consultar_cipu(c.strip()))
        st.session_state["cipu_coords"] = todos
        st.success(f"{len(todos)} coordenadas obtidas!")

    if "cipu_coords" in st.session_state and st.session_state["cipu_coords"]:
        if st.button("Exportar para KML", type="primary"):
            kml = gerar_kml(st.session_state["cipu_coords"])
            st.download_button("Baixar KML", kml, file_name="cipu_export.kml")

        df = pd.DataFrame(st.session_state["cipu_coords"])
        df["cipu"] = df["cipu"].astype(int)
        df["coordenada"] = df["lat"].astype(str) + ", " + df["lon"].astype(str)
        st.dataframe(df, use_container_width=True)

        def gerar_link_google_maps(dados):
            base_url = "https://www.google.com/maps/dir/"
            coords = [f"{d['lat']},{d['lon']}" for d in dados]
            return base_url + "/".join(coords)

        link = gerar_link_google_maps(st.session_state["cipu_coords"])
        st.markdown(f"📍 [Abrir rota no Google Maps]({link})", unsafe_allow_html=True)

    st.divider()
    st.markdown("**Exportar para o Google Earth com o nome do ponto**")
    st.write("Formato: `CIPU; Nome` — um por linha. Exemplo:")
    st.write("123;HBT 500")
    st.write("5678;HBT 90")

    cipu_nome_list = st.text_area("Um por linha").splitlines()

    if st.button("Consultar coordenadas (CIPU + Nome)"):
        todos = []
        for linha in cipu_nome_list:
            if ";" in linha:
                partes = linha.split(";")
                cipu = partes[0].strip()
                nome = partes[1].strip() if len(partes) > 1 else f"CIPU {cipu}"

                if cipu.isdigit():
                    coords = consultar_cipu(cipu)
                    for c in coords:
                        c["nome"] = nome
                    todos.extend(coords)

        st.session_state["cipu_nome_coords"] = todos
        st.success(f"{len(todos)} coordenadas obtidas com nome!")

    if "cipu_nome_coords" in st.session_state and st.session_state["cipu_nome_coords"]:
        if st.button("Exportar para KML (com nome)", type="primary"):
            kml = gerar_kml_com_nome(st.session_state["cipu_nome_coords"])
            st.download_button("Baixar KML", kml, file_name="cipu_nome_export.kml")

        df2 = pd.DataFrame(st.session_state["cipu_nome_coords"])
        df2["cipu"] = df2["cipu"].astype(int)
        df2["coordenada"] = df2["lat"].astype(str) + ", " + df2["lon"].astype(str)
        st.dataframe(df2, use_container_width=True)

        def gerar_link_google_maps_nome(dados):
            base_url = "https://www.google.com/maps/dir/"
            coords = [f"{d['lat']},{d['lon']}" for d in dados]
            return base_url + "/".join(coords)

        link2 = gerar_link_google_maps_nome(st.session_state["cipu_nome_coords"])
        st.markdown(f"📍 [Abrir rota no Google Maps (CIPU + Nome)]({link2})", unsafe_allow_html=True)

###perfil
with st.expander("**Perfil de elevação**", expanded=False):
    st.write("Clique no Primeiro ponto para definir o início do Perfil 🟢")
    st.write("Clique no Segundo ponto para definir o início do Perfil 🔵")    
    st.write("Depois clique em --Gerar Perfil--")

    # --- Configurações da API ---
    REST_URL = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Geoprocessing/Profile1m/GPServer/Profile/execute"

    # Inicializa o estado da sessão
    if 'points' not in st.session_state:
        st.session_state.points = []
    if 'skip_append' not in st.session_state:
        st.session_state.skip_append = False
    if 'zoom_level' not in st.session_state:
        st.session_state.zoom_level = 14
    # Novo estado para a geometria do lote no mapa de perfil
    if 'cipu_geojson' not in st.session_state:
        st.session_state.cipu_geojson = None

    # --- Função para limpar pontos ---
    #def clear_points():
     #   st.session_state.points = []
      #  st.session_state.skip_append = True
       # st.session_state.cipu_geojson = None  # Limpa a geometria do lote também
        #st.rerun()

    # Configuração inicial do centro e zoom
    if not st.session_state.points:
        map_center = [-15.779774, -47.925562]
    else:
        last_point = st.session_state.points[-1]
        map_center = [last_point[1], last_point[0]]

    # Cria o mapa principal (único) do perfil de elevação
    m_perfil = folium.Map(location=map_center, zoom_start=st.session_state.zoom_level, tiles="Esri.WorldImagery", max_zoom=23)

    # Adiciona o cursor crosshair personalizado
    m_perfil.get_root().header.add_child(
        folium.Element("""
        <style>
        .leaflet-container {
            cursor: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32'><circle cx='16' cy='16' r='14' fill='none' stroke='red' stroke-width='2'/><line x1='16' y1='0' x2='16' y2='8' stroke='red' stroke-width='2'/><line x1='16' y1='24' x2='16' y2='32' stroke='red' stroke-width='2'/><line x1='0' y1='16' x2='8' y2='16' stroke='red' stroke-width='2'/><line x1='24' y1='16' x2='32' y2='16' stroke='red' stroke-width='2'/></svg>") 16 16, crosshair !important;
        }
        </style>
        """)
    )

    # Se já houver pontos, desenha-os no mapa
    if st.session_state.points:
        if len(st.session_state.points) > 1:
            folium.PolyLine(
                locations=[(lat, lon) for lon, lat in st.session_state.points],
                color="red",
                weight=3,
                opacity=0.8
            ).add_to(m_perfil)
        
        for i, (lon, lat) in enumerate(st.session_state.points):
            if i == 0:
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=3,                 # tamanho do ponto
                    color="green",            # cor da borda
                    fill=True,
                    fill_color="green",
                    fill_opacity=1,
                    popup="Início"
                ).add_to(m_perfil)
            elif i == len(st.session_state.points) - 1:
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=3,
                    color="blue",
                    fill=True,
                    fill_color="blue",
                    fill_opacity=1,
                    popup="Fim"
                ).add_to(m_perfil)
            else:
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=3,
                    color="gray",
                    fill=True,
                    fill_color="gray",
                    fill_opacity=1,
                    popup=f"Ponto {i+1}"
                ).add_to(m_perfil)

    # --- Adiciona a geometria do lote ao mapa, se existir no estado da sessão ---
    # --- Adiciona a geometria do lote ao mapa, se existir no estado da sessão ---
    if st.session_state.cipu_geojson:
    # Adiciona o polígono
        gj = folium.GeoJson(
            st.session_state.cipu_geojson,
            style_function=lambda feature: {
                "fillColor": "cyan",
                "color": "cyan",
                "weight": 3,
                "fillOpacity": 0.01,
                "pointer-events": "none"
            },
            interactive=False
        ).add_to(m_perfil)

        # Ajusta mapa para caber todo o polígono
        coords = st.session_state.cipu_geojson['geometry']['coordinates'][0]
        lats = [pt[1] for pt in coords]
        lons = [pt[0] for pt in coords]
        m_perfil.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])


    # Renderiza o mapa - ESTA LINHA DEFINE map_state
    map_state = st_folium(m_perfil, width=700, height=500, key="map")
    
    # Botão para carregar o lote no mapa de perfil
    # Botão para carregar o lote no mapa de perfil
    if st.button("Carregar o Lote a Partir do CIPU"):
        # Obtém os dados do resultado selecionado
        all_data = st.session_state.get("all_general_data")
        idx = st.session_state.get("selected_feature_index")

        if all_data and idx is not None and 0 <= idx < len(all_data):
            selected_data = all_data[idx]
            selected_geometry = selected_data.get("geometry")

            if selected_geometry and selected_geometry.get('rings'):
                transformed_rings = []
                for ring in selected_geometry.get('rings'):
                    transformed_ring = []
                    for x, y in ring:
                        # Converte de Web Mercator (x, y) para Lat, Lon
                        lat, lon = transformer.transform(x, y)
                        transformed_ring.append([lat, lon]) # O folium espera [lat, lon]
                    transformed_rings.append(transformed_ring)

                # Cria a feature GeoJSON e salva no estado da sessão
                geojson_feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [transformed_rings[0]]
                    }
                }
                st.session_state.cipu_geojson = geojson_feature
            
            # Re-executa o script para redesenhar o mapa com a nova geometria
            st.rerun()
        else:
            st.warning("Carregue um CIPU primeiro e depois clique no botão.")


#############################################
#############################################
#############################################
    # --- Clique no mapa ---
    # --- Clique no mapa --- (AGORA COM ATUALIZAÇÃO DE ZOOM)
    if map_state and "last_clicked" in map_state and map_state["last_clicked"]:
        new_point = (map_state["last_clicked"]['lng'], map_state["last_clicked"]['lat'])
        
        # ATUALIZA O ZOOM APENAS QUANDO HOUVER CLIQUE
        if map_state and "zoom" in map_state:
            st.session_state.zoom_level = map_state["zoom"]
        
        if not st.session_state.skip_append:
            if not st.session_state.points or new_point != st.session_state.points[-1]:
                st.session_state.points.append(new_point)
                st.rerun()
        else:
            st.session_state.skip_append = False  # reseta flag após limpar

    # --- Lista de pontos ---
    #st.subheader("Pontos da Linha")
    #if st.session_state.points:
    #    for i, point in enumerate(st.session_state.points):
    #        st.write(f"Ponto {i+1}: Lon={point[0]:.6f}, Lat={point[1]:.6f}")

    # Botão de limpar
    #st.button("Limpar todos os Pontos", on_click=clear_points)


    if st.button("Gerar Perfil"):
        if len(st.session_state.points) < 2:
            st.error("Por favor, selecione pelo menos dois pontos no mapa para gerar o perfil.")
        else:
            try:
                # Formato correto para a API do ArcGIS
                geometry_json = {
                    "geometryType": "esriGeometryPolyline",
                    "features": [
                        {
                            "geometry": {
                                "paths": [st.session_state.points],
                                "spatialReference": {"wkid": 4326}
                            }
                        }
                    ]
                }
                
                params = {
                    "InputLineFeatures": json.dumps(geometry_json),
                    "DEMResolution": "FINEST",
                    "returnZ": "true",
                    "f": "json"
                }

                st.info("Buscando o perfil de elevação...")
                
                response = requests.post(REST_URL, data=params)
                response_json = response.json()

                # Verificar se a resposta contém resultados
                if response_json.get("results"):
                    result = response_json["results"][0]["value"]
                    
                    if isinstance(result, str):
                        # Tentar parsear se for string JSON
                        try:
                            result = json.loads(result)
                        except:
                            st.error("Formato de resposta inválido da API")
                            st.stop()
                    
                    if "features" in result and result["features"]:
                        feature = result["features"][0]
                        
                        # Verificar diferentes formatos possíveis
                        if "geometry" in feature and "paths" in feature["geometry"]:
                            profile_points = feature["geometry"]["paths"][0]
                            
                            if len(profile_points[0]) >= 3:
                                # Processar dados de elevação
                                df = pd.DataFrame(profile_points, columns=['lon', 'lat', 'elevation'])
                                df['distance'] = 0.0
                                
                                # Calcular distâncias cumulativas
                                for i in range(1, len(df)):
                                    p1 = (df.loc[i-1, 'lon'], df.loc[i-1, 'lat'])
                                    p2 = (df.loc[i, 'lon'], df.loc[i, 'lat'])
                                    # Converter graus para metros (aproximadamente)
                                    distance = sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2) * 111320
                                    df.loc[i, 'distance'] = df.loc[i-1, 'distance'] + distance
                                
                                st.success("Perfil gerado com sucesso!")
                                # Criar pontos interpolados para suavização extrema
                                if len(df) > 10:
                                    # Spline cúbica para suavização máxima
                                    x_smooth = np.linspace(df['distance'].min(), df['distance'].max(), 1000)
                                    
                                    # Usar interpolação cúbica para suavização
                                    cs = interpolate.CubicSpline(df['distance'], df['elevation'])
                                    y_smooth = cs(x_smooth)
                                    
                                    # Criar gráfico com linha suavizada
                                    fig = go.Figure()
                                    
                                    # Linha suavizada (principal)
                                    fig.add_trace(go.Scatter(
                                        x=x_smooth, 
                                        y=y_smooth,
                                        mode='lines',
                                        name='Perfil',
                                        line=dict(color='blue', width=3, shape='spline'),
                                        hoverinfo='skip'
                                    ))
                                    
                                    # Pontos originais (opcional, para referência)
                                    fig.add_trace(go.Scatter(
                                        x=df['distance'],
                                        y=df['elevation'],
                                        mode='markers',
                                        name='Pontos GeoPortal',
                                        marker=dict(color='red', size=4, opacity=0.6),
                                        hoverinfo='text',
                                        text=[f'Dist: {d:.1f}m<br>Elev: {e:.1f}m' for d, e in zip(df['distance'], df['elevation'])]
                                    ))
                                    
                                else:
                                    # Para poucos pontos, usar interpolação linear suavizada
                                    fig = px.line(df, x='distance', y='elevation', 
                                                labels={'distance': 'Distância (m)', 'elevation': 'Elevação (m)'}, 
                                                title="Perfil de Elevação da Linha")
                                    fig.update_traces(line=dict(shape='spline', smoothing=1.3, width=3))
                                
                                # Define a escala fixa para o eixo Y
                                min_elevation = df['elevation'].min() - 5  # Margem inferior
                                max_elevation = df['elevation'].max() + 5  # Margem superior

                                # Configurações do layout com escala vertical FIXA
                                fig.update_layout(
                                    hovermode="x unified",
                                    showlegend=True,
                                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                    xaxis_title="Distância (m)",
                                    yaxis_title="Elevação (m)",
                                    height=500,
                                    yaxis=dict(
                                        tickmode="linear",
                                        tick0=0,
                                        dtick=1,  # Marcadores de 1 em 1 metro
                                        range=[min_elevation, max_elevation],  # ← ESCALA FIXA AQUI
                                        showgrid=True,
                                        gridwidth=1,
                                        gridcolor="lightgray",
                                        zeroline=True,
                                        zerolinewidth=2,
                                        zerolinecolor="gray"
                                    )
                                )
                                
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Estatísticas

                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Elevação Mínima", f"{df['elevation'].min():.1f} m")
                                with col2:
                                    st.metric("Elevação Máxima", f"{df['elevation'].max():.1f} m")
                                with col3:
                                    st.metric("Desnível Total", f"{abs(df['elevation'].max() - df['elevation'].min()):.1f} m")
                                with col4:
                                    st.metric("Comprimento Total", f"{df['distance'].max():.1f} m")
                                
                                # Comprimento total
                                
                                
                                
                                # Mapa com a linha
                                #st.subheader("Linha Traçada no Mapa")
                                #map_center = [df['lat'].mean(), df['lon'].mean()]
                                #m_result = folium.Map(location=map_center, zoom_start=14, tiles="cartodbpositron")
                                #folium.PolyLine(locations=df[['lat', 'lon']].values.tolist(), color="red", weight=5, opacity=0.8).add_to(m_result)
                                #folium.Marker(location=[df['lat'].iloc[0], df['lon'].iloc[0]], popup="Início", icon=folium.Icon(color='green')).add_to(m_result)
                                #folium.Marker(location=[df['lat'].iloc[-1], df['lon'].iloc[-1]], popup="Fim", icon=folium.Icon(color='blue')).add_to(m_result)
                                #folium_static(m_result)
                                
                                st.write("Download dos dados")
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="Download dos dados CSV",
                                    data=csv,
                                    file_name="perfil_elevacao.csv",
                                    mime="text/csv"
                                )
                                
                            else:
                                st.error("Dados de elevação não retornados. Verifique as coordenadas.")
                        else:
                            st.error("Formato de geometria inválido na resposta da API")
                    else:
                        st.error("Nenhuma feature retornada pela API. Verifique as coordenadas.")
                else:
                    error_msg = response_json.get("error", {}).get("message", "Erro desconhecido")
                    st.error(f"Erro ao obter o perfil: {error_msg}")
                    
            except Exception as e:
                st.error(f"Ocorreu um erro: {str(e)}")

### gerar mapa do lote
with st.expander("**Perímetro do Lote - Planta com cotas**", expanded=False):
    st.write("Observação: podem ocorrer pequenas imprecisões, da ordem de alguns centímetros.")

    # Recupera o CIPU e a geometria do lote selecionado (já carregados anteriormente)
    if st.session_state.get("all_general_data"):
        selected_data = st.session_state.all_general_data[st.session_state.selected_feature_index]
        pu_cipu = selected_data.get("cipu")
        geometry = selected_data.get("geometry")
    else:
        pu_cipu = None
        geometry = None

   
    # Botão principal
    if st.button("Gerar Planta", key="gerar_planta"):
        if not geometry or not pu_cipu:
            st.warning("Nenhum CIPU carregado. Primeiro realize a pesquisa do imóvel.")
        else:

            # Função Haversine (graus -> metros)
            def haversine_metros(lon1, lat1, lon2, lat2):
                R = 6371000
                lon1_r, lat1_r, lon2_r, lat2_r = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2_r - lon1_r
                dlat = lat2_r - lat1_r
                a = sin(dlat/2)**2 + cos(lat1_r) * cos(lat2_r) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                return R * c

            # Distância Euclidiana (quando já está em metros)
            def euclidiana_metros(x1, y1, x2, y2):
                return sqrt((x2 - x1)**2 + (y2 - y1)**2)

            # Extrair coordenadas da geometria (rings, paths, etc.)
            coords = []
            if "rings" in geometry:
                ring = geometry["rings"][0]
                for pt in ring:
                    coords.append((pt[0], pt[1]))
            elif "paths" in geometry:
                for path in geometry["paths"]:
                    for pt in path:
                        coords.append((pt[0], pt[1]))
            elif "x" in geometry and "y" in geometry:
                coords.append((geometry["x"], geometry["y"]))
            else:
                st.warning("Geometria em formato não tratado.")
                coords = []

            if not coords:
                st.warning("Nenhuma coordenada extraída da geometria.")
            else:
                if len(coords) > 1 and coords[0] == coords[-1]:
                    coords = coords[:-1]

                sample_x, sample_y = coords[0]
                em_graus = (abs(sample_x) <= 180 and abs(sample_y) <= 90)

                tipo_coord = "Geográficas (graus)" if em_graus else "UTM / Métricas (metros)"


                segs = []
                n = len(coords)
                perimetro = 0.0

                for i in range(n):
                    x1, y1 = coords[i]
                    x2, y2 = coords[(i + 1) % n]
                    dist = haversine_metros(x1, y1, x2, y2) if em_graus else euclidiana_metros(x1, y1, x2, y2)
                    perimetro += dist
                    segs.append({
                        "lado": f"{i+1}",
                        "x1": x1, "y1": y1,
                        "x2": x2, "y2": y2,
                        "dist_m": dist,
                        "x_mid": (x1 + x2) / 2,
                        "y_mid": (y1 + y2) / 2
                    })

                # Tabela de segmentos
                df_segs = pd.DataFrame([{
                    "lado": s["lado"],
                    "x1": s["x1"], "y1": s["y1"],
                    "x2": s["x2"], "y2": s["y2"],
                    "dist_m": round(s["dist_m"], 3)
                } for s in segs])

                xs = [p[0] for p in coords] + [coords[0][0]]
                ys = [p[1] for p in coords] + [coords[0][1]]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines+markers+text",
                    text=[str(i+1) for i in range(len(coords))] + [""],
                    textposition="top center",
                    line=dict(width=2, color='blue'),
                    marker=dict(size=7, color='red'),
                ))

                # Anotações de distâncias
                for s in segs:
                    fig.add_annotation(
                        x=s["x_mid"],
                        y=s["y_mid"],
                        text=f'{s["dist_m"]:.1f} m',
                        showarrow=False,
                        font=dict(size=11, color='black', weight='bold'),
                        # Caixa de fundo para melhorar a leitura
                        bgcolor="yellow", 
                        bordercolor="black",
                        borderwidth=0.5,
                        borderpad=2,
                    )

                fig.update_yaxes(scaleanchor="x", scaleratio=1)
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)
                dx = x_max - x_min
                dy = y_max - y_min
                margem = max(dx, dy) * 0.05 if max(dx, dy) > 0 else 0.00005
                fig.update_xaxes(range=[x_min - margem, x_max + margem])
                fig.update_yaxes(range=[y_min - margem, y_max + margem])

                fig.update_layout(
                    title=f"Geometria do CIPU {pu_cipu} (em graus)" if em_graus else f"Geometria do CIPU {pu_cipu} (em metros)",
                    xaxis_title="X",
                    yaxis_title="Y",
                    width=800,
                    height=700,
                    plot_bgcolor="white",
                    showlegend=False
                )
                #st.write(df_segs)
                #st.write(coords)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f"**Perímetro total:** {perimetro:.2f} m")

    else:
        st.info("Primeiro realize a pesquisa do imóvel na etapa **Parâmetros Urbanísticos.**")

############# relatório de vistoria ##########
with st.expander("**Gerar Relatório de Vistoria**", expanded=False):
    # --- Perguntas do Resumo Final ---
    
    st.radio("**1) Existe rampa (cunha) na entrada de veículos?**", options=['Sim', 'Não'], key='rampa', horizontal=True)
    st.radio("**2) Existe telhado em área pública?**", options=['Sim', 'Não'], key='telhado', horizontal=True)
    st.radio("**3) Falta Placa de Endereçamento?**", options=['Sim', 'Não'], key='endereco', horizontal=True)
    st.radio("**4) Área impermeável onde foi previsto permabilidade?**", options=['Sim', 'Não'], key='obs_area_verde', horizontal=True) 
    st.radio("**5) Falta calçada ou está irregular?**", options=['Sim', 'Não'], key='falta_calcada', horizontal=True) 

    st.divider()

    # --- Campo de Observações (Seleção única) ---
    st.subheader("Observações")
    
    opcoes_obs = {
        "Art 151": "Trata-se de processo de Habite-se de Regularização, conforme ATESTADO DE HABILITAÇÃO DE REGULARIZAÇÃO, embasado no ART.151 da LEI Nº 6.138/18, sendo, portanto, a vistoria restrita à verificação da consonância do imóvel executado com o licenciado através do projeto de arquitetura visado.",
        "Art 153": "Trata-se de processo de Habite-se de Regularização, conforme ATESTADO DE HABILITAÇÃO DE REGULARIZAÇÃO, embasado no ART.153 da LEI Nº 6.138/18, sendo, portanto, a vistoria restrita à verificação da consonância do imóvel executado com o licenciado através do projeto de arquitetura depositado. Obra comprovadamente concluída há mais de cinco anos. Indevida a cobrança da Taxa de Execução de Obras - TEO. Parecer técnico UREC/DF LEGAL de 05/10/2020 - Processo SEI 04017-00015495/2020-87",
        "Alvará 7 dias": "Vistoria restrita à verificação da consonância do imóvel executado com o licenciado pelo Alvará de Construção supracitado, referente ao projeto de arquitetura depositado conforme Termo de Responsabilidade e Cumprimento de Normas, TRCN, com base na Lei 6.412/2019 e Decreto 40.302/2019",
        "Alvarás antigos (2018<)": "Vistoria restrita à verificação da consonância do imóvel executado com o licenciado pelo Alvará de Construção supracitado, referente ao projeto de arquitetura visado."
    }
    
    st.radio(
        "Selecione uma opção para o campo 'Observações':",
        options=list(opcoes_obs.keys()),
        format_func=lambda x: x if x else "Nenhuma",
        key='observacoes_selecionadas'
    )

    st.radio("Nota Técnica para as calçadas do Park Way, Chácaras do Lago Sul, SMDB e SMLN", options=['Sim', 'Não'], key='calcada_parway', horizontal=True) 
    st.radio("Nota Técnica para as calçadas do Condomínio Verde do JB", options=['Sim', 'Não'], key='calcada_verde', horizontal=True) 
    st.radio("Nota sobre a Metragem do imóvel", options=['Sim', 'Não'], key='obs_metragem', horizontal=True)  
    st.radio("Nota sobre poda de árvore", options=['Sim', 'Não'], key='obs_poda', horizontal=True)  
    st.radio("Nota sobre calçada", options=['Sim', 'Não'], key='calcada_pequena', horizontal=True) 
 
 

    st.divider()

    # --- Campo Livre ---
    st.subheader("Informações Adicionais (Resumo)")
    st.text_area(
        "Adicione qualquer informação relevante ao resumo final:",
        key='texto_livre',
        height=100
    )

    st.divider()
    
    # --- Botão para gerar o relatório ---
    if st.button("**Gerar Relatório**"):
        st.session_state.relatorio_gerado = True

    # --- Bloco de Resumo Final e Ações ---
    if st.session_state.relatorio_gerado:
        st.subheader("Resumo da Vistoria")
        
        # --- Lógica de geração do resumo e observações ---
        resumo_final = []
        observacoes_final = []
        
        if st.session_state.rampa == "Sim":
            resumo_final.append("O responsável deverá demolir a rampa (cunha) instalada no acesso aos veículos invadindo a pista de rolamento. Art. 10 inciso VI do Decreto 38047/2017.")
        
        if st.session_state.telhado == "Sim":
            resumo_final.append("O telhado está ultrapassando o limite do lote. O interessado deverá retirar a parte do telhado que avança sobre área pública e providenciar a devida coleta da água pluvial de modo a não lança-la diretamente no passeio (calçada). Art. 62, inciso III, da Lei nº 6.138/2018, - a edificação não extrapole os limites do lote ou da projeção -.")
        
        if st.session_state.endereco == "Sim":
            resumo_final.append("Não consta placa de endereçamento. De acordo com o Art. 163 do Descreto Nº 43.056, DE 03 DE MARÇO DE 2022, na vistoria para subsidiar a emissão da carta de habite-se ou do atestado de conclusão, deve-se verificar: a instalação de placa de endereçamento legível, quando exigível.")
        
        if st.session_state.obs_area_verde == "Sim":
            resumo_final.append("Foi constado que existe área impermeável (calçada) nos locais indicados, no projeto arquitetônico, onde era previsto área permeável. De acordo com o Art. 163 do Descreto Nº 43.056, DE 03 DE MARÇO DE 2022, os parâmetros urbanísticos do projeto habilitado ou depositado a serem observados são: XII - taxa de permeabilidade ou de área verde")
        
        if st.session_state.falta_calcada == "Sim":
            resumo_final.append("A largura mínima das rotas acessíveis deve ser de 1,20 m, admitindo-se redução pontual para até 0,90 m, limitada a trechos com extensão máxima de 0,80 m, conforme a NBR 9050. A calçada deverá ainda possuir superfície antiderrapante, com piso regular, na altura do meio-fio e de forma contínua, sem interrupção do passeio para o acesso de veículos para a garagem, e com inclinação transversal máxima de 3%.")
        




        if st.session_state.texto_livre:
            resumo_final.append(st.session_state.texto_livre)



            
        if st.session_state.observacoes_selecionadas:
            # Use .append() para adicionar o valor à lista
            observacoes_final.append(opcoes_obs[st.session_state.observacoes_selecionadas])

        if st.session_state.calcada_parway == "Sim":
            observacoes_final.append("De acordo com a Nota Técnica N°1/2025-DF LEGAL/ SECEX/ UACESS, para obras em unidades de lotes no Park Way, Chácaras do Lago Sul, SMDB e SMLN, os itens 18.i e 18.j da NGB 118/97 e 18.n da NGB 161/98 foram revogados pela LUOS, passando a responsabilidade da execução da área comum (inclusive calçada) para o Condomínio, conforme estabelecido no Código de Obras e Edificações do Distrito Federal e na Convenção e Instituição de Condomínio de cada lote específico. Portanto, as calçadas internas ao lote não serão cobradas da última unidade quando da solicitação da Vistoria de Habite-se.")

        if st.session_state.calcada_verde == "Sim":
            observacoes_final.append("De acordo com a Nota Técnica nº.30/2023-DF-LEGAL/SUOB/COFIS/DIACESS, de 17/03/2023, o Condomínio Verde será responsável por executar ou reconstruir, no final da obra de urbanização, todas as calçadas contíguas às testadas dos lotes, conforme determina o inciso VIII, do artigo 15, da Lei nº 6.138/2018, atendendo à acessibilidade das áreas comuns e áreas lindeiras.")

        if st.session_state.obs_metragem == "Sim":
            observacoes_final.append("Ressaltamos que a área construída é declarada pelo Responsável Técnico, não cabendo a esta fiscalização afirmar se a área construída está correta em sua metragem final. ")

        if st.session_state.obs_poda == "Sim":
            observacoes_final.append("Este laudo não constitui autorização para poda ou supressão de árvores.")

        if st.session_state.calcada_pequena == "Sim":
            observacoes_final.append("O passeio externo foi objeto de verificação parcial desta vistoria, uma vez que a calçada não apresenta a largura mínima exigida para a aplicação integral da NBR 9050, conforme entendimento manifestado em Nota Técnica DIACESS/SUOB/DF LEGAL, de 28 de setembro de 2020. ")




        # Após adicionar todos os itens à lista, você pode juntá-los em uma única string, se necessário
        observacoes_final_str = " ".join(observacoes_final)
        
        # --- Exibição do Resumo ---
        relatorio_texto = ""
        st.markdown("### Pendências")
        if resumo_final:
            relatorio_texto += "Pendências:\n\n"
            for item in resumo_final:
                st.write(f"- {item}")
                relatorio_texto += f"- {item}\n"
        else:
            st.info("Nenhuma condição para o resumo foi selecionada.")
        
        # --- Exibição das Observações ---
        st.markdown("### Observações")
        if observacoes_final_str:
            st.write(observacoes_final_str)
            relatorio_texto += "\n\nObservações:\n\n" + observacoes_final_str
        else:
            st.info("Nenhuma observação adicional foi selecionada.")

        # --- Botões de Ação ---
        st.divider()
        
        col1, col2 = st.columns(2) # Mantido para consistência de layout, mas apenas um botão será usado.

        # Botão para gerar e baixar o PDF
        with col1: # Usando a primeira coluna

            def create_txt(resumo, observacoes):
        # Criar conteúdo do texto formatado
                txt_content = f"RELATÓRIO DE VISTORIA\n"
                txt_content += f"Data: {date.today()}\n"
                txt_content += "=" * 60 + "\n\n"
                
                # Seção de Pendências
                if resumo:
                    txt_content += "PENDÊNCIAS:\n"
                    txt_content += "-" * 30 + "\n"
                    for item in resumo:
                        txt_content += f"• {item}\n"
                    txt_content += "\n"
                else:
                    txt_content += "PENDÊNCIAS: Nenhuma pendência identificada.\n\n"
                
                # Seção de Observações
                if observacoes:
                    txt_content += "OBSERVAÇÕES:\n"
                    txt_content += "-" * 30 + "\n"
                    for obs in observacoes:
                        txt_content += f"{obs}\n\n"
                else:
                    txt_content += "OBSERVAÇÕES: Nenhuma observação adicional.\n"
                
                return txt_content

            # Gerar conteúdo do TXT
            txt_content = create_txt(resumo_final, observacoes_final)
            
            st.download_button(
                label="📥 Gerar TXT",
                data=txt_content,
                file_name=f"relatorio_vistoria_{date.today()}.txt",
                mime="text/plain",
                help="Clique para baixar o relatório em formato texto"
            )
