import streamlit as st
import requests
from pyproj import Transformer
import folium
from streamlit_folium import st_folium
from datetime import date

import pandas as pd
from pyproj import Transformer
import time


# busca pelo mapa
with st.expander("Buscar Lotes e Soleiras por Mapa", expanded=False):
    # Ponto padrão em Brasília
    default_point = [-15.793665, -47.882956]  # (lat, lon)

    st.markdown("Consulta de Lotes, Pontos e Alvarás - Raio de 50m")

    # Initialize session state variables if they don't exist
    if "lotes_geojson" not in st.session_state:
        st.session_state.lotes_geojson = None
    if "pontos_geojson" not in st.session_state:
        st.session_state.pontos_geojson = None

    if "clicked_point" not in st.session_state:
        st.session_state.clicked_point = default_point

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
    mapa = folium.Map(location=[current_lat, current_lon], zoom_start=18, tiles="Esri.WorldImagery", max_zoom=23)

    # Add a marker for the selected point
    folium.CircleMarker(
        location=[current_lat, current_lon],
        radius=2,                  # raio do ponto (quanto menor, mais discreto)
        color="red",               # cor da borda
        fill=True,
        fill_color="red",          # cor de preenchimento
        fill_opacity=1,            # opacidade total
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



    # Adiciona controle de camadas
    folium.LayerControl().add_to(mapa)

    # Display the map and capture clicks
    map_data = st_folium(mapa, height=600, width=900)

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
        st.info("Pesquisando...")

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
            where_clause = f"pu_cipu = {int(search_value)}"

        # Parâmetros da API principal
        api_url = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/10/query"
        params = {
            "where": where_clause,
            "outFields": "pu_ciu,pu_cipu,pu_projeto,pu_end_cart,pu_ra,pu_end_usual,pu_situacao,pn_norma_vg,x,y,pu_arquivo,pn_cod_par,qd_dim_frente,qd_dim_fundo,qd_dim_lat_dir,qd_dim_lat_esq,qd_dim_chanfro", # Incluindo pu_arquivo
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
                st.success(f"{len(data['features'])} resultado(s) encontrado(s).")
                
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
                        "geometry": feature.get("geometry") # <-- Novo campo para armazenar a geometria
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

        
        # Adiciona texto adicional conforme o caso
        # Adiciona texto adicional conforme o caso
        if norma_vigente == "LC 1041/2024":
            norma_vigente += " (PPCUB) "
            url_completa = linkppcub + codigo_parametro
            st.markdown(f'**Parâmetro**: <a href="{url_completa}" target="_blank">{url_completa}</a>', unsafe_allow_html=True)

        elif norma_vigente == "LC 948/2019 alterada pela LC 1007/2022":
            norma_vigente += " (LUOS)"

        st.write(f"**Norma Vigente**: {norma_vigente}")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Latitude:** {selected_data.get('latitude', 'N/A')}")

        with col2:
            st.write(f"**Longitude:** {selected_data.get('longitude', 'N/A')}")

        link_google_maps = f"https://www.google.com/maps?q={selected_data.get('latitude', 'N/A')},{selected_data.get('longitude', 'N/A')}"
        st.write(f"[🗺️ Abrir no Google Maps 🗺️]({link_google_maps})", unsafe_allow_html=True)
        st.divider()

        ################## certidão dos parâmetros
        # Mostrar os resultados gerais
        if st.session_state.all_general_data:
            st.write(" ---- **Certidão dos Parâmetros Urbanísticos** ---- ")
            
            for idx, result in enumerate(st.session_state.all_general_data):
                with st.container():
                    st.write(f"**Resultado {idx + 1}**")
                    st.write(f"CIU: {result['ciu']}")
                    
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
                                        pdf_url = result.get("value")
                            
                            if not pdf_url:
                                st.warning("Link para o PDF não encontrado.")
                                st.stop()
                            
                            st.subheader("📄 Certidão Gerada")
                            st.markdown(f"[Clique aqui para abrir o PDF]({pdf_url})", unsafe_allow_html=True)






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

                    st.write(f"*Área básica de construção calculada (m²): {area_lote_float * coeficiente_basico_float:.2f}")
                    st.write(f"*Área máxima de construção calculada (m²): {area_lote_float * coeficiente_maximo_float:.2f}")
                    st.write(f"*Taxa de ocupação calculada (m²): {area_lote_float * (taxa_ocupacao_float/100):.2f}")
                    st.write(f"*Área permeável calculada (m²): {area_lote_float * (taxa_permeabilidade_float/100):.2f}")

                except (ValueError, TypeError):
                    st.warning("Não foi possível calcular as áreas de construção e permeabilidade devido a valores inválidos.")
        else:
            st.warning(f"Nenhum dado LUOS encontrado para este CIPU: {selected_cipu}.")
    
    ##########################
    # --- Botão para carregar Informações de Normas ---
    if selected_cipu != 'N/A':
        if st.button("**Carregar Projeto**"):
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
                st.write(f"**Parâmetro UOS**: {get_value(normas_attrs.get('pn_uos_par'))}")
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

                    st.write(f"*Área básica de construção calculada (m²): {area_lote_float2 * coeficiente_basico_float2:.2f}")
                    st.write(f"*Área máxima de construção calculada (m²): {area_lote_float2 * coeficiente_maximo_float2:.2f}")
                    st.write(f"*Taxa de ocupação calculada (m²): {area_lote_float2 * (taxa_ocupacao_float2/100):.2f}")
                    st.write(f"*Área permeável calculada (m²): {area_lote_float2 * (taxa_permeabilidade_float2/100):.2f}")
        else:
            st.warning(f"Nenhuma informação de Normas encontrada para CIPU {selected_cipu}.")


                
    
    # # # # # # # # # # # # 
# Supondo que 'selected_cipu' seja a variável com o valor de entrada (CIPU/CIU).
    if selected_cipu != 'N/A':
        if st.button("**Carregar Cotas de Soleira**"):
            st.session_state.show_cota_soleira_data = True
# https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CONTROLE_URBANO/MapServer/1/query
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

            # --- TENTATIVA 2: Buscar por CIU (se não achou nada) ---
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

                            # --- Se não houver link, tentar recuperar pelo CIPU retornado ---
                            for cota in cotas_encontradas:
                                if not cota.get("cs_link") and cota.get("cs_cipu"):
                                    try:
                                        params_cipu_2 = {
                                            "where": f"cs_cipu = {int(cota['cs_cipu'])}",
                                            "outFields": "cs_cota, cs_link, cs_cipu, cs_ciu",
                                            "returnGeometry": "false",
                                            "f": "json"
                                        }
                                        resp2 = requests.get(api_url, params=params_cipu_2)
                                        resp2.raise_for_status()
                                        data2 = resp2.json()
                                        if data2.get("features"):
                                            link2 = data2["features"][0]["attributes"].get("cs_link")
                                            if link2:
                                                cota["cs_link"] = link2
                                    except Exception as e:
                                        st.warning(f"Erro recuperando link por CIPU: {e}")
                    except Exception as e:
                        st.warning(f"Erro na busca por CIU: {e}")

            # Salva no cache
            st.session_state.cota_soleira_data_map[selected_cipu] = cotas_encontradas

            # --- EXIBE RESULTADOS IMEDIATAMENTE ---
            if cotas_encontradas:
                st.success(f"Encontradas {len(cotas_encontradas)} cota(s) de soleira para o lote.")
                for idx, cota in enumerate(cotas_encontradas, start=1):
                    st.markdown(f"**Cota {idx}:** {cota.get('cs_cota', 'N/A')}")
                    link = cota.get('cs_link')
                    if link:
                        st.markdown(f"[📄 Ver Documento]({link})")
                    else:
                        st.markdown("⚠️ **Não tem LINK desse documento no GeoPortal**")
                    st.markdown("---")
            else:
                st.warning("Nenhuma cota de soleira encontrada para este lote.")



    # # # # # # # # # # # # 






    # --- Botão para carregar o Mapa ---
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
            max_zoom=21,
            attr="GDF / GeoServiços",
            show=False  # Desligado por padrão
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
    st.info("Use o formulário acima para pesquisar e ver os resultados do Cadastro Territorial.")




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



#######################
#SEDUH
with st.expander("**Anexo III - Parâmetros Urbanísticos do Terreno**"):
    # Dados das regiões e links (no formato: Região;Link1;Link2)
    # Dados das regiões e links (no formato: Região;Link1;Link2)
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
    Santa Maria;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-11A_Santa-Maria.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-11A_Santa-Maria.pdf
    Sao Sebastiao;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-12A_Sao-Sebastiao.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-12A_Sao-Sebastiao.pdf
    Recanto das Emas;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-13A_Recanto-das-Emas.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-13A_Recanto-das-Emas.pdf
    Lago Sul;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-II-%25E2%2580%2593-Mapa-14A_Lago-Sul.pdf;https://www.seduh.df.gov.br/documents/6726485/38572899/LC1007_2022_Anexo-III-%25E2%2580%2593-Quadro-14A_Lago-Sul.pdf
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


#######################################
# Restante do seu código permanece igual...
# Layout do formulário
# --- Expander Principal ---

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
