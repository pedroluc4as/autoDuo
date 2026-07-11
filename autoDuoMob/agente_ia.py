import uiautomator2 as u2
import google.generativeai as genai
from PIL import Image
import time
import json

# Configure sua chave da API do Gemini aqui
genai.configure(api_key="SUA_CHAVE_API_AQUI")

# Escolhendo o modelo otimizado para tarefas rápidas e visão
modelo = genai.GenerativeModel('gemini-1.5-pro-latest')

# Conecta ao celular
d = u2.connect()

# O "Prompt de Sistema" é a alma do Agente. Ele define como a IA deve se comportar.
INSTRUCAO_MESTRE = """
Você é um agente autônomo jogando o aplicativo Duolingo.
Analise a imagem da tela que enviei. Determine qual é o tipo de exercício, resolva-o e me devolva APENAS um objeto JSON válido dizendo o que devo fazer.

Regras do JSON:
Se precisar clicar em uma sequência de blocos de palavras, retorne: {"action": "click", "words": ["palavra1", "palavra2"]}
Se precisar digitar texto em uma lacuna, retorne: {"action": "type", "text": "palavra_a_digitar"}
Se for um erro/acerto ou precisar avançar/pular tela, retorne: {"action": "click_button", "text": "CONTINUAR"} (ou o botão correspondente).
Se for ligar pares, retorne na ordem exata: {"action": "click", "words": ["inglês1", "português1", "inglês2", "português2"]}

NÃO explique seu raciocínio. NÃO use formatação markdown (```json). Retorne apenas o JSON puro.
"""

def observar_e_agir():
    print("\n[OLHO] Capturando a tela do celular...")
    # 1. Observação: O agente "olha" para a tela tirando um screenshot
    caminho_foto = "tela_atual.jpg"
    d.screenshot(caminho_foto)
    img = Image.open(caminho_foto)

    print("[CÉREBRO] Enviando visão para o Gemini processar...")
    try:
        # 2. Raciocínio: A IA analisa o jogo
        resposta = modelo.generate_content([INSTRUCAO_MESTRE, img])
        json_texto = resposta.text.strip()
        
        # Limpa possível formatação extra do LLM
        if json_texto.startswith("```json"):
            json_texto = json_texto[7:-3]
            
        acao_ia = json.loads(json_texto)
        print(f"[AÇÃO CALCULADA] {acao_ia}")

        # 3. Ação: O corpo (uiautomator2) executa o que o cérebro (Gemini) mandou
        comando = acao_ia.get("action")
        
        if comando == "click":
            for palavra in acao_ia.get("words", []):
                if d(text=palavra).exists:
                    d(text=palavra).click()
            time.sleep(0.5)
            d(text="VERIFICAR").click_exists() or d(text="CHECK").click_exists()
            
        elif comando == "type":
            d(className="android.widget.EditText").set_text(acao_ia.get("text", ""))
            time.sleep(0.5)
            d.press("back") # Fecha o teclado
            d(text="VERIFICAR").click_exists() or d(text="CHECK").click_exists()
            
        elif comando == "click_button":
            botao = acao_ia.get("text", "CONTINUAR")
            d(text=botao).click_exists() or d(textIgnoreCase=botao).click_exists()

    except Exception as e:
        print(f"[FALHA NA IA] O Agente se confundiu: {e}")
        time.sleep(1)

def loop_autonomo():
    print("Iniciando o Agente Multimodal de IA... (Aperte Ctrl+C para parar)")
    while True:
        observar_e_agir()
        # Espera as animações do Duolingo acabarem antes de olhar de novo
        time.sleep(3) 

if __name__ == "__main__":
    loop_autonomo()