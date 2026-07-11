import time
import json
import os
import re
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

client = genai.Client(api_key="SUA_CHAVE_API_AQUI")
ARQUIVO_MEMORIA = "memoria.json"

INSTRUCAO_MESTRE = """
Você é um agente autônomo jogando Duolingo.
Retorne APENAS um JSON:
{
  "raciocinio": "breve explicação",
  "texto_para_digitar": "texto da resposta se for de escrever, senão vazio",
  "alvos": ["palavra1", "palavra2", "VERIFICAR"]
}
"""

def carregar_memoria():
    if os.path.exists(ARQUIVO_MEMORIA):
        with open(ARQUIVO_MEMORIA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salvar_memoria(memoria):
    with open(ARQUIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(memoria, f, indent=4, ensure_ascii=False)

def obter_chave_da_pergunta_via_rpa(pagina):
    """
    Tenta ler a pergunta direto do HTML (MUITO RÁPIDO).
    Procura pelos atributos padrão do Duolingo.
    """
    try:
        # Tenta pegar a frase a ser traduzida
        locator = pagina.locator('[data-test="hint-sentence"]')
        if locator.count() > 0:
            return locator.first.inner_text().strip()
        
        # Se não achar, tenta pegar o cabeçalho do desafio
        locator_cabecalho = pagina.locator('[data-test="challenge-header"]')
        if locator_cabecalho.count() > 0:
            return locator_cabecalho.first.inner_text().strip()
    except Exception:
        pass
    return None

def executar_rpa(pagina, dados):
    """A Mão: Executa as ações na velocidade máxima do navegador"""
    texto_digitar = dados.get("texto_para_digitar", "").strip()
    if texto_digitar:
        caixa_texto = pagina.get_by_role("textbox").first
        if caixa_texto.is_visible():
            caixa_texto.fill(texto_digitar)
            time.sleep(0.1)

    alvos = dados.get("alvos", [])
    for texto in alvos:
        texto_limpo = texto.strip()
        
        if texto_limpo.upper() in ["VERIFICAR", "CONTINUAR"]:
            pagina.keyboard.press("Enter")
            time.sleep(0.5)
            continue 
        
        padrao = re.compile(f"^{re.escape(texto_limpo)}$", re.IGNORECASE)
        botoes = pagina.get_by_text(padrao).filter(visible=True)
        
        if botoes.count() > 0:
            botoes.first.click()
            time.sleep(0.1) # Pausa mínima só para o site registrar
        else:
            # Tenta busca parcial caso falhe
            botoes_parciais = pagina.get_by_text(texto_limpo).filter(visible=True)
            if botoes_parciais.count() > 0:
                botoes_parciais.first.click()
                time.sleep(0.1)

def observar_e_agir_com_ia(pagina):
    """Aciona a IA apenas se o RPA não souber a resposta"""
    screenshot_bytes = pagina.screenshot(type='jpeg', quality=30)
    imagem = types.Part.from_bytes(data=screenshot_bytes, mime_type='image/jpeg')

    try:
        resposta = client.models.generate_content(
            model='gemini-3.5-flash', 
            contents=[INSTRUCAO_MESTRE, imagem]
        )
        
        texto_limpo = resposta.text.strip().replace('```json', '').replace('```', '')
        dados = json.loads(texto_limpo)
        return dados
    except Exception as e:
        print(f"[FALHA NA IA] Erro: {e}")
        return None

def iniciar_agente():
    memoria = carregar_memoria()
    print(f"[SISTEMA] Banco de dados carregado com {len(memoria)} exercícios aprendidos.")

    with sync_playwright() as p:
        navegador = p.chromium.launch_persistent_context(
            user_data_dir="./sessao_duolingo",
            headless=False,
            viewport={"width": 1280, "height": 720}
        )
        pagina = navegador.pages[0]
        pagina.goto("https://www.duolingo.com/")
        
        time.sleep(15) 
        
        while True:
            # 1. Tenta ler o exercício em tempo real via HTML
            chave_pergunta = obter_chave_da_pergunta_via_rpa(pagina)
            
            # 2. Verifica se a resposta já está salva na memória
            if chave_pergunta and chave_pergunta in memoria:
                print(f"\n[RPA FAST] Já conheço essa: '{chave_pergunta}'. Executando do banco...")
                dados = memoria[chave_pergunta]
                executar_rpa(pagina, dados)
            else:
                # 3. Se for inédita, pede ajuda pra IA
                print(f"\n[IA LENTA] Inédito. Analisando tela...")
                dados = observar_e_agir_com_ia(pagina)
                
                if dados:
                    print(f"[APRENDIZADO] IA resolveu. Ação: {dados.get('alvos')}")
                    # Salva a nova descoberta no banco (se conseguiu extrair uma chave válida da tela)
                    if chave_pergunta:
                        memoria[chave_pergunta] = dados
                        salvar_memoria(memoria)
                    
                    executar_rpa(pagina, dados)
            
            time.sleep(2) 

if __name__ == "__main__":
    iniciar_agente()