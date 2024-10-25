import json
import requests

# Configurações da API Zabbix
ZABBIX_API_URL = "http://192.168.0.225/api_jsonrpc.php"
AUTH_TOKEN = None  # Inicializa o token de autenticação como None
headers = {'Content-Type': 'application/json'}

# Login
data = {
    "jsonrpc": "2.0",
    "method": "user.login",
    "params": {
        "user": "Admin",
        "password": "zabbix"
    },
    "id": 1
}

response = requests.post(ZABBIX_API_URL, headers=headers, json=data)
print(response.json())
# Função para fazer chamadas à API do Zabbix
def zabbix_api_call(method, params):
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "auth": AUTH_TOKEN,  # Usar AUTH_TOKEN aqui
        "id": 1
    }

    response = requests.post(ZABBIX_API_URL, headers=headers, json=payload)
    response_json = response.json()

    # Verifica se a chamada foi bem-sucedida
    if 'error' in response_json:
        print(f"Erro na chamada da API: {response_json['error']}")
    return response_json

# Função para autenticar na API do Zabbix
def autenticar_api(usuario, senha):
    global AUTH_TOKEN
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "user": usuario,
            "password": senha
        },
        "id": 1
    }
    response = requests.post(ZABBIX_API_URL, json=payload)
    response_json = response.json()
    if 'result' in response_json:
        AUTH_TOKEN = response_json['result']
        print("Autenticação bem-sucedida. Token de autenticação obtido.")
    else:
        print("Falha na autenticação.")

# Função para extrair a localidade de um hostname
def extrair_localidade(hostname):
    partes = hostname.split('-')
    if len(partes) > 1:
        return partes[1]  # Retorna a parte que indica a localidade
    return None

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
def criar_mapa(localidade, dispositivos, links):
    nome_mapa = f"Mapa da Localidade {localidade}"
    largura = 800  # largura do mapa
    altura = 600   # altura do mapa

    mapa = {
        "name": nome_mapa,
        "width": largura,
        "height": altura,
        "selements": [],
        "links": links  # Adiciona os links aqui
    }

    # Coordenadas iniciais
    x_positions = {'core': 100, 'distribuicao': 200, 'acesso': 300}
    y_positions = {'core': 100, 'distribuicao': 200, 'acesso': 300}
    espaco_horizontal = 150  # Espaço entre elementos

    # Adicionar elementos ao mapa
    for tipo in ['router', 'core', 'distribuicao', 'acesso']:
        for i, switch in enumerate(dispositivos[tipo]):
            host = zabbix_api_call("host.get", {"filter": {"name": switch['hostname']}})
            if host and 'result' in host and len(host['result']) > 0:
                host_id = host['result'][0]['hostid']
                mapa['selements'].append({
                    'elements': [{'hostid': host_id}],
                    'elementtype': 0,  # Tipo do elemento (host)
                    'x': x_positions[tipo] + i * espaco_horizontal,
                    'y': y_positions[tipo],
                    'iconid_off': TIPOS_ICONE[tipo],  # ID do ícone para o elemento
                    'iconid_on': TIPOS_ICONE[tipo]    # ID do ícone quando ativo (opcional)
                })
                print(f"Adicionado {switch['hostname']} com ID {host_id} ao mapa {nome_mapa}.")
            else:
                print(f"Host {switch['hostname']} não encontrado no Zabbix.")

    # Criar o mapa no Zabbix
    mapa_criado = zabbix_api_call("map.create", mapa)
    if 'result' in mapa_criado:
        print(f"Mapa '{nome_mapa}' criado com sucesso.")
    else:
        print(f"Erro ao criar o mapa: {mapa_criado}")

# Carregar o arquivo JSON
try:
    with open('network_graph.json') as f:  # Certifique-se de que o nome do arquivo está correto
        rede = json.load(f)
except FileNotFoundError:
    print("Arquivo 'network_graph.json' não encontrado.")
    exit(1)

# Organizando switches por localidade
localidades = {}
links = []  # Lista para armazenar os links

for ip, vizinhos in rede.items():
    for vizinho in vizinhos:
        hostname = vizinho['hostname']
        localidade = extrair_localidade(hostname)
        if localidade:
            # Cria um dicionário para a localidade se não existir
            if localidade not in localidades:
                localidades[localidade] = {'router': [], 'core': [], 'distribuicao': [], 'acesso': []}
            
            # Adiciona o switch à lista correspondente
            tipo = identificar_tipo(hostname)
            if tipo in localidades[localidade]:
                localidades[localidade][tipo].append(vizinho)

            # Adiciona os links entre o dispositivo atual e seus vizinhos
            for neighbor in vizinhos:
                neighbor_ip = neighbor["ip"]
                neighbor_host = zabbix_api_call("host.get", {"filter": {"ip": neighbor_ip}})
                if neighbor_host and 'result' in neighbor_host and len(neighbor_host['result']) > 0:
                    neighbor_host_id = neighbor_host['result'][0]['hostid']
                    links.append({
                        "selementid1": "",
                        "selementid2": neighbor_host_id,
                        "drawtype": 2,  # Estilo da linha de link
                        "color": "00AA00"  # Cor do link (verde)
                    })

# Criar um mapa para cada localidade
for localidade, dispositivos in localidades.items():
    print(f"Criando mapa para a localidade: {localidade}")
    criar_mapa(localidade, dispositivos, links)

# Autenticar na API do Zabbix antes de continuar
usuario = "Admin"  # Insira seu nome de usuário
senha = "zabbix"      # Insira sua senha
autenticar_api(usuario, senha)
