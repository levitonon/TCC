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
    # Routers
    if hostname.startswith('RT'):
        return 'router'
    # Switches
    elif hostname.startswith('SWC'):
        return 'core'
    elif hostname.startswith('SWD'):
        return 'distribuicao'
    elif hostname.startswith('SWA'):
        return 'acesso'
    return 'desconhecido'  # Caso exista algum fora do padrão

# Extração da localidade/site
def extrair_localidade(hostname):
    tipo = identificar_tipo(hostname)
    if tipo == 'router':
        return None  # RTs não têm uma localidade própria baseada no hostname
    partes = hostname.split('-')  # Divide o hostname baseado no caractere '-'
    if len(partes) >= 3:
        # Para hostnames como 'SWC-EP01-01', retorna 'EP01'
        return partes[1]
    elif len(partes) == 2:
        # Para hostnames como 'SWA-EP01', retorna 'EP01'
        return partes[1]
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
    conexoes = defaultdict(set)  # Dicionário para armazenar conexões entre dispositivos usando set para evitar duplicatas

    # Identificar os dispositivos e suas conexões
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
                # Não alteramos a localidade dos RTs aqui

            # Adiciona a conexão de hostname_atual para vizinho
            # Precisamos identificar o hostname_atual baseado no IP
            hostname_atual = None
            for h, info in dispositivos.items():
                if info['ip'] == ip:
                    hostname_atual = h
                    break

            if not hostname_atual:
                # Regra para detectar o router que possui 'RT' no nome
                rt_hosts = [h for h in dispositivos if h.startswith('RT')]
                if rt_hosts:
                    hostname_atual = rt_hosts[0]
                else:
                    print("Nenhum dispositivo RT encontrado para o IP:", ip)
                    continue  # Pula se não houver RT

            # Adiciona a conexão bidirecional
            if hostname_atual and hostname_atual != hostname:
                conexoes[hostname_atual].add(hostname)
                conexoes[hostname].add(hostname_atual)

    # Converter sets de vizinhos para listas
    for dispositivo in dispositivos.values():
        dispositivo['vizinhos'] = list(dispositivos['vizinhos']) if 'vizinhos' in dispositivos else []

    # Retornar dispositivos e conexoes sem alterar localidade dos RTs
    return dispositivos, conexoes

# Definição das camadas para layout hierárquico
CAMADAS = {
    'router': 1,
    'core': 2,
    'distribuicao': 3,
    'acesso': 4,
    'desconhecido': 5
}

# Cálculo da posição de cada dispositivo baseado na camada e ordem dentro da camada
def calcular_posicao_hierarquica(largura, altura, dispositivos_loc):
    """
    Calcula posições hierárquicas para os dispositivos dentro de uma localidade.
    RT no topo, seguido por SWC, SWD, SWA.
    Ajusta o espaçamento para caber no mapa reduzido.
    """
    # Agrupar dispositivos por camada
    camadas_dispositivos = defaultdict(list)
    for dispositivo in dispositivos_loc.values():
        camada = CAMADAS.get(dispositivo['tipo'], 5)
        camadas_dispositivos[camada].append(dispositivo)

    # Ordenar as camadas
    sorted_camadas = sorted(camadas_dispositivos.keys())

    posicoes = {}
    # Ajustar o espaçamento vertical para mapas menores
    espacamento_vertical = altura / (len(sorted_camadas) + 1)  # +1 para margens

    for camada in sorted_camadas:
        dispositivos_camada = camadas_dispositivos[camada]
        num_dispositivos = len(dispositivos_camada)
        # Ajustar ainda mais o espaçamento horizontal
        espacamento_horizontal = largura / (num_dispositivos + 1) if num_dispositivos > 0 else largura / 2
        y = espacamento_vertical * camada

        for idx, dispositivo in enumerate(dispositivos_camada, start=1):
            x = espacamento_horizontal * idx
            posicoes[dispositivo['hostname']] = (int(x), int(y))
            # Debug
            print(f"Dispositivo {dispositivo['hostname']} posicionado em ({int(x)}, {int(y)}) na camada {camada}")

    return posicoes

def criar_mapa(nome_mapa, dispositivos_loc, conexoes_loc, host_to_selementid, next_selementid):
    # Ajustes gerais do mapa
    largura = 2000  # Reduzido para diminuir o espaçamento
    altura = 1500  

    # Estrutura básica do mapa a ser criado
    mapa = {
        "name": nome_mapa,
        "width": largura,
        "height": altura,
        "selements": [],
        "links": []
    }

    # Calcula posições hierárquicas
    posicoes_dispositivos = calcular_posicao_hierarquica(largura, altura, dispositivos_loc)

    # Buscar os IDs dos dispositivos no Zabbix e adicionar elementos ao mapa
    print(f"Criando o mapa '{nome_mapa}' no Zabbix...")
    for hostname, info in dispositivos_loc.items():
        host = zabbix_api_call("host.get", {"filter": {"host": hostname}})
        if host and len(host) > 0:
            host_id = host[0]['hostid']  # Obtém o hostid do primeiro resultado
            dispositivos_loc[hostname]['hostid'] = host_id
            print(f"Encontrado {hostname} com hostid {host_id}.")
        else:
            print(f"Host {hostname} não encontrado no Zabbix.")
            dispositivos_loc[hostname]['hostid'] = None

    # Adicionar dispositivos ao mapa
    print("Adicionando elementos ao mapa...")
    for hostname, info in dispositivos_loc.items():
        tipo_dispositivo = info['tipo']
        host_id = info.get('hostid')

        icon_id = TIPOS_ICONE.get(tipo_dispositivo, TIPOS_ICONE['desconhecido'])

        # Obter posição hierárquica
        pos = posicoes_dispositivos.get(hostname, (0, 0))
        x, y = pos

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
    for source, targets in conexoes_loc.items():
        for target in targets:
            source_info = dispositivos_loc.get(source)
            target_info = dispositivos_loc.get(target)
            if not source_info or not target_info:
                print(f"Erro: Dispositivo {source} ou {target} não encontrado.")
                continue

            source_hostid = source_info.get('hostid')
            target_hostid = target_info.get('hostid')

            # Obtém os selementids a partir de hostid ou hostname
            source_selementid = host_to_selementid.get(source_hostid) if source_hostid else host_to_selementid.get(source)
            target_selementid = host_to_selementid.get(target_hostid) if target_hostid else host_to_selementid.get(target)

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
    mapa_criado = zabbix_api_call("map.create", mapa)
    if mapa_criado:
        print(f"Mapa '{nome_mapa}' criado com sucesso. ID do mapa: {mapa_criado}")
    else:
        print(f"Erro ao criar o mapa: {mapa_criado}")

    return next_selementid  # Retorna o próximo selementid para evitar conflitos

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

    # Agrupar dispositivos por localidade (SWC, SWD, SWA)
    localidades = defaultdict(dict)  # Cria um dicionário onde cada chave é uma localidade e o valor é um dict de dispositivos
    for hostname, info in dispositivos.items():
        tipo = info['tipo']
        localidade = info['localidade']
        if tipo in ['core', 'distribuicao', 'acesso'] and localidade:
            localidades[localidade][hostname] = info

    # Identificar todas as localidades
    sorted_localidades = sorted(localidades.keys())
    print(f"Total de localidades identificadas: {len(sorted_localidades)}")
    for loc in sorted_localidades:
        print(f"Localidade encontrada: {loc}")

    # Inicializar mapeamento de hostid para selementid e contador de IDs
    host_to_selementid = {}
    next_selementid = 1

    # Criar um mapa separado para cada localidade
    for loc in sorted_localidades:
        print(f"\nProcessando mapa para a localidade: {loc}")
        dispositivos_loc = localidades[loc].copy()  # Copia os dispositivos da localidade
        conexoes_loc = {}

        # Identificar RT(s) conectados aos SWC(s) da localidade
        swc_hosts = [host for host, info in localidades[loc].items() if info['tipo'] == 'core']
        rt_hosts = set()
        for swc in swc_hosts:
            conexoes_do_swc = conexoes.get(swc, set())
            for vizinho in conexoes_do_swc:
                if dispositivos.get(vizinho, {}).get('tipo') == 'router':
                    rt_hosts.add(vizinho)

        # Incluir RT(s) conectados à localidade
        for rt in rt_hosts:
            if rt not in dispositivos_loc and rt in dispositivos:
                dispositivos_loc[rt] = dispositivos[rt]
                dispositivos_loc[rt]['localidade'] = loc  # Atribuir a localidade correta
                print(f"RT '{rt}' adicionado à localidade '{loc}'.")
                # Adicionar conexões do RT dentro da localidade
                conexoes_do_rt = conexoes.get(rt, set())
                conexoes_loc[rt] = [t for t in conexoes_do_rt if t in dispositivos_loc]
                # Também, adicionar as conexões existentes do SWC para RT
                for swc in swc_hosts:
                    if swc in conexoes and rt in conexoes[swc]:
                        conexoes_loc[swc] = [t for t in conexoes[swc] if t in dispositivos_loc]

        # Filtrar conexões que estão **dentro** da localidade atual
        for source, targets in conexoes.items():
            if source in dispositivos_loc:
                filtered_targets = [t for t in targets if t in dispositivos_loc]
                if filtered_targets:
                    conexoes_loc[source] = filtered_targets

        # Nome do mapa baseado na localidade
        nome_mapa = f"Mapa_{loc}"

        # Chamar a função de criação de mapa para a localidade atual
        next_selementid = criar_mapa(nome_mapa, dispositivos_loc, conexoes_loc, host_to_selementid, next_selementid)

    print("\nTodos os mapas por localidade foram processados.")

if __name__ == "__main__":
    main()
