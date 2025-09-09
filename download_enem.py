import os
import time
import random
import logging
import requests
import re
import unicodedata  # Importação necessária para a solução definitiva
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

# --- Configurações Iniciais ---
BASE_URL = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos"
OUTPUT_DIR = "data"
LOG_FILE = "crawler_enem.log"

# Lista para armazenar as ocorrências de erros/avisos para o relatório final
REPORTS = []

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)

# --- Funções do Crawler ---


def normalizar_texto_para_comparacao(texto):
    """
    Normaliza uma string para comparação:
    1. Trata casos especiais de caracteres e entidades HTML (&nbsp;, –).
    2. Remove indicadores ordinais (º, ª).
    3. Remove acentos e diacríticos.
    4. Converte para minúsculas.
    5. Substitui caracteres não alfanuméricos por espaço (incluindo hífens).
    6. Padroniza múltiplos espaços para um único espaço e remove espaços nas extremidades.
    """
    if texto is None:
        return ""

    # Passo 1: Tratar casos especiais de caracteres e entidades HTML
    texto = texto.replace("&nbsp;", " ")
    texto = texto.replace("–", "-")  # Converte en-dash para hífen padrão

    # Passo 2: Remover indicadores ordinais (º, ª) antes da normalização Unicode
    texto = texto.replace("º", "").replace("ª", "")

    # Passo 3: Remover acentos e diacríticos (á, ç, ã -> a, c, a)
    texto = (
        unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode("utf-8")
    )

    # Passo 4: Converter para minúsculas
    texto = texto.lower()

    # Passo 5: Substituir qualquer caractere que NÃO seja letra (a-z) ou número (0-9) por um espaço.
    # Isso irá transformar pontuações, hífens, etc., em espaços.
    texto = re.sub(r"[^a-z0-9]+", " ", texto)

    # Passo 6: Padronizar múltiplos espaços (resultantes do passo anterior) para um único espaço
    # e remover espaços em branco extras no início e fim.
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def gerar_atraso_aleatorio(min_seg=1, max_seg=5):
    """Gera um atraso aleatório para simular comportamento humano."""
    delay = random.uniform(min_seg, max_seg)
    logging.info(f"Aguardando {delay:.2f} segundos...")
    time.sleep(delay)


def iniciar_navegador():
    """Configura e inicia uma instância do navegador Chrome em modo headless."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    )

    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        logging.info("Navegador Chrome iniciado com sucesso em modo headless.")
        return driver
    except WebDriverException as e:
        logging.error(f"Erro ao iniciar o navegador: {e}")
        REPORTS.append(f"CRÍTICO: Erro ao iniciar o navegador: {e}")
        return None


def acessar_pagina(driver, url):
    """Navega para uma URL específica e espera que a página esteja carregada."""
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "content-core"))
        )
        logging.info(f"Página acessada: {url}")
        return True
    except TimeoutException:
        logging.error(f"Tempo limite excedido ao carregar a página: {url}")
        REPORTS.append(
            f"ERRO: Tempo limite excedido ao carregar a página inicial: {url}"
        )
        return False
    except WebDriverException as e:
        logging.error(f"Erro ao acessar a página {url}: {e}")
        REPORTS.append(f"ERRO: Erro ao acessar a página inicial {url}: {e}")
        return False


def obter_anos_disponiveis(driver):
    """Identifica dinamicamente todos os anos com provas disponíveis."""
    anos = []
    try:
        tab_elements = driver.find_elements(
            By.CSS_SELECTOR, "div.govbr-tabs .tabs .tab a[data-id]"
        )
        for tab in tab_elements:
            ano = tab.get_attribute("data-id")
            if ano and ano != "Sobre":
                anos.append(ano)
        logging.info(f"Anos disponíveis identificados: {', '.join(anos)}")
        return sorted(anos, reverse=True)
    except NoSuchElementException:
        logging.error("Não foi possível encontrar os elementos das abas de ano.")
        REPORTS.append("ERRO: Não foi possível encontrar os elementos das abas de ano.")
        return []
    except Exception as e:
        logging.error(f"Erro ao obter anos disponíveis: {e}")
        REPORTS.append(f"ERRO: Erro ao obter anos disponíveis: {e}")
        return []


def clicar_aba_ano(driver, ano):
    """Ativa a aba correspondente a um ano específico e aguarda seu carregamento."""
    try:
        tab_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f"div.tab a[data-id='{ano}']"))
        )

        driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            tab_link,
        )
        gerar_atraso_aleatorio(0.5, 1.5)

        try:
            tab_link.click()
        except WebDriverException as e:
            if "element click intercepted" in str(e):
                logging.warning(
                    f"Clique normal interceptado para o ano '{ano}'. Tentando clique via JavaScript."
                )
                driver.execute_script("arguments[0].click();", tab_link)
            else:
                raise e

        logging.info(f"Clicou na aba do ano: {ano}")

        # MELHORIA 1: Esperar por elementos de conteúdo em vez de data-loaded
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    f"div.tab-content[data-id='{ano}'] h3, div.tab-content[data-id='{ano}'] p.callout",
                )
            )
        )
        logging.info(
            f"Conteúdo da aba '{ano}' carregado (verificado por título/callout)."
        )
        return True
    except TimeoutException:
        logging.error(
            f"Tempo limite excedido ao carregar conteúdo da aba para o ano: {ano} (nenhum título ou callout encontrado)."
        )
        REPORTS.append(
            f"ERRO: Falha ao carregar conteúdo da aba para o ano {ano} (timeout ou falta de elementos de conteúdo)."
        )
        return False
    except NoSuchElementException:
        logging.error(f"Aba para o ano '{ano}' não encontrada.")
        REPORTS.append(f"ERRO: Aba para o ano {ano} não encontrada.")
        return False
    except WebDriverException as e:
        logging.error(f"Erro ao clicar ou carregar a aba do ano '{ano}': {e}")
        REPORTS.append(f"ERRO: Erro ao interagir com a aba do ano {ano}: {e}")
        return False


def _extrair_prova_gabarito_links(
    container_elemento, description_for_logs, keywords_to_match, ano, tipo_base
):
    """
    Função auxiliar para extrair links de prova e gabarito.
    Usa uma lista de palavras-chave normalizadas para encontrar o p.callout de forma mais genérica.
    A lógica de busca de links é mais flexível, buscando links 'Prova' e 'Gabarito' após o callout,
    independentemente da estrutura exata de ULs intermediários.
    """
    links = []
    found_callout = None

    try:
        callout_elements = container_elemento.find_elements(
            By.CSS_SELECTOR, "p.callout"
        )

        for element in callout_elements:
            raw_text = element.text
            normalized_element_text = normalizar_texto_para_comparacao(raw_text)
            # logging.debug(f"DEBUG - Raw Callout Text: '{raw_text}'")
            # logging.debug(f"DEBUG - Normalized Callout Text: '{normalized_element_text}'")
            # logging.debug(f"DEBUG - Keywords to Match: {keywords_to_match}")
            # match_found = all(keyword in normalized_element_text for keyword in keywords_to_match)
            # logging.debug(f"DEBUG - Match result: {match_found}")

            if all(keyword in normalized_element_text for keyword in keywords_to_match):
                found_callout = element
                break

        if not found_callout:
            raise NoSuchElementException(
                f"Nenhum callout correspondente às palavras-chave '{keywords_to_match}' encontrado."
            )

        logging.info(
            f"Callout encontrado para descrição '{description_for_logs}' em {ano}."
        )

        # START OF MODIFICATION - Implementação da Abordagem 2 (XPath Combinado)
        # O start_element é sempre o found_callout.
        # O XPath é expandido para procurar links tanto como irmãos do callout,
        # quanto como irmãos do pai do callout.
        base_element_for_link_search = found_callout

        # XPath combinado para lidar com as estruturas de 2023 e 2024
        xpath_combined_links = (
            "./following-sibling::ul//a | "  # Links em ULs irmãos (estrutura 2024)
            "./following-sibling::div//a | "  # Links em DIVs irmãos (se houver, para flexibilidade)
            "./parent::*/following-sibling::ul//a | "  # Links em ULs irmãos do pai (estrutura 2023)
            "./parent::*/following-sibling::div//a"  # Links em DIVs irmãos do pai (para flexibilidade)
        )

        all_following_links_in_siblings = base_element_for_link_search.find_elements(
            By.XPATH, xpath_combined_links
        )
        # END OF MODIFICATION

        prova_link_found = None
        gabarito_link_found = None

        for link_element in all_following_links_in_siblings:
            link_text_normalized = normalizar_texto_para_comparacao(link_element.text)
            if "prova" in link_text_normalized and not prova_link_found:
                prova_link_found = link_element.get_attribute("href")
            elif "gabarito" in link_text_normalized and not gabarito_link_found:
                gabarito_link_found = link_element.get_attribute("href")

            if prova_link_found and gabarito_link_found:
                break

        if prova_link_found:
            links.append(
                {"ano": ano, "tipo": f"{tipo_base}_prova_azul", "url": prova_link_found}
            )
            logging.info(
                f"Link de prova para '{description_for_logs}' em {ano} encontrado."
            )
        else:
            msg = f"AVISO: Link de prova não encontrado para '{description_for_logs}' em {ano}."
            logging.warning(msg)
            REPORTS.append(msg)

        if gabarito_link_found:
            links.append(
                {
                    "ano": ano,
                    "tipo": f"{tipo_base}_gabarito_azul",
                    "url": gabarito_link_found,
                }
            )
            logging.info(
                f"Link de gabarito para '{description_for_logs}' em {ano} encontrado."
            )
        else:
            msg = f"AVISO: Link de gabarito não encontrado para '{description_for_logs}' em {ano}."
            logging.warning(msg)
            REPORTS.append(msg)

    except NoSuchElementException as e:
        msg = f"AVISO: Não encontrado o padrão '{description_for_logs}' (palavras-chave: {keywords_to_match}) ou seus links para {ano}: {e}"
        logging.warning(msg)
        REPORTS.append(msg)
    except Exception as e:
        msg = f"ERRO: Erro inesperado ao extrair links para o padrão '{description_for_logs}' (palavras-chave: {keywords_to_match}) para {ano}: {e}"
        logging.error(msg)
        REPORTS.append(msg)

    return links


def extrair_links_provas_e_gabaritos(driver, ano):
    """
    Encontra e retorna os links de download para as provas e gabaritos
    do caderno azul, e tema da redação de reaplicação, para um dado ano.
    Inclui lógica para Aplicação Digital.
    """
    links_encontrados = []

    try:
        container_ano = driver.find_element(
            By.CSS_SELECTOR, f"div.tab-content[data-id='{ano}']"
        )

        # --- Aplicação Regular ---
        logging.info(f"Buscando links de Aplicação Regular para {ano}...")

        # Keywords refinadas para incluir o número do caderno para maior precisão
        regular_d1_keywords = ["1 dia", "caderno 1", "azul", "aplicacao regular"]
        regular_d2_keywords = ["2 dia", "caderno 7", "azul", "aplicacao regular"]

        links_encontrados.extend(
            _extrair_prova_gabarito_links(
                container_ano,
                "1º Dia - Caderno 1 - Azul - Aplicação Regular",
                regular_d1_keywords,
                ano,
                "regular_d1",
            )
        )
        links_encontrados.extend(
            _extrair_prova_gabarito_links(
                container_ano,
                "2º Dia - Caderno 7 - Azul - Aplicação Regular",
                regular_d2_keywords,
                ano,
                "regular_d2",
            )
        )

        # --- Aplicação Digital (NOVO) ---
        logging.info(f"Buscando links de Aplicação Digital para {ano}...")

        # Mantemos as palavras-chave da Aplicação Digital mais genéricas,
        # pois o HTML de exemplo não forneceu números de caderno específicos para 'Azul'.
        digital_d1_keywords = ["1 dia", "caderno", "azul", "aplicacao digital"]
        digital_d2_keywords = ["2 dia", "caderno", "azul", "aplicacao digital"]

        links_encontrados.extend(
            _extrair_prova_gabarito_links(
                container_ano,
                "1º Dia - Caderno Azul - Aplicação Digital",
                digital_d1_keywords,
                ano,
                "digital_d1",
            )
        )
        links_encontrados.extend(
            _extrair_prova_gabarito_links(
                container_ano,
                "2º Dia - Caderno Azul - Aplicação Digital",
                digital_d2_keywords,
                ano,
                "digital_d2",
            )
        )

        # --- Reaplicação/PPL ---
        logging.info(f"Buscando links de Reaplicação/PPL para {ano}...")

        # Tema da Redação Reaplicação/PPL
        try:
            tema_redacao_link_element = container_ano.find_element(
                By.XPATH, ".//a[contains(., 'Tema da Redação')]"
            )
            links_encontrados.append(
                {
                    "ano": ano,
                    "tipo": "reaplicacao_redacao",
                    "url": tema_redacao_link_element.get_attribute("href"),
                }
            )
            logging.info(f"Link Tema da Redação (Reaplicação) para {ano} encontrado.")
        except NoSuchElementException:
            msg = f"AVISO: Tema da Redação (Reaplicação) não encontrado para {ano} (pode não existir)."
            logging.info(msg)
            REPORTS.append(msg)

        # Keywords refinadas para incluir o número do caderno para maior precisão, se aplicável
        # Baseado no HTML de 2024 e 2022, Reaplicação/PPL usa "Caderno 1" para D1 e "Caderno 7" para D2 Azul.
        reap_d1_keywords = ["1 dia", "caderno 1", "azul", "reaplicacao ppl"]
        reap_d2_keywords = ["2 dia", "caderno 7", "azul", "reaplicacao ppl"]

        links_encontrados.extend(
            _extrair_prova_gabarito_links(
                container_ano,
                "1º Dia - Caderno 1 - Azul - Reaplicação/PPL",
                reap_d1_keywords,
                ano,
                "reaplicacao_d1",
            )
        )
        links_encontrados.extend(
            _extrair_prova_gabarito_links(
                container_ano,
                "2º Dia - Caderno 7 - Azul - Reaplicação/PPL",
                reap_d2_keywords,
                ano,
                "reaplicacao_d2",
            )
        )

    except NoSuchElementException:
        msg = f"ERRO: Container da aba para o ano '{ano}' não encontrado para extração de links."
        logging.error(msg)
        REPORTS.append(msg)
    except Exception as e:
        msg = f"ERRO: Erro ao extrair links para o ano '{ano}': {e}"
        logging.error(msg)
        REPORTS.append(msg)

    return links_encontrados


def criar_diretorio_ano(ano):
    """Cria a estrutura de diretórios data/{ano}/ se ela não existir."""
    path = os.path.join(OUTPUT_DIR, ano)
    if not os.path.exists(path):
        os.makedirs(path)
        logging.info(f"Diretório criado: {path}")
    else:
        logging.info(f"Diretório já existe: {path}")
    return path


def baixar_arquivo(
    url_download, caminho_destino, max_retries=3, delay_between_retries=5
):
    """
    Baixa um arquivo de uma URL e o salva no caminho especificado,
    com lógica de retries para erros de conexão.
    """
    for attempt in range(max_retries):
        try:
            logging.info(
                f"Tentando baixar (tentativa {attempt + 1}/{max_retries}): {os.path.basename(caminho_destino)}"
            )
            response = requests.get(url_download, stream=True, timeout=30)
            response.raise_for_status()

            with open(caminho_destino, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(
                f"Arquivo baixado com sucesso: {os.path.basename(caminho_destino)}"
            )
            return True

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            msg = f"AVISO: Erro de conexão/timeout ao baixar {os.path.basename(caminho_destino)} (tentativa {attempt + 1}/{max_retries}): {e}"
            logging.warning(msg)
            if attempt < max_retries - 1:
                logging.info(
                    f"Aguardando {delay_between_retries} segundos antes de tentar novamente..."
                )
                time.sleep(delay_between_retries)
            else:
                final_msg = f"ERRO: Falha ao baixar {os.path.basename(caminho_destino)} após {max_retries} tentativas devido a erro de conexão/timeout."
                logging.error(final_msg)
                REPORTS.append(final_msg)

        except requests.exceptions.RequestException as e:
            msg = f"ERRO: Erro de requisição ao baixar {os.path.basename(caminho_destino)}: {e}"
            logging.error(msg)
            REPORTS.append(msg)
            break

        except Exception as e:
            msg = f"ERRO: Erro genérico ao baixar o arquivo {os.path.basename(caminho_destino)}: {e}"
            logging.error(msg)
            REPORTS.append(msg)
            break

    return False


# --- Fluxo Principal do Crawler ---


def main():
    driver = None
    try:
        logging.info("Iniciando o Enem Crawler...")
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            logging.info(f"Diretório principal de saída criado: {OUTPUT_DIR}")

        driver = iniciar_navegador()
        if not driver:
            return

        if not acessar_pagina(driver, BASE_URL):
            return

        gerar_atraso_aleatorio(2, 5)

        anos_disponiveis = obter_anos_disponiveis(driver)
        if not anos_disponiveis:
            logging.error("Nenhum ano disponível encontrado. Encerrando o crawler.")
            REPORTS.append(
                "CRÍTICO: Nenhum ano disponível foi encontrado. O crawler não pôde prosseguir."
            )
            return

        for ano in anos_disponiveis:
            logging.info(f"\n--- Processando provas do ano: {ano} ---")
            gerar_atraso_aleatorio(3, 7)

            if not clicar_aba_ano(driver, ano):
                logging.warning(
                    f"Pulando o ano {ano} devido a falha ao clicar ou carregar a aba. Detalhes acima."
                )
                continue

            gerar_atraso_aleatorio(5, 10)

            links_para_baixar = extrair_links_provas_e_gabaritos(driver, ano)

            if not links_para_baixar:
                msg = f"AVISO: Nenhum link relevante para baixar encontrado para o ano {ano}. Prosseguindo para o próximo."
                logging.info(msg)
                REPORTS.append(msg)
                continue

            caminho_base_ano = criar_diretorio_ano(ano)

            for link_info in links_para_baixar:
                url_download = link_info["url"]
                tipo_prova = link_info["tipo"]

                file_extension = os.path.splitext(url_download.split("/")[-1])[1]
                if not file_extension:
                    file_extension = ".pdf"

                nome_arquivo = f"ENEM_{ano}_{tipo_prova}{file_extension}"
                caminho_destino = os.path.join(caminho_base_ano, nome_arquivo)

                if os.path.exists(caminho_destino):
                    logging.info(
                        f"Arquivo já existe, pulando download: {os.path.basename(caminho_destino)}"
                    )
                else:
                    baixar_arquivo(url_download, caminho_destino)
                    gerar_atraso_aleatorio(1, 4)

            logging.info(f"--- Finalizado o processamento do ano: {ano} ---")

    except Exception as e:
        logging.critical(
            f"Erro crítico no fluxo principal do crawler: {e}", exc_info=True
        )
        REPORTS.append(f"CRÍTICO: Erro inesperado no fluxo principal: {e}")
    finally:
        if driver:
            finalizar_navegador(driver)
            logging.info("Navegador encerrado.")

        logging.info("\n--- Resumo Final do Crawler ---")
        if REPORTS:
            logging.info(
                f"Foram encontrados {len(REPORTS)} itens com problemas ou não encontrados:"
            )
            for report_item in REPORTS:
                logging.warning(f"- {report_item}")
        else:
            logging.info(
                "Todas as provas e gabaritos esperados foram processados sem problemas reportados."
            )

        logging.info("Crawler concluído.")


def finalizar_navegador(driver):
    """Fecha e encerra a instância do navegador."""
    try:
        driver.quit()
    except WebDriverException as e:
        logging.error(f"Erro ao fechar o navegador: {e}")


if __name__ == "__main__":
    main()
