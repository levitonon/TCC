import time
import subprocess

def executar_codigo1():
    print("Executando o script cdp_graph.py")
    subprocess.run(["python3", "cdp_graph.py"])
    
def executar_codigo2():
    print("Executando o script create_map4.py")
    subprocess.run(["python3", "map_per_locale.py"]) 

if __name__ == "__main__":
    #Timer do processo
    start_time = time.time()

    # Executa na ordem desejada
    executar_codigo1()
    executar_codigo2()

    end_time = time.time()

    total_time = end_time - start_time

    # Exibe o tempo total formatado (2 casas decimais, por exemplo)
    print(f"Tempo total de execução: {total_time:.2f} segundos")
