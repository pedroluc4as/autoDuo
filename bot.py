import xml.etree.ElementTree as ET
import re
from deep_translator import GoogleTranslator
import subprocess
import time

def analisar_tela(caminho_xml):
    tree = ET.parse(caminho_xml)
    root = tree.getroot()
    elementos_uteis = []

    for node in root.iter('node'):
        texto = node.attrib.get('text', '')
        desc = node.attrib.get('content-desc', '')
        bounds = node.attrib.get('bounds', '')
        clickable = node.attrib.get('clickable', 'false')
        conteudo = texto if texto else desc
        
        if conteudo:
            coords = re.findall(r'\d+', bounds)
            if len(coords) == 4:
                x1, y1, x2, y2 = map(int, coords)
                centro_x = (x1 + x2) // 2
                centro_y = (y1 + y2) // 2
                elementos_uteis.append({
                    "texto": conteudo,
                    "centro": (centro_x, centro_y),
                    "clicavel": clickable == 'true'
                })
    return elementos_uteis

def resolver_exercicio(elementos_da_tela):
    textos = [el['texto'] for el in elementos_da_tela]
    
    # DEBUG: Raio-X da tela para você entender a ordem dos elementos
    print("\n--- RAIO-X DOS TEXTOS DA TELA ---")
    for i, t in enumerate(textos):
        print(f"[{i}] {t}")
    print("---------------------------------\n")
    
    # Procura onde está a instrução
    idx_instrucao = -1
    for i, t in enumerate(textos):
        if "Traduza" in t:
            idx_instrucao = i
            break
            
    if idx_instrucao != -1:
        print("--> Detectado: Exercício de Tradução.")
        
        # A frase real geralmente é o próximo elemento da lista. 
        # Se o próximo for vazio (ex: ícone sem texto), pula pro seguinte.
        frase_original = ""
        for i in range(idx_instrucao + 1, len(textos)):
            if textos[i].strip(): # Se o texto não for vazio
                frase_original = textos[i]
                break
                
        print(f"--> Frase original extraída: '{frase_original}'")
        
        # Traduz a frase
        resposta_ideal = GoogleTranslator(source='en', target='pt').translate(frase_original)
        resposta_ideal = resposta_ideal.replace(".", "").replace(",", "").replace("!", "").replace("?", "").lower()
        print(f"--> Resposta calculada pela API: '{resposta_ideal}'")
        
        palavras_alvo = resposta_ideal.split()
        botoes_clicaveis = [el for el in elementos_da_tela if el['clicavel']]
        cliques_para_executar = []
        
        # Faz o match das palavras com os botões
        for palavra in palavras_alvo:
            for botao in botoes_clicaveis:
                # Remove pontuações do botão também para a comparação ser exata
                texto_botao = botao['texto'].replace(".", "").replace(",", "").lower()
                
                if texto_botao == palavra:
                    print(f"    [MATCH] Encontrei o botão para: '{palavra}' (X:{botao['centro'][0]}, Y:{botao['centro'][1]})")
                    cliques_para_executar.append(botao['centro'])
                    botoes_clicaveis.remove(botao)
                    break
                    
        return cliques_para_executar
    else:
        print("\n--> Não é um exercício de tradução ou a tela mudou.")
        return []
    
def executar_cliques(lista_coordenadas, elementos_da_tela):
    print("\n--- INICIANDO AUTOMAÇÃO ---")
    
    # 1. Clica em cada palavra na ordem correta
    for (x, y) in lista_coordenadas:
        print(f"Injetando toque em X:{x} Y:{y}")
        subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)])
        time.sleep(0.6) # Pausa de 600ms para o app registrar a animação
        
    time.sleep(1) # Pausa extra antes de confirmar
    
    # 2. Procura e clica no botão "Verificar"
    for el in elementos_da_tela:
        if el['texto'].lower() == "verificar" or el['texto'].lower() == "check":
            x, y = el['centro']
            print(f"Clicando em VERIFICAR (X:{x} Y:{y})")
            subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)])
            time.sleep(2) # Espera a tela de "Correto!" aparecer
            
            # Clica em "Continuar" para ir pra próxima fase
            subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)])
            break

if __name__ == "__main__":
    arquivo_xml = "dataset/1783353211.xml" 
    
    try:
        print("1. Analisando o XML da tela...")
        elementos = analisar_tela(arquivo_xml)
        
        print("2. Calculando a resposta e buscando os botões...")
        coordenadas = resolver_exercicio(elementos)
        
        if coordenadas:
            print(f"\n3. Sucesso! Preparando injeção ADB...")
            # Mantenha o celular ligado, com a tela desbloqueada exatamente no exercício que gerou o XML
            executar_cliques(coordenadas, elementos)
            print("\nAção concluída!")
        else:
            print("\n3. Nenhum botão compatível encontrado.")
            
    except FileNotFoundError:
        print(f"Erro: O arquivo '{arquivo_xml}' não foi encontrado.")
