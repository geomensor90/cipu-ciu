import streamlit as st
import requests
from pyproj import Transformer
import folium
from streamlit_folium import st_folium
import fpdf # Importa a biblioteca para gerar PDF
import base64 # Para fazer o download do PDF
import io # Para manipular o PDF em memória
from datetime import date
import html
from fpdf import FPDF
import urllib.parse  # Para evitar problemas com caracteres especiais
import pandas as pd

# Use um expander para "esconder" o formulário de busca
with st.expander("Clique para buscar endereços", expanded=False):
    # URL do serviço ArcGIS REST para consulta de endereços
    ARCGIS_SERVICE_URL = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/10/query"

    # Campos de interesse
    ADDRESS_FIELD_NAME = "pu_end_usual"
    CARTORIAL_NAME = "pu_end_cart"
    CIPU_FIELD_NAME = "pu_cipu" 
    CIU_FIELD_NAME = "pu_ciu"   


    st.title("🗺️ Localizador de Endereços por Quadra - Geoportal DF")

    st.markdown(
        """
        Digite o nome de uma **quadra** (ex: `SQN 205`, `SCLN 309`) para listar todos os endereços 
        cadastrados dentro dela. Isso ajudará a localizar o prédio exato antes de usar o CIPU/CIU.
        """
    )

    # Campo de entrada para a quadra
    quadra_input = st.text_input("Digite a quadra ou parte do endereço (ex: SQN 205)", "")

    if st.button("Buscar Endereços"):
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
                            with st.expander("Ver todos os dados brutos (JSON)"):
                                st.json(data)
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

    st.markdown("---")
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
# Inicializar o estado da sessão (session_state)
if 'cota_soleira_data_map' not in st.session_state:
    st.session_state.cota_soleira_data_map = {}
if 'show_cota_soleira_data' not in st.session_state:
    st.session_state.show_cota_soleira_data = False
# # # # # # # # # # # # 


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
            "outFields": "pu_ciu,pu_cipu,pu_projeto,pu_situacao,pn_norma_vg,x,y,pu_arquivo,pn_cod_par", # Incluindo pu_arquivo
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
                        "pu_arquivo": attrs.get('pu_arquivo', 'N/A'), 
                        "codigo_parametro": attrs.get('pn_cod_par', 'N/A')
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

        st.write(f"**Projeto**: {selected_data.get('projeto', 'N/A')}")
        
        situacao_map = {
            1: "Registrado",
            2: "Aprovado",
            4: "Escriturado"
        }
        situacao_codigo = selected_data.get("situacao_codigo")
        situacao_texto = situacao_map.get(situacao_codigo, "Desconhecido")
        st.write(f"**Situação**: {situacao_texto}")

        #st.write(f"**Norma Vigente**: {selected_data.get('norma_vigente', 'N/A')}")
        norma_vigente = selected_data.get('norma_vigente', 'N/A')

        
        linkppcub = 'https://sistemas.df.gov.br/PPCUB_SEDUH/Geoportal?File='
        codigo_parametro = selected_data.get('codigo_parametro')

        
        # Adiciona texto adicional conforme o caso
        if norma_vigente == "LC 1041/2024":
            norma_vigente += " (PPCUB) "
            st.write(f"**Parametro**: {linkppcub + codigo_parametro}")
        elif norma_vigente == "LC 948/2019 alterada pela LC 1007/2022":
            norma_vigente += " (LUOS)"

        st.write(f"**Norma Vigente**: {norma_vigente}")

        st.write(f"**Latitude (WGS84)**: {selected_data.get('latitude', 'N/A')}")
        st.write(f"**Longitude (WGS84)**: {selected_data.get('longitude', 'N/A')}")

        link_google_maps = f"https://www.google.com/maps?q={selected_data.get('latitude', 'N/A')},{selected_data.get('longitude', 'N/A')}"
        st.write(f"[Abrir no Google Maps]({link_google_maps})", unsafe_allow_html=True)

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
        if st.button("**Carregar NGB**"):
            st.session_state.show_normas_data = True
            if selected_cipu not in st.session_state.normas_data_map:
                st.info(f"Buscando informações de Normas para CIPU {selected_cipu}...")
                where_clause_normas = f"pn_cipu = {int(selected_cipu)}"
                api_url_normas = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CADASTRO_TERRITORIAL/FeatureServer/18/query"
                params_normas = {
                    "where": where_clause_normas,
                    "outFields": "pn_uos_par,pn_uso,pn_tx_ocu,pn_cfa_b,pn_cfa_m,pn_alt_max,pn_tx_perm,pn_cota_sol,pn_subsol,pn_notas,pn_afr,pn_afu,pn_aft_lat_dir,pn_aft_lat_esq,pn_aft_obs,pn_marquise",
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
                st.rerun()

    # --- Exibir Informações de Normas ---
    if st.session_state.show_normas_data:
        normas_attrs = st.session_state.normas_data_map.get(selected_cipu)
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
        else:
            st.warning(f"Nenhuma informação de Normas encontrada para CIPU {selected_cipu}.")
    
    # # # # # # # # # # # # 
# Supondo que 'selected_cipu' seja a variável com o valor de entrada (CIPU/CIU).
    if selected_cipu != 'N/A':
        if st.button("**Carregar Cotas de Soleira**"):
            st.session_state.show_cota_soleira_data = True

            api_url = "https://www.geoservicos.ide.df.gov.br/arcgis/rest/services/Publico/CONTROLE_URBANO/MapServer/1/query"
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
        
        # Adiciona camada WMS
        folium.raster_layers.WmsTileLayer(
            url="https://www.geoservicos.ide.df.gov.br/arcgis/services/Publico/CADASTRO_TERRITORIAL/MapServer/WMSServer",
            name="Lotes Registrados",
            layers="6",  # Aqui é a camada correta
            fmt="image/png",
            transparent=True,
            attr="GDF / GeoServiços",
            show=False  # <== começa escondido
        ).add_to(m)

        # Adiciona controle para ativar/desativar camadas
        folium.LayerControl().add_to(m)

        # Adiciona o marcador para a coordenada do item selecionado (sem popup_text)
        if selected_coords:
        # Opção 1: Usar um ícone Font Awesome (ex: casa)
            folium.Marker(
                location=selected_coords,
                icon=folium.Icon(icon="home", color="blue", prefix='fa') # 'fa' é o prefixo para Font Awesome
            ).add_to(m)
        
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






#######################################
# Restante do seu código permanece igual...
# Layout do formulário
# --- Expander Principal ---
with st.expander("**Gerar Relatório de Vistoria**", expanded=False):
    st.header("Análise de Vistoria")
    st.write("Selecione as opções e preencha os campos para gerar o relatório final.")
    
    st.divider()

    # --- Perguntas do Resumo Final ---
    st.subheader("Resumo Final")
    
    st.write("##### 1) Existe rampa (cunha) na entrada de veículos?")
    st.radio("Selecione uma opção:", options=['Sim', 'Não'], key='rampa', horizontal=True)

    st.write("##### 2) Existe telhado em área pública?")
    st.radio("Selecione uma opção:", options=['Sim', 'Não'], key='telhado', horizontal=True)

    st.divider()

    # --- Campo de Observações (Seleção única) ---
    st.subheader("Observações Adicionais")
    
    opcoes_obs = {
        None: "Nenhuma observação adicional",
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
        observacoes_final = ""
        
        if st.session_state.rampa == "Sim":
            resumo_final.append("O responsável deverá demolir a rampa (cunha) instalada no acesso aos veículos invadindo a pista de rolamento.")
        
        if st.session_state.telhado == "Sim":
            resumo_final.append("O telhado está ultrapassando o limite do lote. O interessado deverá retirar a parte do telhado que avança sobre área pública e providenciar a devida coleta da água pluvial de modo a não lança-la diretamente no passeio (calçada).")
        
        if st.session_state.texto_livre:
            resumo_final.append(st.session_state.texto_livre)
            
        if st.session_state.observacoes_selecionadas:
            observacoes_final = opcoes_obs[st.session_state.observacoes_selecionadas]
        
        # --- Exibição do Resumo ---
        relatorio_texto = ""
        st.markdown("### Resumo Final")
        if resumo_final:
            relatorio_texto += "Resumo Final:\n\n"
            for item in resumo_final:
                st.write(f"- {item}")
                relatorio_texto += f"- {item}\n"
        else:
            st.info("Nenhuma condição para o resumo foi selecionada.")
        
        # --- Exibição das Observações ---
        st.markdown("### Observações")
        if observacoes_final:
            st.write(observacoes_final)
            relatorio_texto += "\n\nObservações:\n\n" + observacoes_final
        else:
            st.info("Nenhuma observação adicional foi selecionada.")

        # --- Botões de Ação ---
        st.divider()
        
        col1, col2 = st.columns(2) # Mantido para consistência de layout, mas apenas um botão será usado.

        # Botão para gerar e baixar o PDF
        with col1: # Usando a primeira coluna
            def create_pdf(text):
                pdf = fpdf.FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                
                # Configurações para quebra de linha
                pdf.multi_cell(0, 10, txt=text)
                
                return pdf.output(dest='S').encode('latin-1')

            pdf_content = create_pdf(relatorio_texto)
            st.download_button(
                label="📥 Gerar PDF",
                data=pdf_content,
                file_name=f"relatorio_vistoria_{date.today()}.pdf",
                mime="application/pdf"
            )
