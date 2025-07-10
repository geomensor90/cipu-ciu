import streamlit as st
import requests
from pyproj import Transformer
import folium
from streamlit_folium import st_folium

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

# Título do app
st.title("Consulta de Cadastro Territorial")

# Formulário de pesquisa
with st.form("search_form"):
    search_field = st.selectbox("Pesquisar por", ["CIPU", "CIU", "pu_arquivo"])
    search_value = st.text_input("Digite o valor para pesquisa")
    submitted = st.form_submit_button("Pesquisar")

if submitted:
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
            "outFields": "pu_ciu,pu_cipu,pu_projeto,pu_situacao,pn_norma_vg,x,y,pu_arquivo", # Incluindo pu_arquivo
            "returnGeometry": "false",
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
                        "projeto": attrs.get('pu_projeto', 'N/A'),
                        "situacao_codigo": attrs.get('pu_situacao'),
                        "norma_vigente": attrs.get('pn_norma_vg', 'N/A'),
                        "latitude": current_lat,
                        "longitude": current_lon,
                        "pu_arquivo": attrs.get('pu_arquivo', 'N/A') # Incluir pu_arquivo
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
        st.write(f"**CIPU**: {selected_data.get('cipu', 'N/A')}")
        
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

        st.write(f"**Projeto**: {selected_data.get('projeto', 'N/A')}")
        
        situacao_map = {
            1: "Registrado",
            2: "Aprovado",
            4: "Escriturado"
        }
        situacao_codigo = selected_data.get("situacao_codigo")
        situacao_texto = situacao_map.get(situacao_codigo, "Desconhecido")
        st.write(f"**Situação**: {situacao_texto}")

        st.write(f"**Norma Vigente**: {selected_data.get('pn_norma_vg', 'N/A')}")
        st.write(f"**Latitude (WGS84)**: {selected_data.get('latitude', 'N/A')}")
        st.write(f"**Longitude (WGS84)**: {selected_data.get('longitude', 'N/A')}")

    # --- Botão para carregar Detalhes LUOS ---
    if selected_cipu != 'N/A':
        if st.button("**Carregar dados LUOS**"):
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
    


    # --- Botão para carregar o Mapa ---
    if st.button("**Carregar Mapa**"):
        st.session_state.show_map = True

    # --- Exibir o mapa Folium (Exibir apenas se o botão foi clicado) ---
    if st.session_state.show_map:
        st.subheader("Localização no Mapa")
        
        # O estilo do mapa é fixo agora
        selected_tiles = "Esri.WorldImagery"

        # Centraliza o mapa na coordenada do item selecionado ou no centro do Brasil
        selected_coords = st.session_state.map_coords_list[st.session_state.selected_feature_index] if st.session_state.map_coords_list else None
        
        center_coords = selected_coords if selected_coords else [-15.7797, -47.9297] # Centro de Brasília como fallback

        m = folium.Map(location=center_coords, zoom_start=15, tiles=selected_tiles)
        
        # Adiciona o marcador para a coordenada do item selecionado (sem popup_text)
        if selected_coords:
            feature_info = st.session_state.all_general_data[st.session_state.selected_feature_index]
            folium.Marker(
                location=selected_coords,
                tooltip=f"CIPU: {feature_info.get('cipu', 'N/A')}" # Apenas tooltip
            ).add_to(m)
        else:
            st.warning("Coordenadas de localização não disponíveis para o item selecionado.")
        
        # Exibe o mapa no Streamlit
        st_folium(m, width=700, height=500)
else:
    st.info("Use o formulário acima para pesquisar e ver os resultados do Cadastro Territorial.")
