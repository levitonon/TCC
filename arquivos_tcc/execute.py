# main_script.py
import subprocess

def executar_codigo1():
    print("Executando o script cdp_graph.py (Código 1)")
    subprocess.run(["python3", "cdp_graph.py"])  # Executa o Código 1

def executar_codigo2():
    print("Executando o script create_map4.py (Código 2)")
    subprocess.run(["python3", "create_map4.py"])  # Executa o Código 2

if __name__ == "__main__":
    executar_codigo1()  # Primeiro, executa o Código 1
    executar_codigo2()  # Depois que o Código 1 terminar, executa o Código 2
