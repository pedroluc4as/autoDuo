import subprocess
import time
import os

# Cria o diretório para armazenar seu dataset
os.makedirs("dataset", exist_ok=True)

def capturar_estado(id_captura):
    caminho_imagem = f"dataset/{id_captura}.png"
    caminho_xml_pc = f"dataset/{id_captura}.xml"
    caminho_xml_celular = "/sdcard/window_dump.xml"

    print(f"Capturando tela {id_captura}...")

    # 1. Tira o print e joga direto no PC em binário (mais rápido)
    with open(caminho_imagem, "wb") as f:
        subprocess.run(["adb", "exec-out", "screencap", "-p"], stdout=f)

    # 2. Pede pro Android gerar o mapeamento da tela em XML
    subprocess.run(["adb", "shell", "uiautomator", "dump", caminho_xml_celular], capture_output=True)

    # 3. Puxa o XML para o PC
    subprocess.run(["adb", "pull", caminho_xml_celular, caminho_xml_pc], capture_output=True)

    print(f"Estado salvo com sucesso!")

if __name__ == "__main__":
    # Gera um ID único baseado no timestamp atual
    id_atual = int(time.time())
    capturar_estado(id_atual)