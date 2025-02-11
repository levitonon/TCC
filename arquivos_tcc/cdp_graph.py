import json
import time
import subprocess
from netmiko import ConnectHandler

# Informações para acesso do dispositivo central
devices = {
    "my_router": {  
        "device_type": "cisco_ios",  
        "host": "192.168.0.69",      
        "username": "Admin",         
        "password": "Eve",           
    }
}

# Lista para armazenar vizinhos descobertos (para evitar recursões já feitas)
discovered_neighbors = []

# Dicionário para armazenar o grafo da rede
network_graph = {}

# Captura os vizinhos CDP de um dispositivo e retorna uma lista de vizinhos.
def capture_neighbors(device):
    print(f"Conectando a {device['host']}...")    
    connection = ConnectHandler(**device)
    
    # Execução do comando
    output = connection.send_command("show cdp neighbors detail")
    neighbors = []  # Lista para armazenar os vizinhos encontrados

    hostname = None
    ip = None
    
    # Análise simples do output para capturar hostname e IP
    for line in output.splitlines():
        if "Device ID:" in line:
            # Extrai o hostname do vizinho
            hostname = line.split("Device ID: ")[1].strip()
            # Remove o sufixo ".cisco.com" do hostname, se presente
            hostname = hostname.replace(".cisco.com", "")
        if "IP address:" in line:
            # Extrai o endereço IP do vizinho
            ip = line.split("IP address: ")[1].strip()
            # Adiciona na lista
            neighbors.append({"hostname": hostname, "ip": ip})
    
    connection.disconnect() 
    return neighbors

# Função recursiva para descobrir todos os vizinhos
def recursive_discovery(device):
    global discovered_neighbors, network_graph
    
    # Captura os vizinhos do dispositivo atual
    new_neighbors = capture_neighbors(device)
    
    # Chave representa o endereço IP do dispositivo atual
    current_device_ip = device["host"]
    
    # Cria a chave no dict do grafo se ainda não existir
    if current_device_ip not in network_graph:
        network_graph[current_device_ip] = []
    
    for neighbor in new_neighbors:
        # Primeiro, registra no grafo a relação (mesmo que já tenha sido descoberto antes)
        adjacency = {"hostname": neighbor["hostname"], "ip": neighbor["ip"]}
        if adjacency not in network_graph[current_device_ip]:
            network_graph[current_device_ip].append(adjacency)
        
        # Se o vizinho ainda não foi explorado antes, faz a recursão
        if neighbor not in discovered_neighbors:
            print(f"Descoberto novo vizinho: {neighbor['hostname']} - {neighbor['ip']}")
            discovered_neighbors.append(neighbor)
            
            # Credenciais de conexão para o novo vizinho
            neighbor_device = {
                "device_type": "cisco_ios",
                "host": neighbor["ip"],
                "username": "Admin",
                "password": "Eve",
            }
            print(f"Acessando novos vizinhos de {neighbor['hostname']}...")
            recursive_discovery(neighbor_device)
        else:
            print(f"{neighbor['hostname']} já foi descoberto.")
    
    # Se não houverem vizinhos novos, imprime uma informação
    if not new_neighbors:
        print(f"{current_device_ip} não tem novos vizinhos.")

# Inicia a descoberta a partir do dispositivo central
recursive_discovery(devices["my_router"])

# Formata a lista de vizinhos para salvar em JSON
formatted_neighbors = [
    {"hostname": neighbor["hostname"], "ip": neighbor["ip"]} 
    for neighbor in discovered_neighbors
]

# Salva a lista de vizinhos descobertos em JSON
json_file_path = "discovered_neighbors.json"
with open(json_file_path, "w") as f:
    json.dump(formatted_neighbors, f, indent=4)

print("Lista de vizinhos descobertos:")
print(json.dumps(formatted_neighbors, indent=4))

# Salva o grafo da rede em JSON
graph_file_path = "network_graph.json"
with open(graph_file_path, "w") as f:
    json.dump(network_graph, f, indent=4)

print("Grafo da rede:")
print(json.dumps(network_graph, indent=4))

# Executa playbook Ansible (caso necessário)
ansible_playbook = "zabbixreadertest.yml"

try:
    print("Executando o playbook Ansible para adicionar hosts no Zabbix...")
    subprocess.run(["ansible-playbook", ansible_playbook], check=True)
    print("Playbook Ansible executado com sucesso.")
except subprocess.CalledProcessError as e:
    print(f"Erro ao executar o playbook Ansible: {e}")
