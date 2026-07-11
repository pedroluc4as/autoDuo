import duolingo
import json

# Suas credenciais
USUARIO = "pedrosper4andio"
SENHA = ""

try:
    print("Conectando aos servidores do Duolingo...")
    lingo = duolingo.Duolingo(USUARIO, SENHA)
    
    # Puxa as palavras que você já aprendeu (Ex: do Inglês)
    print("Baixando vocabulário...")
    vocabulario = lingo.get_vocabulary(language_abbr='en')
    
    gabarito_api = {}
    
    for item in vocabulario['vocab_overview']:
        palavra_ingles = item['word_string']
        # Infelizmente a API oficial não entrega a tradução pronta no dump principal.
        # Precisamos de uma chamada para traduzir cada palavra.
        try:
            traducao = lingo.get_translations([palavra_ingles], target='pt')
            if palavra_ingles in traducao and traducao[palavra_ingles]:
                # Salva a primeira opção de tradução
                gabarito_api[palavra_ingles.lower()] = traducao[palavra_ingles][0].lower()
        except:
            pass

    # Salva no arquivo
    with open('gabarito.json', 'w', encoding='utf-8') as f:
        json.dump(gabarito_api, f, ensure_ascii=False, indent=4)
        
    print("Gabarito de palavras gerado com sucesso!")

except Exception as e:
    print(f"Erro na API: {e}")