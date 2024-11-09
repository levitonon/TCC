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

# Lista para armazenar vizinhos descobertos
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

    # Extrai o nome, remove o domínio e separa os objetos do JSON
    for line in output.splitlines():
        if "Device ID:" in line:
            # Extrai o hostname do vizinho
            hostname = line.split("Device ID: ")[1].strip()
            # Remove o sufixo ".cisco.com" do hostname, se presente
            hostname = hostname.replace(".cisco.com", "")
        if "IP address:" in line:
            # Extrai o endereço IP do vizinho
            ip = line.split("IP address: ")[1].strip()
            # Adiciona o vizinho à lista
            neighbors.append({"hostname": hostname, "ip": ip})
    
    connection.disconnect() 
    return neighbors 

# Realiza o acesso recursivo
def recursive_discovery(device):

    global discovered_neighbors, network_graph
    # Captura os vizinhos do dispositivo atual
    new_neighbors = capture_neighbors(device)
    
    current_device = device['host']

    # Adiciona o dispositivo atual ao grafo, caso não esteja
    if current_device not in network_graph:
        network_graph[current_device] = []

    for neighbor in new_neighbors:
        # Impede ciclo se já estiver adicionado
        if neighbor not in discovered_neighbors:
            print(f"Descoberto novo vizinho: {neighbor['hostname']} - {neighbor['ip']}")  
            discovered_neighbors.append(neighbor)  

            # Adiciona o vizinho ao grafo do dispositivo atual
            network_graph[current_device].append({"hostname": neighbor["hostname"], "ip": neighbor["ip"]})

            # Credenciais de conexão para o vizinho
            neighbor_device = {
                "device_type": "cisco_ios",
                "host": neighbor['ip'],
                "username": "Admin",
                "password": "Eve",
            }
            print(f"Acessando novos vizinhos de {neighbor['hostname']}...")  
            recursive_discovery(neighbor_device)  # Chamada recursiva para o vizinho
        else:
            print(f"{neighbor['hostname']} já foi descoberto.") 

    # Verificação de dispositivo sem vizinhos
    if not new_neighbors:
        print(f"{device['host']} não tem novos vizinhos.")  

# Executa a descoberta começando pelo roteador inicial definido em 'devices'
recursive_discovery(devices["my_router"])

# Formata a lista de vizinhos para salvar em JSON
formatted_neighbors = [{"hostname": neighbor["hostname"], "ip": neighbor["ip"]} for neighbor in discovered_neighbors]

# Caminho do JSON
json_file_path = "discovered_neighbors.json"
with open(json_file_path, "w") as f:
    json.dump(formatted_neighbors, f, indent=4)  

print("Lista de vizinhos descobertos:")
print(json.dumps(formatted_neighbors, indent=4))  # Imprime a lista

# Caminho do JSON para salvar o grafo da rede (O anterior é somente lista, esse é o grafo)
graph_file_path = "network_graph.json"
with open(graph_file_path, "w") as f:
    json.dump(network_graph, f, indent=4)  

print("Grafo da rede:")
print(json.dumps(network_graph, indent=4))  # Imprime o grafo da rede

# Chama o playbook que irá adicionar os dispositivos no zabbix
ansible_playbook = "zabbixreadertest.yml"

# Prints para conexão com o playbook
try:
    print("Executando o playbook Ansible para adicionar hosts no Zabbix...")  # Log da execução    
    subprocess.run(["ansible-playbook", ansible_playbook], check=True)
    print("Playbook Ansible executado com sucesso.")  
except subprocess.CalledProcessError as e:    
    print(f"Erro ao executar o playbook Ansible: {e}")
