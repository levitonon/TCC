import json
from netmiko import ConnectHandler

# Defina as informações de conexão para o roteador ou switch
device = {
    'device_type': 'cisco_ios',
    'host': '192.168.0.69',  # IP do roteador/switch
    'username': 'Admin',      # Nome de usuário
    'password': 'Eve',        # Senha
}

# Lista para armazenar vizinhos já capturados
captured_neighbors = set()

def get_cdp_neighbors(device):
    # Conectar ao dispositivo
    try:
        connection = ConnectHandler(**device)
        # Executar o comando 'show cdp neighbors detail'
        output = connection.send_command('show cdp neighbors detail')
        connection.disconnect()
        
        return output
    except Exception as e:
        print(f"Error connecting to device {device['host']}: {e}")
        return None

def parse_cdp_output(output):
    neighbors = []
    # Dividir a saída em linhas
    lines = output.splitlines()
    
    # Variáveis para armazenar o nome do dispositivo e o IP
    hostname = ""
    ip_address = ""
    
    for line in lines:
        line = line.strip()
        # Verificar se a linha contém informações do dispositivo
        if line.startswith('Device ID:'):
            if hostname and ip_address:  # Se já tivermos um vizinho, salve antes de reatribuir
                neighbors.append({"hostname": hostname, "ip": ip_address})
            hostname = line.split("Device ID: ")[1]  # Extrair o nome do dispositivo
        elif line.startswith('IP address:'):
            ip_address = line.split("IP address: ")[1]  # Extrair o IP
            
    # Adicionar o último vizinho encontrado
    if hostname and ip_address:
        neighbors.append({"hostname": hostname, "ip": ip_address})
        
    return neighbors

def save_to_json(data, filename='neighbors.json'):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Neighbors data saved to {filename}")

def discover_neighbors(device):
    global captured_neighbors
    
    # Obter a saída do CDP
    output = get_cdp_neighbors(device)
    
    if output:
        # Analisar a saída e extrair vizinhos
        neighbors = parse_cdp_output(output)
        
        for neighbor in neighbors:
            # Criar uma chave única para o vizinho
            neighbor_key = (neighbor["hostname"], neighbor["ip"])
            
            if neighbor_key not in captured_neighbors:
                captured_neighbors.add(neighbor_key)  # Marcar como capturado
                
                # Preparar as informações do vizinho para nova descoberta
                neighbor_device = {
                    'device_type': 'cisco_ios',
                    'host': neighbor['ip'],  # Usar o IP do vizinho
                    'username': device['username'],
                    'password': device['password'],
                }
                
                # Recursão para descobrir vizinhos do vizinho
                discover_neighbors(neighbor_device)
    
def main():
    # Iniciar a descoberta
    discover_neighbors(device)
    
    # Salvar os vizinhos capturados em um arquivo JSON
    save_to_json(list(captured_neighbors))

if __name__ == "__main__":
    main()
