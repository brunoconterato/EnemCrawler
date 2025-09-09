# Enem Crawler

Um web crawler robusto desenvolvido em Python utilizando Selenium para baixar provas e gabaritos de edições anteriores do Exame Nacional do Ensino Médio (ENEM) diretamente do portal do INEP.

## 🎯 Objetivos do Projeto

O principal objetivo deste projeto é automatizar o processo de download das provas e gabaritos do ENEM para fins de estudo, análise ou arquivamento. O crawler foi projetado para:

- **Extrair provas e gabaritos de forma dinâmica:** Identificar automaticamente os anos disponíveis na página do INEP, garantindo que novas edições sejam incluídas sem a necessidade de atualização do código.
- **Baixar provas e gabaritos específicos:** Focar na coleta das provas e gabaritos do "Caderno Azul" para o Dia 1 e Dia 2 da Aplicação Regular, e, quando disponíveis, das provas e gabaritos do "Caderno Azul" para o Dia 1 e Dia 2 da Reaplicação/PPL, juntamente com o tema da redação de Reaplicação/PPL.
- **Organizar os arquivos baixados:** Salvar os documentos em uma estrutura de diretórios organizada por ano (`data/{ano}/`).

## 💪 Robustez e Segurança (Anti-Detecção de Bots)

Este crawler foi construído com foco em robustez e na minimização da detecção por mecanismos anti-bot:

- **Atrasos Aleatórios:** Todas as interações significativas (navegação, cliques em abas, downloads) são intercaladas com atrasos aleatórios. Isso simula um comportamento humano mais natural, evitando um padrão de requisições fixo e repetitivo.
- **Modo Headless com User-Agent:** O Selenium é configurado para rodar em modo headless (sem interface gráfica), o que é eficiente para automação em segundo plano. Além disso, um `User-Agent` de navegador real é definido para que as requisições não sejam facilmente identificadas como vindas de um bot.
- **Seletores Resilientes:** A identificação dos elementos HTML na página (abas de anos, links de download) é feita utilizando seletores CSS e XPath que priorizam atributos únicos (`data-id`) e o texto visível dos elementos (`contains(text(), '...')`). Isso torna o crawler menos vulnerável a pequenas alterações no layout da página que poderiam quebrar seletores baseados em ordem ou classes genéricas.
- **Tratamento de Exceções:** O código incorpora `try-except` em todas as etapas críticas para lidar com erros de rede, elementos não encontrados, tempos limite de carregamento da página ou outras anomalias. Isso impede que o crawler pare abruptamente e permite que ele tente se recuperar ou continue o processamento para os próximos itens.

## ⚙️ Boas Práticas de Programação

O projeto adere a princípios de boas práticas de programação para garantir um código limpo, legível e de fácil manutenção:

- **Modularização com Funções:** O código é dividido em funções pequenas e com responsabilidades bem definidas. Cada função tem um único propósito claro (ex: `iniciar_navegador()`, `obter_anos_disponiveis()`, `baixar_arquivo()`).
- **Logging Detalhado:** Utiliza o módulo `logging` do Python para registrar o progresso da execução, avisos (elementos não encontrados que não são críticos) e erros (falhas que impedem o avanço). Isso é essencial para monitorar o crawler e depurar problemas.
- **Configurações Externas:** Variáveis como `BASE_URL`, `OUTPUT_DIR` e `LOG_FILE` são definidas no início do script, facilitando a configuração do projeto sem modificar a lógica principal.
- **Comentários Explicativos:** O código é bem comentado para descrever a lógica por trás de cada função e seção.

## 🚧 Tratamento de Erros

Um sistema abrangente de tratamento de erros foi implementado:

- **Captura de Exceções Específicas:** O código captura exceções específicas do Selenium (como `TimeoutException`, `NoSuchElementException`, `WebDriverException`) e do módulo `requests` (como `requests.exceptions.RequestException`), além de exceções gerais, permitindo um tratamento adequado para diferentes cenários de falha.
- **Logs Informes:** Erros e avisos são registrados no console e em um arquivo de log, fornecendo um histórico detalhado da execução e dos problemas encontrados.
- **Resiliência:** Em caso de falha ao processar um ano ou baixar um arquivo específico, o crawler tenta continuar para o próximo item, evitando a interrupção completa do processo.

## 🚀 Funcionamento Básico e Ordem Lógica de Execução

O crawler segue uma sequência lógica de passos para realizar sua tarefa:

1. **Inicialização:**
   - Verifica e cria o diretório de saída principal (`data/`).
   - Configura o sistema de `logging`.
   - Inicia o navegador Chrome em modo headless.
2. **Navegação Inicial:**
   - Acessa a URL base do INEP onde as provas do ENEM estão listadas.
   - Aguarda um tempo aleatório.
3. **Identificação de Anos:**
   - Analisa a estrutura da página para identificar dinamicamente todas as abas de anos disponíveis (ex: 2024, 2023, ..., 1998).
   - Os anos são processados em ordem decrescente (do mais recente para o mais antigo).
4. **Loop por Ano:** Para cada ano identificado:
   - **Atraso:** Aguarda um tempo aleatório antes de interagir.
   - **Ativação da Aba:** Clica no link da aba correspondente ao ano e espera que o conteúdo dessa aba seja carregado completamente (verificando o atributo `data-loaded="true"` ou a presença de um elemento chave).
   - **Extração de Links:** Busca e extrai as URLs de download para as provas e gabaritos do "Caderno Azul" (Aplicação Regular e Reaplicação/PPL, se houver) e o tema da redação de Reaplicação/PPL.
   - **Criação de Diretório:** Cria uma subpasta para o ano (`data/{ano}/`).
   - **Download de Arquivos:** Para cada link de download extraído:
     - Gera um nome de arquivo descritivo (`ENEM_{ano}_{tipo_prova}.pdf`).
     - Verifica se o arquivo já existe no destino para evitar downloads duplicados.
     - Baixa o arquivo para a pasta do ano.
     - Aguarda um tempo aleatório entre os downloads.
5. **Finalização:**
   - Após processar todos os anos, o navegador é encerrado.
   - Uma mensagem de conclusão é exibida nos logs.

## 🛠️ Requisitos

- Python 3.x
- `selenium`
- `requests`
- `webdriver-manager` (opcional, para gerenciar automaticamente o ChromeDriver) ou o `chromedriver` compatível com a sua versão do Chrome instalado no sistema e acessível no PATH.

As dependências são listadas em um arquivo `requirements.txt` (sugestão: crie este arquivo com `pip freeze > requirements.txt` após instalar as libs).

## 🚀 Como Executar

Para garantir um ambiente limpo e evitar conflitos de dependências com outros projetos Python, é altamente recomendável utilizar um ambiente virtual (`venv`).

1. **Certifique-se de ter o Google Chrome instalado** em seu sistema, pois o Selenium utilizará o ChromeDriver para interagir com ele.
2. **Crie um ambiente virtual (venv):**

   - Abra seu terminal ou prompt de comando.
   - Navegue até o diretório onde você salvou o arquivo `download_enem.py`.
   - Execute o seguinte comando para criar o ambiente virtual (um diretório chamado `venv` será criado):

     ```bash
     python -m venv venv
     ```

3. **Ative o ambiente virtual:**

   - **No Windows:**

     ```bash
     .\venv\Scripts\activate
     ```

   - **No macOS/Linux:**

     ```bash
     source venv/bin/activate
     ```

     Após a ativação, o nome do ambiente virtual (ex: `(venv)`) aparecerá no início da sua linha de comando, indicando que ele está ativo.

4. **Instale as dependências:**

   - Se você tiver um arquivo `requirements.txt` (recomendado), execute:

     ```bash
     pip install -r requirements.txt
     ```

   - Caso contrário, instale as bibliotecas manualmente:

     ```bash
     pip install selenium requests webdriver-manager
     ```

5. **Baixe o arquivo `download_enem.py`** para o mesmo diretório.
6. **Execute o script Python:**

   ```bash
   python download_enem.py
   ```

   O crawler iniciará suas operações. Você verá as mensagens de log no terminal, indicando o progresso, avisos e quaisquer erros. Os arquivos baixados serão armazenados na pasta `data/` criada no mesmo diretório de execução do script.

7. **Desativar o ambiente virtual (após terminar):**
   Quando você terminar de usar o crawler, pode desativar o ambiente virtual executando:

   ```bash
   deactivate
   ```

## 📄 Estrutura de Saída

Os arquivos baixados serão organizados da seguinte forma:

```plaintext
data/
├── 2024/
│   ├── ENEM_2024_regular_d1_prova_azul.pdf
│   ├── ENEM_2024_regular_d1_gabarito_azul.pdf
│   ├── ENEM_2024_regular_d2_prova_azul.pdf
│   ├── ENEM_2024_regular_d2_gabarito_azul.pdf
│   ├── ENEM_2024_reaplicacao_redacao.pdf (se houver)
│   ├── ENEM_2024_reaplicacao_d1_prova_azul.pdf (se houver)
│   ├── ENEM_2024_reaplicacao_d1_gabarito_azul.pdf (se houver)
│   ├── ENEM_2024_reaplicacao_d2_prova_azul.pdf (se houver)
│   └── ENEM_2024_reaplicacao_d2_gabarito_azul.pdf (se houver)
├── 2023/
│   └── ...
└── ...
```

---

**Observação:** Acesso funcional em Setembro/2025. A confiabilidade do crawler depende da estabilidade da estrutura HTML da página do INEP. Alterações significativas no layout podem exigir atualizações nos seletores utilizados.
