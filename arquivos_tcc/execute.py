import subprocess
import time

def executar_codigo1():
    print("Executando o script cdp_graph.py (Código 1)")
    subprocess.run(["python3", "cdp_graph.py"])  # Executa o código que irá varrer a rede

def executar_codigo2():
    print("Executando o script create_map4.py (Código 2)")
    subprocess.run(["python3", "map_per_locale.py"])  # Executa o código que irá criar o mapa

if __name__ == "__main__":
    inicio_total = time.time()  # Início do timer total
    
    # Ordem de execução
    executar_codigo1()  
    executar_codigo2()
    
    fim_total = time.time()  # Fim do timer total
    print(f"Tempo total de execução: {fim_total - inicio_total:.2f} segundos")
