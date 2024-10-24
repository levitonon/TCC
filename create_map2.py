import requests
import json

# URL e token da API do Zabbix fornecidos
ZABBIX_API_URL = "http://192.168.0.225/api_jsonrpc.php"
AUTH_TOKEN = "9016c2e484b954ef43f2adf98e69c4a0"

# Função para obter o ID de um host no Zabbix pelo seu IP
def get_host_id_by_ip(auth_token, ip):
    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid"],
            "filter": {
                "ip": [ip]
            }
        },
        "auth": auth_token,
        "id": 1
    }
    response = requests.post(ZABBIX_API_URL, json=payload)
    result = response.json().get("result")
    if result:
        return result[0]["hostid"]
    else:
        return None

# Função para criar o mapa no Zabbix
def create_map(auth_token, map_name, elements, links):
    payload = {
        "jsonrpc": "2.0",
        "method": "map.create",
        "params": {
            "name": map_name,
            "width": 800,
            "height": 600,
            "selements": elements,  # Elementos do mapa (hosts)
            "links": links          # Links (conexões entre os dispositivos)
        },
        "auth": auth_token,
        "id": 1
    }
    response = requests.post(ZABBIX_API_URL, json=payload)
    return response.json()

# Função principal que lê o grafo JSON e cria o mapa no Zabbix
def create_zabbix_network_map(graph_file):
    # Carregar o grafo da rede do arquivo JSON
    with open(graph_file, "r") as f:
        network_graph = json.load(f)
    
    elements = []  # Elementos do mapa (hosts)
    links = []     # Links (conexões entre hosts)
    host_ids = {}  # Dicionário para armazenar os IDs dos hosts

    # Variáveis para o espaçamento dos elementos no mapa
    x_offset = 0
    y_offset = 0
    spacing = 150  # Espaçamento entre os elementos

    # Obter IDs dos hosts e criar os elementos
    for device_ip, neighbors in network_graph.items():
        host_id = get_host_id_by_ip(AUTH_TOKEN, device_ip)
        if host_id:
            host_ids[device_ip] = host_id
            # Adiciona o dispositivo como elemento do mapa
            elements.append({
                "selementid": host_id,
                "elements": [{"hostid": host_id}],
                "elementtype": 0,  # Tipo: host
                "iconid_off": "1",  # ID do ícone no Zabbix
                "label": device_ip,
                "x": x_offset,      # Posição X
                "y": y_offset       # Posição Y
            })

            # Criar links (conexões) com os vizinhos
            for neighbor in neighbors:
                neighbor_ip = neighbor["ip"]
                neighbor_host_id = get_host_id_by_ip(AUTH_TOKEN, neighbor_ip)
                if neighbor_host_id:
                    links.append({
                        "selementid1": host_ids[device_ip],
                        "selementid2": neighbor_host_id,
                        "drawtype": 2,  # Estilo da linha de link
                        "color": "00AA00"  # Cor do link (verde)
                    })

            # Atualiza a posição Y para o próximo dispositivo
            y_offset += spacing
            # Reseta o offset X e aumenta o Y para a próxima linha se necessário
            if y_offset >= 600:  # Limite de altura do mapa
                y_offset = 0
                x_offset += spacing

    # Criar o mapa no Zabbix
    map_name = "Network Topology Map"
    response = create_map(AUTH_TOKEN, map_name, elements, links)

    if 'result' in response:
        print(f"Mapa '{map_name}' criado com sucesso no Zabbix!")
    else:
        print(f"Erro ao criar o mapa: {response}")

# Exemplo de uso
create_zabbix_network_map("/home/osboxes/TCCPYTHON/network_graph.json")
