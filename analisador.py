import xml.etree.ElementTree as ET
import re

def analisar_tela(caminho_xml):
    tree = ET.parse(caminho_xml)
    root = tree.getroot()

    elementos_uteis = []

    # Itera sobre todos os nós da árvore XML
    for node in root.iter('node'):
        texto = node.attrib.get('text', '')
        desc = node.attrib.get('content-desc', '')
        bounds = node.attrib.get('bounds', '')
        clickable = node.attrib.get('clickable', 'false')

        # Prioriza o texto, mas pega a descrição se o texto for vazio (comum em ícones)
        conteudo = texto if texto else desc
        
        # Só nos importamos com nós que tenham conteúdo visual ou textual
        if conteudo:
            # O bounds vem no formato "[x1,y1][x2,y2]". Vamos extrair os 4 números.
            coords = re.findall(r'\d+', bounds)
            if len(coords) == 4:
                x1, y1, x2, y2 = map(int, coords)
                
                # Calcula a coordenada X e Y exata do meio do elemento
                centro_x = (x1 + x2) // 2
                centro_y = (y1 + y2) // 2
                
                elementos_uteis.append({
                    "texto": conteudo,
                    "centro": (centro_x, centro_y),
                    "clicavel": clickable == 'true'
                })

    return elementos_uteis

if __name__ == "__main__":
    # Substitua pelo nome do arquivo XML que seu extrator gerou
    arquivo_teste = "dataset/1783353211.xml" 
    
    try:
        elementos = analisar_tela(arquivo_teste)
        for el in elementos:
            print(f"Texto: '{el['texto']}' | Coordenada: {el['centro']} | Clicável: {el['clicavel']}")
    except FileNotFoundError:
        print("Arquivo XML não encontrado. Verifique o caminho.")