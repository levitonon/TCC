import json
import requests
import os
from collections import defaultdict
import math

# Configurações da API Zabbix
ZABBIX_API_URL = "http://192.168.0.225/api_jsonrpc.php"  
AUTH_TOKEN = "9016c2e484b954ef43f2adf98e69c4a0"

# Caminho do grafo
JSON_REDE_PATH = "/home/osboxes/arquivos_tcc/network_graph.json"  

# Chamada para API com parâmetros a serem passados
def zabbix_api_call(method, params):
    headers = {'Content-Type': 'application/json'}  
    payload = {
        "jsonrpc": "2.0",  
        "method": method,    
        "params": params,    
        "auth": AUTH_TOKEN,  
        "id": 1              
    }

    try:
        response = requests.post(ZABBIX_API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Lança um erro para status de resposta HTTP 4xx/5xx
        response_json = response.json()  # Decodifica a resposta JSON

        if 'error' in response_json:           
            print(f"Erro na chamada da API ({method}): {response_json['error']['data']}")
            return None
        return response_json.get('result')  
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição HTTP: {e}")
        return None
    except json.JSONDecodeError:
        print("Erro ao decodificar a resposta JSON.")
        return None

# Identificação dos dispositivos pelo nome
def identificar_tipo(hostname):
=================================    
	   # Routers
=================================
    if hostname.startswith('RT'):
        return 'router'
=================================    
	   # Switches
=================================
    elif hostname.startswith('SWC'):
        return 'core'
    elif hostname.startswith('SWD'):
        return 'distribuicao'
    elif hostname.startswith('SWA'):
        return 'acesso'
    return 'desconhecido'  # Caso exista algum fora do padrão

# Extração da localidade/site
def extrair_localidade(hostname):
    partes = hostname.split('-')  # Divide o hostname baseado no caractere '-'
    if len(partes) >= 2:
        return partes[1]  # Retorna a segunda parte do hostname como localidade
    return 'UNICA'  # Retorna 'UNICA' se a localidade não estiver presente ou não seguir o padrão

# Definição dos ícones [130 para routers, 155 para switches, 158 para qualquer outro]
TIPOS_ICONE = {
    'router': 130,       
    'core': 155,         
    'distribuicao': 155, 
    'acesso': 155,       
    'desconhecido': 158  
}

# Detectar conexões a partir do grafo
def processar_json(json_rede):
    dispositivos = {}  # Dicionário para armazenar informações dos dispositivos
    conexoes = defaultdict(list)  # Dicionário para armazenar conexões entre dispositivos

    # Identificar os vizinhos e seus tipos
    for ip, vizinhos in json_rede.items():
        for vizinho in vizinhos:
            hostname = vizinho['hostname']  
            ip_vizinho = vizinho['ip']       
            tipo = identificar_tipo(hostname)  
            localidade = extrair_localidade(hostname)  

            if hostname not in dispositivos:
                dispositivos[hostname] = {
                    'hostname': hostname,
                    'ip': ip_vizinho,
                    'tipo': tipo,
                    'localidade': localidade,
                    'vizinhos': set()  
                }
            else:               
                dispositivos[hostname]['ip'] = ip_vizinho
                dispositivos[hostname]['tipo'] = tipo
                dispositivos[hostname]['localidade'] = localidade

    # Preencher as conexões entre dispositivos
    for ip, vizinhos in json_rede.items():
        hostname_atual = None  
        # Identifica o hostname correspondente a este IP
        for hostname, info in dispositivos.items():
            if info['ip'] == ip:
                hostname_atual = hostname
                break

        if not hostname_atual:
            # Regra para detectar o router
            if "RT" not in dispositivos:
                dispositivos["RT"] = {
                    'hostname': "RT",
                    'ip': ip,
                    'tipo': identificar_tipo("RT"),
                    'localidade': 'UNICA',
                    'vizinhos': set()
                }
            hostname_atual = "RT"  # Define o hostname atual como "RT"

        # Adiciona os vizinhos ao dicionário de conexões
        for vizinho in vizinhos:
            conexoes[hostname_atual].append(vizinho['hostname'])  
            dispositivos[hostname_atual]['vizinhos'].add(vizinho['hostname'])  

    for dispositivo in dispositivos.values():
        dispositivo['vizinhos'] = list(dispositivo['vizinhos'])

    return dispositivos, conexoes  

# Cálculo da posição de cada localidade de forma radial
def calcular_posicao_radia(largura, altura, index, total, raio_inicial=600, delta_raio=400):
    if total == 0:
        # Retorna o centro do mapa, caso esteja vazio
        return largura // 2, altura // 2

    angulo = (2 * math.pi / total) * index  # Calcula o ângulo baseado no índice e no total de localidades
    raio = raio_inicial + (delta_raio * index)  # Incrementa o raio para cada localidade

    # Calcula as coordenadas x e y usando a fórmula polar para cartesiano
    x = largura // 2 + int(raio * math.cos(angulo))
    y = altura // 2 + int(raio * math.sin(angulo))
    return x, y  

def criar_mapa(localidade_mapa, dispositivos, conexoes):
    #Ajustes gerais do mapa
    nome_mapa = f"Mapa da {localidade_mapa}"  
    largura = 7000  
    altura = 6000   

    # Estrutura básica do mapa a ser criado
    mapa = {
        "name": nome_mapa,
        "width": largura,
        "height": altura,
        "selements": [],  
        "links": []       
    }

    # Agrupar dispositivos por localidade
    localidades = defaultdict(list)  # Cria um dicionário onde cada chave é uma localidade e o valor é uma lista de dispositivos
    for hostname, info in dispositivos.items():
        localidades[info['localidade']].append(info)  

    # Ordenar localidade
    sorted_localidades = sorted(localidades.keys())

    total_locais = len(sorted_localidades)  # Número total de localidades
    espaco_horizontal_locais = largura // (total_locais + 1)  # Espaçamento horizontal entre localidades

    # Definir posição base para cada localidade de forma radial
    posicoes_localidades = {}  
    for idx, loc in enumerate(sorted_localidades):
        x_base, y_base = calcular_posicao_radia(largura, altura, idx, total_locais)  
        posicoes_localidades[loc] = (x_base, y_base)  
        print(f"Localidade '{loc}' posicionada em ({x_base}, {y_base})")  

    # Relaciona o id dos hosts com o id no mapa deles
    host_to_selementid = {}
    next_selementid = 1 

    # Busca os ids para todos os dispositivos
    print("Buscando hostids dos dispositivos no Zabbix...")
    for hostname, info in dispositivos.items():
        host = zabbix_api_call("host.get", {"filter": {"host": hostname}})
        if host and len(host) > 0:
            host_id = host[0]['hostid']  # Obtém o hostid do primeiro resultado
            dispositivos[hostname]['hostid'] = host_id 
            print(f"Encontrado {hostname} com hostid {host_id}.") 
        else:
            print(f"Host {hostname} não encontrado no Zabbix.")  
            dispositivos[hostname]['hostid'] = None  

    # Adicionar dispositivos ao mapa
    print("Adicionando elementos ao mapa...")
    for loc in sorted_localidades:
        x_base, y_base = posicoes_localidades[loc]  # Obtém a posição base da localidade

        # Separar dispositivos por tipo dentro da localidade
        tipos = defaultdict(list)
        for dispositivo in localidades[loc]:
            tipos[dispositivo['tipo']].append(dispositivo) 

        # Definir espaçamento horizontal e vertical dentro da localidade
        espaco_horizontal_dispositivos = 300  
        deslocamento_vertical_inicial = -600  

        # Itera sobre cada tipo de dispositivo para posicionamento
        for tipo in ['router', 'core', 'distribuicao', 'acesso', 'desconhecido']:
            dispositivos_tipo = tipos.get(tipo, [])  
            num_dispositivos = len(dispositivos_tipo)  
            if num_dispositivos == 0:
                continue  

            # Calcular espaçamento vertical com base no número de dispositivos
            espaco_vertical_dispositivos = 150  # Espaço vertical entre dispositivos do mesmo tipo

            # Itera sobre cada dispositivo do tipo atual para posicionamento
            for i, dispositivo in enumerate(dispositivos_tipo):
                hostname = dispositivo['hostname']  
                tipo_dispositivo = dispositivo['tipo']  
                host_id = dispositivo.get('hostid')  

                icon_id = TIPOS_ICONE.get(tipo_dispositivo, TIPOS_ICONE['desconhecido']) 

                # Cálculo para evitar sobreposição
                offset_x = (i - num_dispositivos / 2) * espaco_horizontal_dispositivos  
                offset_y = deslocamento_vertical_inicial + (i * espaco_vertical_dispositivos)  

                x = x_base + offset_x  
                y = y_base + offset_y  

                # Mapeia id dos hosts para selementid (identificador no mapa)
                selement_id = next_selementid  
                next_selementid += 1  

                if host_id:
                    host_to_selementid[host_id] = selement_id  
                else:
                    host_to_selementid[hostname] = selement_id  # Caso não haja host id, seleciona por hostname

                # Adiciona o elemento ao mapa
                mapa['selements'].append({
                    "selementid": selement_id,  
                    "elementtype": 0 if host_id else 2, 
                    "elements": [{"hostid": host_id}] if host_id else [],  
                    "x": x, 
                    "y": y, 
                    "iconid_off": icon_id, 
                    "iconid_on": icon_id    
                })
                print(f"Adicionado selementid {selement_id}: {hostname} na posição ({x}, {y}).")  

    # Adicionar conexões ao mapa
    print("Adicionando links ao mapa...")
    for source, targets in conexoes.items():
        for target in targets:
            source_info = dispositivos.get(source)  
            target_info = dispositivos.get(target)  
            if not source_info or not target_info:
                print(f"Erro: Dispositivo {source} ou {target} não encontrado.")  
                continue  

            source_hostid = source_info.get('hostid')  
            target_hostid = target_info.get('hostid')  

            # Obtém os selementids a partir de hostid ou hostname
            source_selementid = host_to_selementid.get(source_hostid) or host_to_selementid.get(source)
            target_selementid = host_to_selementid.get(target_hostid) or host_to_selementid.get(target)

            if not source_selementid or not target_selementid:
                print(f"Erro: selementid para {source} ou {target} não encontrado.") 
                continue 

            # Evita conexões duplicadas
            existente = any(
                (link["selementid1"] == source_selementid and link["selementid2"] == target_selementid) or
                (link["selementid1"] == target_selementid and link["selementid2"] == source_selementid)
                for link in mapa['links']
            )
            if existente:
                continue  

            # Adicionar o link ao mapa
            mapa['links'].append({
                "selementid1": source_selementid,  
                "selementid2": target_selementid,  
                "drawtype": 2,      # Estilo da linha de link (linha reta)
                "color": "00AA00",  # Cor do link
                "width": 1,          
                "label": ""         
            })
            print(f"Adicionado link entre {source} (selementid {source_selementid}) e {target} (selementid {target_selementid}).")  

    # Criar o mapa no Zabbix via API
    print(f"Criando o mapa '{nome_mapa}' no Zabbix...")
    mapa_criado = zabbix_api_call("map.create", mapa)  
    if mapa_criado:
        print(f"Mapa '{nome_mapa}' criado com sucesso. ID do mapa: {mapa_criado}")  
    else:
        print(f"Erro ao criar o mapa: {mapa_criado}")  

def main():
    # Verifica se o arquivo JSON existe
    if not os.path.exists(JSON_REDE_PATH):
        print(f"Arquivo JSON não encontrado em {JSON_REDE_PATH}. Verifique o caminho.") 
        return  

    # Carregar a estrutura JSON
    try:
        with open(JSON_REDE_PATH, 'r') as file:
            json_rede = json.load(file)  
        print(f"Arquivo JSON de rede carregado com sucesso de {JSON_REDE_PATH}.")  
    except Exception as e:
        print(f"Erro ao ler o arquivo JSON: {e}")  
        return  

    # Processa a estrutura JSON para obter dispositivos e conexões
    dispositivos, conexoes = processar_json(json_rede)

    # Criar o mapa no Zabbix com base nos dispositivos e conexões processados
    localidade_mapa = "Mapa Universal"  # Nome do mapa 
    criar_mapa(localidade_mapa, dispositivos, conexoes)

if __name__ == "__main__":
    main()  
