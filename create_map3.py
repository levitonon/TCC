import requests
import json
import math

# URL e token da API do Zabbix fornecidos
ZABBIX_API_URL = "http://192.168.0.225/api_jsonrpc.php"
AUTH_TOKEN = "9016c2e484b954ef43f2adf98e69c4a0"
RT_IP = "192.168.0.69"  # IP do seu roteador

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
            "selements": elements,
            "links": links
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
    
    elements = []
    links = []
    host_ids = {}

    # Obter ID do RT
    rt_id = get_host_id_by_ip(AUTH_TOKEN, RT_IP)
    if rt_id is None:
        print(f"Erro ao obter o ID do RT com IP {RT_IP}.")
        return

    # Definir posição do RT
    rt_position = (400, 300)
    elements.append({
        "selementid": rt_id,
        "elements": [{"hostid": rt_id}],
        "elementtype": 0,
        "iconid_off": "1",
        "label": "RT",
        "x": rt_position[0],
        "y": rt_position[1]
    })

    # Definir ângulo e distância para o posicionamento dos outros dispositivos
    distance_from_rt = 150  # Distância do RT para os dispositivos
    angle_step = (2 * math.pi) / len(network_graph)

    # Obter IDs dos hosts e criar os elementos
    for idx, (device_ip, neighbors) in enumerate(network_graph.items()):
        if device_ip == RT_IP:
            continue  # Pular o RT

        host_id = get_host_id_by_ip(AUTH_TOKEN, device_ip)
        print(f"Host ID for {device_ip}: {host_id}")  # Verificação

        if host_id:
            host_ids[device_ip] = host_id
            
            # Calcular a posição do switch
            angle = idx * angle_step
            x = rt_position[0] + int(distance_from_rt * math.cos(angle))
            y = rt_position[1] + int(distance_from_rt * math.sin(angle))

            elements.append({
                "selementid": host_id,
                "elements": [{"hostid": host_id}],
                "elementtype": 0,
                "iconid_off": "1",
                "label": device_ip,
                "x": x,
                "y": y
            })

            # Criar links (conexões) com os vizinhos
            for neighbor in neighbors:
                neighbor_ip = neighbor["ip"]
                neighbor_host_id = get_host_id_by_ip(AUTH_TOKEN, neighbor_ip)
                if neighbor_host_id:
                    links.append({
                        "selementid1": host_id,
                        "selementid2": neighbor_host_id,
                        "drawtype": 2,
                        "color": "00AA00"
                    })
                else:
                    print(f"Erro ao obter o ID do vizinho {neighbor_ip} para {device_ip}.")

    # Criar o mapa no Zabbix
    map_name = "Network Topology Map"
    response = create_map(AUTH_TOKEN, map_name, elements, links)

    if 'result' in response:
        print(f"Mapa '{map_name}' criado com sucesso no Zabbix!")
    else:
        print(f"Erro ao criar o mapa: {response}")

# Exemplo de uso
create_zabbix_network_map("/home/osboxes/TCCPYTHON/network_graph.json")
