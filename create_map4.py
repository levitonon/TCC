import json
import requests

# Configurações da API Zabbix
ZABBIX_API_URL = "http://192.168.0.225/api_jsonrpc.php"
AUTH_TOKEN = "9016c2e484b954ef43f2adf98e69c4a0"

# Função para fazer chamadas à API do Zabbix
def zabbix_api_call(method, params):
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "auth": AUTH_TOKEN,
        "id": 1
    }
    
    response = requests.post(ZABBIX_API_URL, headers=headers, json=payload)
    response_json = response.json()
    
    # Verifica se a chamada foi bem-sucedida
    if 'error' in response_json:
        print(f"Erro na chamada da API: {response_json['error']}")
    return response_json

# Função para identificar o tipo de switch
def identificar_tipo(hostname):
    if hostname.startswith('RT'):
        return 'router'
    elif hostname.startswith('SWC'):
        return 'core'
    elif hostname.startswith('SWD'):
        return 'distribuicao'
    elif hostname.startswith('SWA'):
        return 'acesso'
    return 'desconhecido'

# Mapeamento de tipos de ícones
TIPOS_ICONE = {
    'router': 130,          # ID do ícone para o roteador
    'core': 155,            # ID do ícone para o core switch
    'distribuicao': 155,    # ID do ícone para switch de distribuição
    'acesso': 155            # ID do ícone para switch de acesso
}

# Função para criar o mapa no Zabbix
def criar_mapa(localidade, dispositivos):
    nome_mapa = f"Mapa da Localidade {localidade}"
    largura = 800  # largura do mapa
    altura = 600   # altura do mapa

    mapa = {
        "name": nome_mapa,
        "width": largura,
        "height": altura,
        "selements": [],
        "links": []
    }

    # Coordenadas iniciais
    x_positions = {'core': 100, 'distribuicao': 100, 'acesso': 100}
    y_positions = {'core': 100, 'distribuicao': 200, 'acesso': 300}
    espaco_horizontal = 150  # Espaço entre elementos

    # Mapeamento de IDs dos hosts
    host_ids = {}

    # Adicionar elementos ao mapa e armazenar os IDs
    for tipo in ['router', 'core', 'distribuicao', 'acesso']:
        if tipo in dispositivos:  # Verifique se o tipo existe em dispositivos
            for i, switch in enumerate(dispositivos[tipo]):
                # Verifique se switch é um dicionário e contém 'hostname'
                if isinstance(switch, dict) and 'hostname' in switch:
                    hostname = switch['hostname']
                    # Verifica se o hostname está no formato esperado
                    split_hostname = hostname.split('-')
                    if len(split_hostname) < 2:
                        print(f"Hostname '{hostname}' não está no formato esperado.")
                        continue  # Ignora este switch se o formato estiver errado
                    
                    host = zabbix_api_call("host.get", {"filter": {"name": hostname}})
                    if host and 'result' in host and len(host['result']) > 0:
                        host_id = host['result'][0]['hostid']
                        host_ids[hostname] = host_id  # Armazena o ID do host
                        mapa['selements'].append({
                            'elements': [{'hostid': host_id}],
                            'elementtype': 0,  # Tipo do elemento (host)
                            'x': x_positions[tipo] + i * espaco_horizontal,
                            'y': y_positions[tipo],
                            'iconid_off': TIPOS_ICONE[tipo],
                            'iconid_on': TIPOS_ICONE[tipo]
                        })
                        print(f"Adicionado {hostname} com ID {host_id} ao mapa {nome_mapa}.")
                    else:
                        print(f"Host {hostname} não encontrado no Zabbix.")
                else:
                    print(f"Switch {switch} não é um dicionário ou não possui 'hostname'.")

    # Adicionar conexões entre os dispositivos
    for hostname, id_host in host_ids.items():
        print(f"Verificando vizinhos para {hostname}.")
        if hostname.startswith('RT'):  # Se for um roteador
            # Obtém os vizinhos do dispositivo
            # Certifique-se de que a estrutura para vizinhos esteja correta
            neighbors = dispositivos['router'].get(hostname, {}).get('vizinhos', [])
            print(f"Vizinhos de {hostname}: {neighbors}")

            for neighbor in neighbors:
                neighbor_host = zabbix_api_call("host.get", {"filter": {"name": neighbor}})
                if neighbor_host and 'result' in neighbor_host and len(neighbor_host['result']) > 0:
                    neighbor_host_id = neighbor_host['result'][0]['hostid']
                    # Adiciona o link ao mapa
                    mapa['links'].append({
                        "selementid1": id_host,  # ID do host atual
                        "selementid2": neighbor_host_id,  # ID do vizinho
                        "drawtype": 2,  # Estilo da linha de link
                        "color": "00AA00"  # Cor do link (verde)
                    })
                    print(f"Adicionando link entre {hostname} e {neighbor}.")
                else:
                    print(f"Vizinho {neighbor} não encontrado no Zabbix.")

    # Criar o mapa no Zabbix
    mapa_criado = zabbix_api_call("map.create", mapa)
    if 'result' in mapa_criado:
        print(f"Mapa '{nome_mapa}' criado com sucesso.")
    else:
        print(f"Erro ao criar o mapa: {mapa_criado}")

