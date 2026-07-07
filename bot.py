import subprocess
import xml.etree.ElementTree as ET
import re
import time
import difflib
from deep_translator import GoogleTranslator

def capturar_estado_memoria():
    comando_xml = 'adb shell "uiautomator dump /sdcard/dump.xml > /dev/null && cat /sdcard/dump.xml"'
    return subprocess.run(comando_xml, shell=True, capture_output=True, text=True).stdout

def extrair_elementos(xml_raw):
    elementos = []
    if not xml_raw.strip(): return elementos
    try:
        root = ET.fromstring(xml_raw)
        for node in root.iter('node'):
            texto = node.attrib.get('text', '') or node.attrib.get('content-desc', '')
            bounds = node.attrib.get('bounds', '')
            if texto and bounds:
                coords = re.findall(r'\d+', bounds)
                if len(coords) == 4:
                    x1, y1, x2, y2 = map(int, coords)
                    centro_y = (y1 + y2) // 2
                    elementos.append({
                        "texto": texto,
                        "centro": ((x1 + x2) // 2, centro_y),
                        "eixo_y": centro_y 
                    })
    except ET.ParseError:
        pass
    return elementos

def resolver_traducao(elementos):
    textos = [el['texto'] for el in elementos]
    idx_instrucao = -1
    for i, t in enumerate(textos):
        if "Traduza" in t:
            idx_instrucao = i
            break
            
    if idx_instrucao != -1:
        frase_original = ""
        for i in range(idx_instrucao + 1, len(textos)):
            if textos[i].strip():
                frase_original = textos[i]
                break
                
        print(f"\n[ALVO] Frase original: '{frase_original}'")
        resposta_ideal = GoogleTranslator(source='en', target='pt').translate(frase_original)
        resposta_ideal = resposta_ideal.replace(".", "").replace(",", "").replace("!", "").replace("?", "").lower().strip()
        print(f"[IA] Tradução sugerida: '{resposta_ideal}'")
        
        palavras_alvo = resposta_ideal.split()
        
        # Filtra os botões de palavras disponíveis na metade inferior da tela
        palavras_ignoradas = ["verificar", "check", "continuar", "continue", "pular", "solução"]
        botoes_palavras = [el for el in elementos if el['eixo_y'] > 800 and el['texto'].lower() not in palavras_ignoradas]
        
        cliques_para_executar = []
        
        for palavra in palavras_alvo:
            # Cria um mapeamento de texto limpo para o objeto do botão
            mapeamento = {}
            for b in botoes_palavras:
                txt_b = b['texto'].replace(".", "").replace(",", "").replace("!", "").replace("?", "").lower().strip()
                if txt_b:
                    mapeamento[txt_b] = b
            
            possibilidades = list(mapeamento.keys())
            
            # 1. Tenta o Match Perfeito
            if palavra in possibilidades:
                botao = mapeamento[palavra]
                cliques_para_executar.append(botao['centro'])
                botoes_palavras.remove(botao)
            else:
                # 2. Se falhar, usa Inteligência Fuzzy (Fuzzy Match) para aproximar a palavra
                matches_proximos = difflib.get_close_matches(palavra, possibilidades, n=1, cutoff=0.5)
                if matches_proximos:
                    print(f"    [MATCH APROXIMADO] '{palavra}' associada a '{matches_proximos[0]}'")
                    botao = mapeamento[matches_proximos[0]]
                    cliques_para_executar.append(botao['centro'])
                    botoes_palavras.remove(botao)
                else:
                    print(f"    [AVISO] Palavra '{palavra}' não encontrada nos botões disponíveis.")
                    
        return cliques_para_executar
    return []

def processar_frame(elementos):
    textos_validos = [el['texto'].lower().strip() for el in elementos]
    
    # PRIORIDADE 1: Se o botão Continuar/Avançar estiver na tela, saia do exercício imediatamente
    gatilhos_continuar = ["continuar", "continue", "entendi", "ótimo", "correto", "solução"]
    for el in elementos:
        txt = el['texto'].lower().strip()
        if any(g == txt for g in gatilhos_continuar):
            return [el['centro']], "AVANCAR"
            
    # PRIORIDADE 2: Se a instrução de Tradução estiver na tela
    if any("traduza" in t for t in textos_validos):
        cliques_palavras = resolver_traducao(elementos)
        if cliques_palavras:
            return cliques_palavras, "PALAVRAS"
        else:
            # Se a instrução existe mas nenhuma palavra foi encontrada para clicar, 
            # significa que a frase já foi montada. Forçamos o clique em Verificar.
            for el in elementos:
                if el['texto'].lower().strip() in ["verificar", "check"]:
                    return [el['centro']], "VERIFICAR"
                    
    return [], "NADA"

def loop_principal():
    print("Iniciando MÓDULO CORRIGIDO Auto-Duo... Ctrl+C para parar.")
    
    while True:
        xml_raw = capturar_estado_memoria()
        elementos = extrair_elementos(xml_raw)
        
        if not elementos:
            time.sleep(1)
            continue
            
        cliques, tipo_acao = processar_frame(elementos)
        
        if cliques:
            if tipo_acao == "PALAVRAS":
                print(f"[AÇÃO] Selecionando {len(cliques)} palavras na ordem correta...")
                for (x, y) in cliques:
                    subprocess.run(["adb", "shell", "input", "tap", str(x), str(y)])
                    time.sleep(0.4)
                
                # Força uma pequena pausa e tenta clicar em Verificar logo em seguida
                time.sleep(0.5)
                xml_atualizado = capturar_estado_memoria()
                elementos_atualizados = extrair_elementos(xml_atualizado)
                for el in elementos_atualizados:
                    if el['texto'].lower().strip() in ["verificar", "check"]:
                        print("[AÇÃO] Forçando clique em VERIFICAR...")
                        subprocess.run(["adb", "shell", "input", "tap", str(el['centro'][0]), str(el['centro'][1])])
                        break
                        
            elif tipo_acao == "VERIFICAR":
                print("[AÇÃO] Tela estagnada detectada. Clicando em VERIFICAR...")
                subprocess.run(["adb", "shell", "input", "tap", str(cliques[0][0]), str(cliques[0][1])])
                
            elif tipo_acao == "AVANCAR":
                print("[AÇÃO] Tela de transição detectada. Clicando em CONTINUAR...")
                subprocess.run(["adb", "shell", "input", "tap", str(cliques[0][0]), str(cliques[0][1])])
                
        time.sleep(1.5)

if __name__ == "__main__":
    loop_principal()