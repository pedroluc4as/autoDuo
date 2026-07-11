from playwright.sync_api import sync_playwright
import time

def iniciar_autoduo():
    with sync_playwright() as p:
        # Abre o Chrome de forma visível e salva o login na pasta "sessao_duolingo"
        navegador = p.chromium.launch_persistent_context(
            user_data_dir="./sessao_duolingo",
            headless=False, # False para vermos a tela, True para rodar invisível
            viewport={"width": 1280, "height": 720}
        )
        
        pagina = navegador.pages[0]
        pagina.goto("https://www.duolingo.com/")
        
        print("Faça o login manualmente se for a primeira vez.")
        print# O script pausa aqui por 60 segundos para você interagir
        time.sleep(9999999) 
        
        navegador.close()

if __name__ == "__main__":
    iniciar_autoduo()