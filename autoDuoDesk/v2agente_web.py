import time
import json
import re
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

# 1. Configurando o Gemini
client = genai.Client(api_key="SUA_CHAVE_API_AQUI")

# 2. A Instrução Mestre (Agora com habilidade de digitação)
INSTRUCAO_MESTRE = """
Você é um agente autônomo jogando Duolingo no computador.
Analise a imagem. Identifique o tipo de exercício, resolva a questão e decida a ação.

Retorne APENAS um JSON válido no formato abaixo, sem formatação Markdown ou blocos de código:
{
  "raciocinio": "Explique brevemente o que o exercício pede e a solução.",
  "texto_para_digitar": "Se for um exercício de digitar (campo de texto em branco), escreva a resposta final aqui. Se não for, deixe vazio.",
  "alvos": ["texto do botão 1", "Verificar"]
}

Regras vitais:
1. Exercícios de DIGITAÇÃO: Coloque a resposta correta em "texto_para_digitar" e retorne APENAS ["VERIFICAR"] na lista de "alvos".
2. Exercícios de BOTÕES: Deixe "texto_para_digitar" vazio ("") e liste as palavras na ordem correta em "alvos". Escolha apenas palavras visíveis.
3. SEMPRE coloque o botão de confirmar ("VERIFICAR" ou "CONTINUAR") como o ÚLTIMO alvo da lista.
4. Para pular áudio, retorne ["NÃO POSSO OUVIR AGORA"].
5. Copie os textos exatamente como aparecem nos botões.
"""

def observar_e_agir(pagina):
    print("\n[OLHO] Tirando print do navegador...")
    screenshot_bytes = pagina.screenshot(type='jpeg', quality=80)
    imagem = types.Part.from_bytes(data=screenshot_bytes, mime_type='image/jpeg')

    print("[CÉREBRO] Enviando visão para o Gemini processar...")
    try:
        resposta = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=[INSTRUCAO_MESTRE, imagem]
        )
        
        texto_limpo = resposta.text.strip().replace('```json', '').replace('```', '')
        dados = json.loads(texto_limpo)
        
        print(f"[PENSAMENTO] {dados.get('raciocinio', 'Sem raciocínio explícito.')}")
        
        # --- A MÃO: DIGITAÇÃO ---
        texto_digitar = dados.get("texto_para_digitar", "").strip()
        if texto_digitar:
            print(f"[AÇÃO - TECLADO] O Agente vai digitar: '{texto_digitar}'")
            # Busca a caixa de texto padrão de acessibilidade do HTML e preenche
            caixa_texto = pagina.get_by_role("textbox").first
            if caixa_texto.is_visible():
                caixa_texto.fill(texto_digitar)
                time.sleep(0.5)
            else:
                print("[-] Campo de texto não encontrado na tela.")

        # --- A MÃO: CLIQUES ---
        alvos = dados.get("alvos", [])
        if alvos:
            print(f"[AÇÃO - MOUSE] O Agente decidiu clicar em: {alvos}")
            
        for texto in alvos:
            texto_limpo_alvo = texto.strip()
            
            # O Hack do Enter para os botões principais de avanço
            if texto_limpo_alvo.upper() in ["VERIFICAR", "CONTINUAR"]:
                print(f"[*] Apertando tecla 'Enter' para avançar ({texto_limpo_alvo})...")
                pagina.keyboard.press("Enter")
                time.sleep(0.8)
                continue 
            
            # Busca flexível para os botões de palavras
            padrao_texto = re.compile(texto_limpo_alvo, re.IGNORECASE)
            botoes_visiveis = pagina.get_by_text(padrao_texto).filter(visible=True)
            
            if botoes_visiveis.count() > 0:
                botoes_visiveis.first.click()
                time.sleep(0.4) 
            else:
                print(f"[-] Botão '{texto}' não encontrado na interface visível.")
                
    except json.JSONDecodeError:
        print("[FALHA NA IA] A IA não retornou um JSON válido.")
    except Exception as e:
        print(f"[FALHA DO SISTEMA] Ocorreu um erro: {e}")

def iniciar_agente():
    with sync_playwright() as p:
        print("[SISTEMA] Abrindo o Chrome...")
        navegador = p.chromium.launch_persistent_context(
            user_data_dir="./sessao_duolingo",
            headless=False, 
            viewport={"width": 1280, "height": 720}
        )
        
        pagina = navegador.pages[0]
        pagina.goto("https://www.duolingo.com/")
        
        print("\n=== SETUP INICIAL ===")
        print("Deixe na primeira tela de exercício. O robô assume em 15 segundos...\n")
        time.sleep(15) 
        
        print("=== INICIANDO AUTONOMIA ===")
        while True:
            observar_e_agir(pagina)
            time.sleep(3) 

if __name__ == "__main__":
    iniciar_agente()