import json
import requests
import os
from collections import defaultdict
import math

# Configurações da API Zabbix
ZABBIX_API_URL = "http://192.168.0.225/api_jsonrpc.php"
AUTH_TOKEN = "9016c2e484b954ef43f2adf98e69c4a0"  # Atualize com seu token válido

# Caminho para o arquivo JSON da rede
JSON_REDE_PATH = "/home/osboxes/arquivos_tcc/network_graph.json"  # Caminho atualizado

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

    try:
        response = requests.post(ZABBIX_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()

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

# Função para identificar o tipo de dispositivo
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

# Função para extrair a localidade do hostname
def extrair_localidade(hostname):
    partes = hostname.split('-')
    if len(partes) >= 2:
        return partes[1]
    return 'UNICA'  # Caso a localidade não esteja presente ou não siga o padrão

# Mapeamento de tipos de ícones (todos os switches usam 155)
TIPOS_ICONE = {
    'router': 130,       # ID do ícone para o roteador
    'core': 155,         # ID do ícone para switches core
    'distribuicao': 155, # ID do ícone para switches de distribuição
    'acesso': 155,       # ID do ícone para switches de acesso
    'desconhecido': 158  # ID padrão para desconhecido (ajustar conforme necessário)
}

# Função para processar a estrutura JSON e extrair dispositivos e conexões
def processar_json(json_rede):
    dispositivos = {}
    conexoes = defaultdict(list)

    # Identificar todos os dispositivos e seus tipos
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
                # Atualiza informações se necessário
                dispositivos[hostname]['ip'] = ip_vizinho
                dispositivos[hostname]['tipo'] = tipo
                dispositivos[hostname]['localidade'] = localidade

    # Preencher as conexões
    for ip, vizinhos in json_rede.items():
        # Identificar o hostname correspondente a este IP
        hostname_atual = None
        for hostname, info in dispositivos.items():
            if info['ip'] == ip:
                hostname_atual = hostname
                break

        if not hostname_atual:
            # Caso o IP atual não corresponda a nenhum dispositivo listado, assumimos que ele representa o roteador
            # Adiciona o roteador caso não exista
            if "RT" not in dispositivos:
                dispositivos["RT"] = {
                    'hostname': "RT",
                    'ip': ip,
                    'tipo': identificar_tipo("RT"),
                    'localidade': 'UNICA',
                    'vizinhos': set()
                }
            hostname_atual = "RT"

        # Adicionar vizinhos
        for vizinho in vizinhos:
            conexoes[hostname_atual].append(vizinho['hostname'])
            dispositivos[hostname_atual]['vizinhos'].add(vizinho['hostname'])

    # Converter sets para listas
    for dispositivo in dispositivos.values():
        dispositivo['vizinhos'] = list(dispositivo['vizinhos'])

    return dispositivos, conexoes

# Função para calcular a posição de cada localidade de forma radial
def calcular_posicao_radia(largura, altura, index, total, raio_inicial=300, delta_raio=200):
    if total == 0:
        return largura // 2, altura // 2
    # Calcular o ângulo para a localidade atual
    angulo = (2 * math.pi / total) * index
    raio = raio_inicial + (delta_raio * (index // 4))  # Ajustar o raio conforme necessário

    x = largura // 2 + int(raio * math.cos(angulo))
    y = altura // 2 + int(raio * math.sin(angulo))
    return x, y

# Função para criar o mapa no Zabbix
def criar_mapa(localidade_mapa, dispositivos, conexoes):
    nome_mapa = f"Mapa da Localidade {localidade_mapa}"
    largura = 2000  # Aumentado para 2000
    altura = 1200    # Aumentado para 1200

    mapa = {
        "name": nome_mapa,
        "width": largura,
        "height": altura,
        "selements": [],
        "links": []
    }

    # Agrupar dispositivos por localidade
    localidades = defaultdict(list)
    for hostname, info in dispositivos.items():
        localidades[info['localidade']].append(info)

    # Ordenar localidades para consistência
    sorted_localidades = sorted(localidades.keys())

    total_locais = len(sorted_localidades)
    espaco_horizontal_locais = largura // (total_locais + 1)

    # Definir posição base para cada localidade de forma radial
    posicoes_localidades = {}
    for idx, loc in enumerate(sorted_localidades):
        x_base, y_base = calcular_posicao_radia(largura, altura, idx, total_locais)
        posicoes_localidades[loc] = (x_base, y_base)

    # Mapeamento de hostid para selementid
    host_to_selementid = {}
    next_selementid = 1  # Iniciar ID dos selements

    # Buscar os hostids para todos os dispositivos
    print("Buscando hostids dos dispositivos no Zabbix...")
    for hostname, info in dispositivos.items():
        host = zabbix_api_call("host.get", {"filter": {"host": hostname}})
        if host and len(host) > 0:
            host_id = host[0]['hostid']
            dispositivos[hostname]['hostid'] = host_id
            print(f"Encontrado {hostname} com hostid {host_id}.")
        else:
            print(f"Host {hostname} não encontrado no Zabbix.")
            dispositivos[hostname]['hostid'] = None

    # Adicionar selements ao mapa com posicionamento aprimorado
    print("Adicionando elementos ao mapa...")
    for loc in sorted_localidades:
        x_base, y_base = posicoes_localidades[loc]

        # Separar dispositivos por tipo dentro da localidade
        tipos = defaultdict(list)
        for dispositivo in localidades[loc]:
            tipos[dispositivo['tipo']].append(dispositivo)

        # Definir espaçamento horizontal dentro da localidade
        espaco_horizontal_dispositivos = 150  # Espaço horizontal entre dispositivos do mesmo tipo

        for tipo in ['router', 'core', 'distribuicao', 'acesso', 'desconhecido']:
            dispositivos_tipo = tipos.get(tipo, [])
            for i, dispositivo in enumerate(dispositivos_tipo):
                hostname = dispositivo['hostname']
                tipo_dispositivo = dispositivo['tipo']
                host_id = dispositivo.get('hostid')

                icon_id = TIPOS_ICONE.get(tipo_dispositivo, TIPOS_ICONE['desconhecido'])

                # Calcular posição y baseada no tipo
                posicao_tipo = {
                    'router': y_base,
                    'core': y_base + 150,
                    'distribuicao': y_base + 300,
                    'acesso': y_base + 450,
                    'desconhecido': y_base + 600
                }
                y = posicao_tipo.get(tipo_dispositivo, y_base + 600)

                # Calcular posição x com espaçamento para múltiplos dispositivos do mesmo tipo
                x = x_base + (i - len(dispositivos_tipo) / 2) * espaco_horizontal_dispositivos

                # Mapear hostid para selementid
                selement_id = next_selementid
                next_selementid += 1

                if host_id:
                    host_to_selementid[host_id] = selement_id
                else:
                    host_to_selementid[hostname] = selement_id  # Usar hostname se hostid não disponível

                # Adicionar elemento
                mapa['selements'].append({
                    "selementid": selement_id,
                    "elementtype": 0 if host_id else 2,  # 0 para host, 2 para textual
                    "elements": [{"hostid": host_id}] if host_id else [],
                    "x": x,
                    "y": y,
                    "iconid_off": icon_id,
                    "iconid_on": icon_id
                })
                print(f"Adicionado selementid {selement_id}: {hostname} na posição ({x}, {y}).")

    # Adicionar links (conexões) ao mapa
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

            source_selementid = host_to_selementid.get(source_hostid) or host_to_selementid.get(source)
            target_selementid = host_to_selementid.get(target_hostid) or host_to_selementid.get(target)

            if not source_selementid or not target_selementid:
                print(f"Erro: selementid para {source} ou {target} não encontrado.")
                continue

            # Evitar duplicatas
            existente = any(
                (link["selementid1"] == source_selementid and link["selementid2"] == target_selementid) or
                (link["selementid1"] == target_selementid and link["selementid2"] == source_selementid)
                for link in mapa['links']
            )
            if existente:
                continue

            # Adicionar link
            mapa['links'].append({
                "selementid1": source_selementid,
                "selementid2": target_selementid,
                "drawtype": 2,      # Estilo da linha de link
                "color": "00AA00",  # Cor do link (verde)
                "width": 1,
                "label": ""         # Opcional: adicionar rótulo
            })
            print(f"Adicionado link entre {source} (selementid {source_selementid}) e {target} (selementid {target_selementid}).")

    # Criar o mapa no Zabbix
    print(f"Criando o mapa '{nome_mapa}' no Zabbix...")
    mapa_criado = zabbix_api_call("map.create", mapa)
    if mapa_criado:
        print(f"Mapa '{nome_mapa}' criado com sucesso. ID do mapa: {mapa_criado}")
    else:
        print(f"Erro ao criar o mapa: {mapa_criado}")

def main():
    # Verificar se o arquivo JSON existe
    if not os.path.exists(JSON_REDE_PATH):
        print(f"Arquivo JSON não encontrado em {JSON_REDE_PATH}. Verifique o caminho.")
        return

    # Carregar a estrutura JSON da rede
    try:
        with open(JSON_REDE_PATH, 'r') as file:
            json_rede = json.load(file)
        print(f"Arquivo JSON de rede carregado com sucesso de {JSON_REDE_PATH}.")
    except Exception as e:
        print(f"Erro ao ler o arquivo JSON: {e}")
        return

    # Processar a estrutura JSON
    dispositivos, conexoes = processar_json(json_rede)

    # Criar o mapa no Zabbix
    localidade_mapa = "Mapa Universal"  # Você pode parametrizar isso conforme a necessidade
    criar_mapa(localidade_mapa, dispositivos, conexoes)

if __name__ == "__main__":
    main()
