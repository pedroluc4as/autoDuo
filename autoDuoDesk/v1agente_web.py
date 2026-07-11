import time
import json
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

# 1. O Cérebro: Configurando o Gemini com a NOVA SDK (google-genai)
# Substitua pela sua chave do Google AI Studio
client = genai.Client(api_key="SUA_CHAVE_API_AQUI")

# 2. A Instrução Mestre (Prompt)
INSTRUCAO_MESTRE = """
Você é um agente autônomo jogando Duolingo no computador.
Analise o print do navegador. Identifique o tipo de exercício, resolva a questão e decida onde clicar.
Retorne APENAS um JSON válido no seguinte formato, sem blocos de código (```json):
{
  "alvos": ["texto do botão 1", "texto do botão 2", "Verificar"]
}
Regras:
1. Para exercícios de tradução, liste as palavras na ordem correta, e adicione "Verificar" no final.
2. Para pular áudio, retorne ["Não posso ouvir agora"].
3. Se for uma tela de acerto/erro, retorne ["Continuar"].
4. Retorne as palavras EXATAMENTE como estão escritas nos botões da imagem.
"""

def observar_e_agir(pagina):
    print("\n[OLHO] Tirando print do navegador...")
    
    # O Playwright tira o print e joga direto na memória
    screenshot_bytes = pagina.screenshot(type='jpeg', quality=30)
    
    # Formata a imagem para a nova SDK do Gemini
    imagem = types.Part.from_bytes(data=screenshot_bytes, mime_type='image/jpeg')

    print("[CÉREBRO] Enviando visão para o Gemini processar...")
    try:
        resposta = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[INSTRUCAO_MESTRE, imagem]
        )
        
        texto_limpo = resposta.text.strip().replace('```json', '').replace('```', '')
        dados = json.loads(texto_limpo)
        
        print(f"[AÇÃO] O Agente decidiu clicar em: {dados['alvos']}")
        
        # 3. A Mão: Executando os cliques no navegador
        for texto in dados["alvos"]:
            botao = pagina.get_by_text(texto, exact=True).first
            
            if botao.is_visible():
                botao.click()
                time.sleep(0.4) 
            else:
                print(f"[-] Botão '{texto}' não está visível. Pulando.")
                
    except Exception as e:
        print(f"[FALHA NA IA] Ocorreu um erro no processamento: {e}")

def iniciar_agente():
    with sync_playwright() as p:
        print("[SISTEMA] Abrindo o Chrome...")
        navegador = p.chromium.launch_persistent_context(
            user_data_dir="./sessao_duolingo",
            headless=False, 
            viewport={"width": 1280, "height": 720}
        )
        
        pagina = navegador.pages[0]
        # Aqui o link está corrigido, sem formatação de Markdown
        pagina.goto("https://www.duolingo.com/")
        
        print("\n=== SETUP INICIAL ===")
        print("1. Se não estiver logado, faça o login agora.")
        print("2. Entre em uma lição e deixe na primeira tela de exercício.")
        print("O robô vai assumir o controle em 5 segundos...\n")
        time.sleep(5) 
        
        print("=== INICIANDO AUTONOMIA ===")
        while True:
            observar_e_agir(pagina)
            time.sleep(3) 

if __name__ == "__main__":
    iniciar_agente()