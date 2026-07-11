import uiautomator2 as u2
import time
import json
import os
import difflib
import re
import g4f
from deep_translator import GoogleTranslator

ARQUIVO_GABARITO = 'gabarito.json'
ARQUIVO_MEMORIA = 'memoria_duolingo.json'

# Cache para o bot lembrar a frase caso tome uma tela de erro
frase_atual_cache = ""

def carregar_dicionario(caminho):
    if os.path.exists(caminho):
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

try:
    d = u2.connect()
    d.implicitly_wait(0.5)
    print("MÓDULO AUTÔNOMO TOTAL V2 - Dispositivo:", d.info.get('productName'))
except Exception as e:
    print(f"Erro ao conectar no celular. Erro: {e}")
    exit()

def extrair_frase_alvo(textos):
    ignorar = [
        "traduza esta frase", "traduza esta frase:", 
        "corrija o erro de antes", "palavra nova", 
        "verificar", "check", "continuar", "continue", 
        "pular", "não posso ouvir agora", "não posso falar agora",
        "toque no que escutar:", "escolha a tradução correta", 
        "complete a conversa", "complete a conversa:",
        "leia e responda:", "leia e responda",
        "complete o espaço vazio:", "complete o espaço vazio",
        "repita o que", "disse:"
    ]
    for t in textos:
        txt_limpo = t.lower().strip()
        # Garante que seja uma frase inteira (tem espaços) e seja grande o suficiente
        if txt_limpo and not any(txt_limpo.startswith(ig) for ig in ignorar) and len(t) > 5 and " " in t and not t.isupper():
            return t
    return ""

def resolver_pares(textos):
    ignorar = ["combine os pares", "combine os pares:", "verificar", "check"]
    opcoes = [t for t in textos if t.lower().strip() not in ignorar and len(t) > 0]
    
    print(f"\n[ALVO Pares] Resolvendo: {opcoes}")
    prompt = f"Match the exact words from this list into translation pairs: {', '.join(opcoes)}. Output strictly like this: word1=word2, word3=word4. No other text."
    
    try:
        resposta = g4f.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]).strip()
        print(f"[IA] Pares: {resposta}")
        pares = [p.strip() for p in resposta.split(',')]
        
        for par in pares:
            if "=" in par:
                w1, w2 = par.split("=")
                w1, w2 = w1.strip(), w2.strip()
                d(textMatch=f"(?i)^{re.escape(w1)}$").click_exists()
                d(textMatch=f"(?i)^{re.escape(w2)}$").click_exists()
                
        time.sleep(0.5)
        d(text="VERIFICAR").click_exists() or d(text="CHECK").click_exists()
    except Exception as e:
        print(f"[ERRO IA] Falha nos pares: {e}")

def resolver_digitacao(textos):
    print(f"\n[ALVO Digitação] Contexto lido: {textos}")
    prompt = f"Read these UI texts from a language app: {textos}. Provide ONLY the EXACT single word or short phrase that is missing in the blank space. No quotes, no explanations."
    
    try:
        resposta = g4f.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]).strip()
        resposta = resposta.replace('"', '').replace('.', '')
        print(f"[IA] Palavra digitada: '{resposta}'")
        
        d(className="android.widget.EditText").set_text(resposta)
        time.sleep(0.5)
        d.press("back") # Fecha teclado
        time.sleep(0.5)
        d(text="VERIFICAR").click_exists() or d(text="CHECK").click_exists()
    except Exception as e:
        print(f"[ERRO IA] Digitação: {e}")

def resolver_multipla_escolha(textos):
    print(f"\n[ALVO Múltipla Escolha] Contexto: {textos}")
    prompt = f"You are solving a language app exercise. Based on this text context: {textos}, which is the correct missing word, logical response, or answer to the question? Return ONLY the EXACT text of the correct option from the context. No quotes, no explanations."
    try:
        resposta = g4f.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]).strip()
        print(f"[IA Escolha] '{resposta}'")
        
        match_regex = f"(?i)^{re.escape(resposta)}$"
        if d(textMatch=match_regex).exists:
            d(textMatch=match_regex).click()
        else:
            # Puxa apenas as opções de botões curtos para match aproximado
            opcoes = [t for t in textos if len(t) < 30]
            matches = difflib.get_close_matches(resposta, opcoes, n=1, cutoff=0.4)
            if matches:
                d(textMatch=f"(?i)^{re.escape(matches[0])}$").click()
                
        time.sleep(0.5)
        d(text="VERIFICAR").click_exists() or d(text="CHECK").click_exists()
    except Exception as e:
        print(f"[ERRO IA] Escolha: {e}")

def resolver_tela():
    global frase_atual_cache
    
    dicionario_completo = {**carregar_dicionario(ARQUIVO_GABARITO), **carregar_dicionario(ARQUIVO_MEMORIA)}
    textos_na_tela = [elem.info['text'] for elem in d.xpath('//android.widget.TextView').all()]

    # 1. TELA DE ERRO (Aprendizado)
    if d(textContains="Incorreto").exists or d(textContains="Resposta correta:").exists:
        print("\n[ERRO] Extraindo gabarito da tela vermelha...")
        texto_correto = ""
        for i, t in enumerate(textos_na_tela):
            if "Resposta correta:" in t and i + 1 < len(textos_na_tela):
                candidato = textos_na_tela[i + 1]
                if "EXPLIQUE" not in candidato.upper() and "REPORTAR" not in candidato.upper():
                    texto_correto = candidato
                break
        
        if texto_correto and frase_atual_cache:
            print(f"[BD] Salvando -> Errou: '{frase_atual_cache}' | Correta: '{texto_correto}'")
            memoria = carregar_dicionario(ARQUIVO_MEMORIA)
            memoria[frase_atual_cache.lower().strip()] = texto_correto
            with open(ARQUIVO_MEMORIA, 'w', encoding='utf-8') as f:
                json.dump(memoria, f, ensure_ascii=False, indent=4)
                
        d(text="Entendi").click_exists() or d(text="CONTINUAR").click_exists()
        return

    # 2. PULAR ÁUDIOS / CONFIRMAÇÕES
    if d(text="NÃO POSSO OUVIR AGORA").exists or d(text="NÃO POSSO FALAR AGORA").exists:
        d(text="NÃO POSSO OUVIR AGORA").click_exists() or d(text="NÃO POSSO FALAR AGORA").click_exists()
        return
    if d(textContains="Vamos pular os exercícios").exists or d(textContains="Foi quase! Tente de novo!").exists:
        d(text="CONTINUAR").click_exists()
        return

    # 3. TRANSIÇÃO DE TELA (Acertos)
    if d(text="CONTINUAR").exists:
        d(text="CONTINUAR").click()
        return

    # 4. EXERCÍCIO DE DIGITAÇÃO (EditText na tela)
    if d(className="android.widget.EditText").exists:
        frase_atual_cache = " ".join([t for t in textos_na_tela if len(t) > 4 and not t.isupper()])
        # Se for tradução para o inglês sem blocos de palavras (somente o teclado livre)
        resolver_digitacao(textos_na_tela)
        return

    # 5. EXERCÍCIO: COMBINE OS PARES
    if d(textContains="Combine os pares").exists:
        resolver_pares(textos_na_tela)
        return

    # 6. EXERCÍCIO: MÚLTIPLA ESCOLHA (Leia/Responda, Espaço vazio, Complete conversa)
    if d(textContains="Leia e responda").exists or d(textContains="Complete o espaço vazio").exists or d(textContains="Complete a conversa").exists or d(textContains="Escolha a tradução").exists:
        resolver_multipla_escolha(textos_na_tela)
        return

    # 7. EXERCÍCIO DE TRADUÇÃO TRADICIONAL
    if d(textContains="Traduza esta frase").exists:
        frase_alvo = extrair_frase_alvo(textos_na_tela)
                
        if frase_alvo:
            frase_atual_cache = frase_alvo
            print(f"\n[ALVO] '{frase_alvo}'")
            
            resposta_exata = dicionario_completo.get(frase_alvo.lower().strip())
            
            # SE ACHOU NO GABARITO (Velocidade Máxima)
            if resposta_exata:
                print(f"[GABARITO] Resolvendo instantaneamente: '{resposta_exata}'")
                for palavra in resposta_exata.split():
                    # Usa Regex de Case Insensitive no UiAutomator2 (!MÁGICA!)
                    match_regex = f"(?i)^{re.escape(palavra)}$"
                    
                    if d(textMatch=match_regex).exists: 
                        d(textMatch=match_regex).click()
                    else:
                        # Fallback de aproximação caso haja pontuação colada
                        opcoes = [t for t in textos_na_tela if len(t) < 25]
                        matches = difflib.get_close_matches(palavra, opcoes, n=1, cutoff=0.6)
                        if matches: d(textMatch=f"(?i)^{re.escape(matches[0])}$").click()
                
                time.sleep(0.3)
                d(text="VERIFICAR").click_exists() or d(text="CHECK").click_exists()
                
            # SE NÃO ACHOU (Modo Tradutor Fallback)
            else:
                print("[IA] Frase inédita. Acionando tradutor para adivinhar...")
                try:
                    chute = GoogleTranslator(source='auto', target='pt').translate(frase_alvo)
                    chute_limpo = chute.replace(".", "").replace(",", "").replace("!", "").replace("?", "").lower().strip()
                    print(f"[IA CHUTE] '{chute_limpo}'")
                    
                    # Pega apenas botões da parte inferior da tela para não clicar na frase da instrução
                    opcoes_botoes = []
                    altura_tela = d.info['displayHeight']
                    for elem in d.xpath('//android.widget.TextView').all():
                        if elem.info['bounds']['top'] > (altura_tela * 0.4): # Abaixo da metade da tela
                            opcoes_botoes.append(elem.info['text'].strip())
                    
                    for palavra in chute_limpo.split():
                        match_regex = f"(?i)^{re.escape(palavra)}$"
                        if d(textMatch=match_regex).exists:
                            d(textMatch=match_regex).click()
                        else:
                            matches = difflib.get_close_matches(palavra, opcoes_botoes, n=1, cutoff=0.5)
                            if matches:
                                print(f"  [Match Aproximado] {palavra} -> {matches[0]}")
                                d(textMatch=f"(?i)^{re.escape(matches[0])}$").click()
                                opcoes_botoes.remove(matches[0])
                    
                    time.sleep(0.5)
                    d(text="VERIFICAR").click_exists() or d(text="CHECK").click_exists()
                except Exception as e:
                    print(f"[ERRO TRADUTOR] {e}")
        return

def loop_principal():
    print("Módulo Autônomo Iniciado. Pressione Ctrl+C para parar.")
    while True:
        try:
            resolver_tela()
        except Exception:
            time.sleep(0.5)

if __name__ == "__main__":
    loop_principal()