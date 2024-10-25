import json
import time
import subprocess
from netmiko import ConnectHandler

# Definindo as credenciais e informações dos switches
devices = {
    "my_router": {
        "device_type": "cisco_ios",
        "host": "192.168.0.69",
        "username": "Admin",
        "password": "Eve",
    }
}

# Lista para armazenar vizinhos descobertos
discovered_neighbors = []
# Dicionário para armazenar o grafo da rede
network_graph = {}

def capture_neighbors(device):
    """Captura os vizinhos CDP de um dispositivo e retorna uma lista de vizinhos."""
    print(f"Conectando a {device['host']}...")
    connection = ConnectHandler(**device)
    
    output = connection.send_command("show cdp neighbors detail")
    neighbors = []

    # Extraindo informações de vizinhos do output
    for line in output.splitlines():
        if "Device ID:" in line:
            hostname = line.split("Device ID: ")[1].strip()
            # Remove "cisco.com" do hostname
            hostname = hostname.replace(".cisco.com", "")
        if "IP address:" in line:
            ip = line.split("IP address: ")[1].strip()
            neighbors.append({"hostname": hostname, "ip": ip})
    
    connection.disconnect()
    return neighbors

def recursive_discovery(device):
    """Realiza a descoberta recursiva de vizinhos CDP."""
    global discovered_neighbors, network_graph
    new_neighbors = capture_neighbors(device)
    
    # Nome do dispositivo atual (baseado no IP)
    current_device = device['host']

    # Adiciona o dispositivo atual ao grafo com seus vizinhos
    if current_device not in network_graph:
        network_graph[current_device] = []

    # Filtrar novos vizinhos
    for neighbor in new_neighbors:
        if neighbor not in discovered_neighbors:
            print(f"Descoberto novo vizinho: {neighbor['hostname']} - {neighbor['ip']}")
            discovered_neighbors.append(neighbor)

            # Adicionar vizinho ao grafo do dispositivo atual
            network_graph[current_device].append({"hostname": neighbor["hostname"], "ip": neighbor["ip"]})

            # Chamada recursiva para capturar vizinhos do novo dispositivo
            neighbor_device = {
                "device_type": "cisco_ios",
                "host": neighbor['ip'],
                "username": "Admin",
                "password": "Eve",
            }
            print(f"Acessando novos vizinhos de {neighbor['hostname']}...")
            recursive_discovery(neighbor_device)
        else:
            print(f"{neighbor['hostname']} já foi descoberto.")

    # Verifica se não há novos vizinhos
    if not new_neighbors:
        print(f"{device['host']} não tem novos vizinhos.")

# Executa a descoberta a partir do roteador inicial
recursive_discovery(devices["my_router"])

# Salva a lista de vizinhos em um arquivo JSON
# Ajustando a estrutura do JSON para hostname e ip
formatted_neighbors = [{"hostname": neighbor["hostname"], "ip": neighbor["ip"]} for neighbor in discovered_neighbors]

json_file_path = "discovered_neighbors.json"
with open(json_file_path, "w") as f:
    json.dump(formatted_neighbors, f, indent=4)

print("Lista de vizinhos descobertos:")
print(json.dumps(formatted_neighbors, indent=4))

# Salva o grafo da rede em um arquivo JSON
graph_file_path = "network_graph.json"
with open(graph_file_path, "w") as f:
    json.dump(network_graph, f, indent=4)

print("Grafo da rede:")
print(json.dumps(network_graph, indent=4))

# Chamando o playbook Ansible após a execução da descoberta
ansible_playbook = "zabbixreadertest.yml"

try:
    print("Executando o playbook Ansible para adicionar hosts no Zabbix...")
    subprocess.run(["ansible-playbook", ansible_playbook], check=True)
    print("Playbook Ansible executado com sucesso.")
except subprocess.CalledProcessError as e:
    print(f"Erro ao executar o playbook Ansible: {e}")
