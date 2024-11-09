import subprocess

def executar_codigo1():
    print("Executando o script cdp_graph.py (Código 1)")
    subprocess.run(["python3", "cdp_graph.py"])  # Executa o código que irá varrer a rede

def executar_codigo2():
    print("Executando o script create_map4.py (Código 2)")
    subprocess.run(["python3", "create_map4.py"])  # Executa o código que irá criar o mapa

if __name__ == "__main__":
#Ordem de execução
    executar_codigo1()  
    executar_codigo2()  
