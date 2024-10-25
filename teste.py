import re

# Simulação da saída do comando
output = """-------------------------
Device ID: SW1
Entry address(es):
  IP address: 192.168.10.10
Platform: Cisco ,  Capabilities: Router Switch IGMP
Interface: GigabitEthernet0/1,  Port ID (outgoing port): GigabitEthernet0/1
Holdtime : 131 sec
...
"""

# Imprimir a saída para verificação
print("Saída do comando:")
print(output)

# Regex para capturar o nome do dispositivo e o IP
pattern = r"Device ID:\s*(\S+).*?IP address:\s*(\d+\.\d+\.\d+\.\d+)"

# Encontrar todas as correspondências
matches = re.findall(pattern, output, re.DOTALL)  # Usar re.DOTALL para capturar quebras de linha

# Verificar se as correspondências foram encontradas
if matches:
    print("Matches encontrados:", matches)
else:
    print("Nenhuma correspondência encontrada.")
