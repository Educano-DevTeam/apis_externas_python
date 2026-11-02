# Documentação Geral — APIs Externas em Python

## 1. Visão geral

Este repositório reúne dois projetos desenvolvidos em Python para integração com APIs externas. Ambos têm foco no processamento e na análise de dados, sem implementação de interface gráfica.

Os programas atuam como clientes consumidores de serviços externos: enviam requisições HTTP, recebem respostas em JSON, validam e organizam os registros e executam operações sobre os dados. Os resultados são apresentados no terminal e, no projeto de voos, também podem ser exportados para arquivos CSV.

### Projetos

| Projeto | Fontes de dados | Finalidade |
|---|---|---|
| Rastreador de Voos | OpenSky Network | Consultar aeronaves, trajetórias e registros históricos de chegadas e partidas |
| Indicadores Econômicos Brasileiros | Banco Central do Brasil (SGS) e IPEADATA | Consultar séries econômicas, comparar indicadores e calcular correlação e regressão linear |

## 2. Tecnologias utilizadas

- **Python 3:** linguagem utilizada na implementação da lógica, integração, tratamento e análise dos dados.
- **Requests:** realiza as requisições HTTP às APIs externas.
- **Pandas:** organiza os dados em estruturas tabulares, trata séries temporais, alinha datas e exporta resultados em CSV no projeto de voos.
- **NumPy:** realiza o ajuste da regressão linear por meio de operações numéricas no projeto econômico.
- **ThreadPoolExecutor (biblioteca padrão):** permite consultar diferentes indicadores em paralelo no projeto econômico.
- **Datetime (biblioteca padrão):** trabalha com datas, períodos e conversão de timestamps.
- **JSON:** formato utilizado pelas APIs para retornar os dados.

Não há banco de dados próprio nem servidor web nesses scripts. A execução é feita localmente pelo terminal, e os dados são consultados diretamente nas fontes externas.

## 3. Organização do repositório

```text
apis_externas_python/
├── APIS Externas V/
│   └── API Rastreador de Voos/
│       └── main.py
├── APIs Externas IV/
│   └── API Indicadores Econômicos Brasileiros/
│       └── main.py
└── README.md
```

Cada projeto possui seu próprio arquivo `main.py` e pode ser executado de forma independente.

## 4. Requisitos gerais

- Python 3 instalado.
- Acesso à internet.
- Terminal (PowerShell, Prompt de Comando, Git Bash ou terminal de uma IDE).
- Bibliotecas Python utilizadas pelo projeto correspondente.

Instale as dependências com:

```bash
python -m pip install requests pandas numpy
```

O projeto de rastreamento de voos utiliza `requests` e `pandas`. O projeto econômico utiliza `requests`, `pandas` e `numpy`.

## 5. Como obter o código

Clone o repositório:

```bash
git clone https://github.com/Educano-DevTeam/apis_externas_python.git
```

Entre na pasta:

```bash
cd apis_externas_python
```

Também é possível baixar o repositório como ZIP pela página do GitHub.

## 6. Como executar

Abra um terminal na pasta do projeto desejado e execute o arquivo `main.py`.

**Rastreador de Voos — Windows:**

```powershell
cd "APIS Externas V/API Rastreador de Voos"
python main.py
```

**Indicadores Econômicos — Windows:**

```powershell
cd "APIs Externas IV/API Indicadores Econômicos Brasileiros"
python main.py
```

Em ambientes nos quais o comando `python` não funciona, tente `py main.py` no Windows ou `python3 main.py` em Linux/macOS.

## 7. APIs externas e credenciais

Cada projeto consulta serviços mantidos por terceiros. As APIs são as fontes dos dados; os scripts deste repositório são responsáveis por solicitar, tratar e analisar as respostas.

- **OpenSky Network:** exige credenciais OAuth2 de aplicação para o fluxo utilizado pelo rastreador. Consulte a documentação oficial e crie uma aplicação/credenciais na área de conta da OpenSky.
- **Banco Central do Brasil — SGS:** disponibiliza séries temporais públicas. Para os endpoints utilizados pelo projeto, não é necessária chave de API.
- **IPEADATA:** disponibiliza dados por meio de uma API OData pública. Para as consultas implementadas, não é necessária chave de API.

As instruções específicas de cadastro, configuração e endpoints estão nos documentos individuais.

## 8. Segurança das credenciais

Credenciais não devem ser publicadas no código-fonte, em repositórios públicos, prints ou documentos. No projeto OpenSky, configure `OPENSKY_CLIENT_ID` e `OPENSKY_CLIENT_SECRET` como variáveis de ambiente e faça o código lê-las com `os.getenv()`.

Exemplo de configuração no PowerShell, válido somente para a janela atual:

```powershell
$env:OPENSKY_CLIENT_ID="seu_client_id"
$env:OPENSKY_CLIENT_SECRET="seu_client_secret"
```

No `main.py` do rastreador, confirme que as constantes são lidas do ambiente:

```python
CLIENT_ID = os.getenv("OPENSKY_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET", "")
```

Na versão consultada do repositório, essas constantes estavam definidas diretamente no código; portanto, essa substituição é necessária para que os comandos de configuração acima funcionem. Se você já realizou essa alteração localmente, basta conferir se ela também está na versão que será entregue.

Se uma credencial já foi publicada, removê-la do arquivo não invalida o segredo: é necessário revogá-lo no serviço e gerar outro. Nunca reutilize credenciais que tenham sido expostas.

## 9. Tratamento e limitações dos dados

As APIs podem apresentar indisponibilidade, limites de requisição, registros incompletos ou atrasos de atualização. Por isso, os scripts incluem validações e tratamento de erros, mas os resultados dependem da disponibilidade e da cobertura das fontes.

Os horários retornados pelo rastreador são apresentados em UTC. Os dados de voos representam informações observadas/processadas pela OpenSky e não devem ser interpretados como uma grade comercial oficial de companhias aéreas.

No projeto econômico, frequências distintas são convertidas para uma base mensal para permitir comparações. A média mensal é utilizada para séries diárias; séries menos frequentes, quando aplicável, podem manter o último valor conhecido até a próxima observação. Essa transformação facilita o alinhamento, mas não cria novas observações econômicas.

Correlação indica associação estatística, não causalidade. Séries econômicas com tendência podem apresentar correlação elevada mesmo sem relação causal direta.

## 10. Autoria e responsabilidade pelo desenvolvimento

**Responsável pelo desenvolvimento dos códigos: Miguel Soares de Sousa.**

A implementação dos scripts, incluindo a estrutura dos programas, integração com as APIs, tratamento das respostas, filtros, organização dos dados, cálculos e menus de execução, foi realizada por Miguel Soares de Sousa.

As APIs OpenSky Network, Banco Central do Brasil e IPEADATA são serviços externos independentes. Seus dados e serviços não são de autoria do desenvolvedor dos scripts.

## 11. Referências oficiais

- Repositório do projeto: https://github.com/Educano-DevTeam/apis_externas_python
- OpenSky Network — documentação da API: https://openskynetwork.github.io/opensky-api/
- OpenSky Network — portal: https://opensky-network.org/
- Banco Central do Brasil — API de dados abertos / SGS: https://dadosabertos.bcb.gov.br/
- IPEADATA: http://www.ipeadata.gov.br/
- Python: https://docs.python.org/3/
- Requests: https://requests.readthedocs.io/
- Pandas: https://pandas.pydata.org/docs/
- NumPy: https://numpy.org/doc/
