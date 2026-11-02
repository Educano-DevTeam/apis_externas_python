# Documentação Técnica — API de Indicadores Econômicos Brasileiros

## 1. Objetivo

O projeto **API de Indicadores Econômicos Brasileiros** consulta séries históricas disponibilizadas pelo Banco Central do Brasil e pelo IPEADATA. Os dados recebidos são tratados, padronizados e utilizados em comparações e análises estatísticas.

O programa foi desenvolvido para trabalhar com os dados no terminal, sem geração de gráficos ou interface visual. A parte central da solução é a integração entre fontes distintas, o alinhamento temporal das séries e a execução dos cálculos.

## 2. Tecnologias e bibliotecas

- **Python 3:** linguagem utilizada na aplicação.
- **Requests:** realiza requisições HTTP às APIs do Banco Central e do IPEADATA.
- **Pandas:** organiza séries temporais, converte datas, trata valores ausentes, reamostra e alinha indicadores.
- **NumPy:** calcula os coeficientes da regressão linear por meio de `polyfit`.
- **ThreadPoolExecutor (concurrent.futures):** executa consultas independentes em paralelo.
- **Datetime:** define o período de consulta e converte datas e timestamps.

Instalação:

```bash
python -m pip install requests pandas numpy
```

## 3. Fontes de dados

### 3.1. Banco Central do Brasil — Sistema Gerenciador de Séries Temporais (SGS)

O SGS disponibiliza séries históricas de indicadores econômicos e financeiros.

- Portal de dados abertos: https://dadosabertos.bcb.gov.br/
- API utilizada: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`
- Formato solicitado: JSON.

Para as séries utilizadas neste projeto, a consulta é pública e não exige chave de API.

Indicadores configurados no código:

| Indicador | Código SGS | Frequência configurada |
|---|---:|---|
| Meta Selic | 432 | Diária |
| IPCA mensal | 433 | Mensal |
| Dólar comercial — venda | 1 | Diária |
| IGP-M | 189 | Mensal |

O programa envia as datas inicial e final no formato esperado pelo endpoint, recebe os registros e converte os valores para números.

### 3.2. IPEADATA

O IPEADATA disponibiliza séries econômicas por meio de uma API baseada em OData.

- Portal: http://www.ipeadata.gov.br/
- Endpoint base utilizado: `https://www.ipeadata.gov.br/api/odata4`
- Recurso consultado: `ValoresSerie(SERCODIGO='...')`.

Para as séries públicas utilizadas pelo projeto, não é necessário obter chave de API.

Indicadores configurados:

| Indicador | Código IPEADATA | Frequência configurada |
|---|---|---|
| IPCA mensal | `PRECOS12_IPCAG12` | Mensal |
| CDI mensal | `BM12_TJCDI12` | Mensal |
| IGP-M mensal | `IGP12_IGPMG12` | Mensal |

O programa percorre as páginas seguintes quando a resposta contém `@odata.nextLink`, filtra os registros pelo período e remove datas duplicadas.

## 4. Período de consulta

O código define:

- Data inicial fixa: 01/01/2020.
- Data final: data atual do computador no momento da execução.

Assim, a quantidade de registros pode aumentar ao longo do tempo, conforme as fontes atualizam suas séries. Também pode haver diferenças entre indicadores devido às suas frequências e calendários de publicação.

## 5. Funcionamento geral

1. O usuário executa `main.py`.
2. O programa apresenta o menu principal.
3. Na primeira opção que exige dados, as séries configuradas são consultadas.
4. As requisições ao BCB e ao IPEADATA são realizadas em paralelo.
5. As respostas são validadas e padronizadas em uma estrutura comum, com indicador, código, frequência, fonte, dados e eventual erro.
6. Os resultados são mantidos em memória por meio de cache para evitar consultas repetidas durante a mesma execução.
7. O usuário pode consultar os dados, comparar indicadores ou calcular correlação.

O cache é reiniciado quando o usuário escolhe a opção de atualização.

## 6. Funcionalidades implementadas

### 6.1. Consulta dos indicadores

A opção de consulta geral exibe, para cada série:

- nome do indicador;
- código;
- fonte dos dados;
- frequência;
- quantidade de registros recebidos;
- três registros mais recentes.

Falhas em uma fonte são registradas individualmente, permitindo que as demais consultas continuem sendo processadas.

### 6.2. Consulta simultânea

O projeto utiliza `ThreadPoolExecutor` com até cinco trabalhadores para consultar as séries do BCB e do IPEADATA em paralelo.

Essa abordagem reduz o tempo de espera em comparação com a execução estritamente sequencial, pois as consultas são independentes.

### 6.3. Comparação de indicadores — base 100

O usuário seleciona de dois a cinco indicadores disponíveis.

Antes da comparação, as séries são preparadas em frequência mensal:

- séries diárias: cálculo da média dos valores de cada mês;
- séries mensais: utilização do valor mensal disponível;
- séries trimestrais ou anuais, caso sejam adicionadas ao catálogo: manutenção do último valor conhecido até a próxima observação.

Depois, as séries são alinhadas pelas datas mensais em comum e os registros sem correspondência são removidos.

A normalização utiliza a fórmula:

\[
Índice_t = \frac{Valor_t}{Valor_{base}} \times 100
\]

O primeiro período comum recebe índice 100. Os demais valores mostram a evolução relativa em comparação com esse ponto inicial.

O código exige valor-base positivo. Séries cujo primeiro valor comum seja nulo ou negativo são ignoradas na normalização.

**Importante:** a base 100 permite comparar a evolução relativa de séries com escalas diferentes, mas não torna seus significados econômicos idênticos. Indicadores que já representam taxas ou variações percentuais exigem interpretação cuidadosa.

### 6.4. Correlação entre indicadores

O usuário seleciona exatamente dois indicadores.

As séries são convertidas para frequência mensal e alinhadas pelas datas em comum. O código exige pelo menos três observações mensais e verifica se as duas séries apresentam variação.

A correlação de Pearson é calculada com `pandas.Series.corr()`. O resultado varia entre -1 e +1:

- próximo de +1: associação linear positiva;
- próximo de -1: associação linear negativa;
- próximo de 0: associação linear fraca ou inexistente.

O programa também classifica a intensidade da correlação em muito fraca, fraca, moderada, forte ou muito forte, conforme o valor absoluto do coeficiente.

### 6.5. Regressão linear e pontos estimados

Para as duas séries selecionadas, o programa ajusta uma reta:

\[
Y = aX + b
\]

O ajuste é realizado com `numpy.polyfit(x, y, 1)`, que retorna o coeficiente angular e o intercepto.

O código calcula também o R-quadrado como o quadrado da correlação de Pearson, no contexto da regressão linear simples com intercepto.

Em vez de gerar um gráfico, o programa apresenta uma tabela com:

- mês de referência;
- valor observado de X;
- valor observado de Y;
- valor estimado de Y pela reta.

Esses dados representam os pontos que poderiam ser utilizados posteriormente em um gráfico de dispersão com linha de tendência.

**Limitação estatística:** correlação e regressão não demonstram causalidade. Séries econômicas que apresentam tendência ao longo do tempo podem produzir correlações elevadas sem que exista uma relação causal entre elas. Os resultados devem ser interpretados considerando o contexto dos indicadores.

## 7. Tratamento de erros e consistência

O código contempla:

- timeout e falhas de conexão;
- respostas HTTP malsucedidas;
- formatos de resposta inesperados;
- valores e datas inválidos;
- registros fora do período selecionado;
- duplicidade de datas no IPEADATA;
- links de paginação repetidos;
- ausência de dados suficientes para comparação ou correlação;
- séries constantes, para as quais a correlação não é definida.

Os dados são convertidos para tipos numéricos e datas padronizadas antes dos cálculos.

## 8. Como executar

1. Instale Python 3.
2. Instale as dependências:

```powershell
python -m pip install requests pandas numpy
```

3. Abra o terminal na pasta `APIs Externas IV/API Indicadores Econômicos Brasileiros`.
4. Execute:

```powershell
python main.py
```

Menu principal:

```text
1 - Consultar todos os indicadores
2 - Comparar de 2 a 5 indicadores (base 100)
3 - Correlação entre 2 indicadores
4 - Atualizar dados das APIs
0 - Encerrar
```

A primeira consulta pode levar alguns segundos, pois os dados são obtidos diretamente das fontes externas. É necessária conexão com a internet.

## 9. Autoria

**Desenvolvimento e implementação do código: Miguel Soares de Sousa.**

A implementação contempla a integração com as APIs do Banco Central e do IPEADATA, a definição do catálogo de séries, consultas paralelas, tratamento e padronização das respostas, paginação, cache, alinhamento temporal, normalização base 100, cálculo de correlação de Pearson e regressão linear.

O Banco Central do Brasil e o IPEADATA são provedores externos das séries econômicas. A autoria do código responsável pela consulta, organização e análise dos dados é do desenvolvedor identificado acima.

## 10. Referências

- Banco Central do Brasil — Dados Abertos: https://dadosabertos.bcb.gov.br/
- API do Banco Central — SGS: https://api.bcb.gov.br/
- IPEADATA: http://www.ipeadata.gov.br/
- Requests: https://requests.readthedocs.io/
- Pandas: https://pandas.pydata.org/docs/
- NumPy: https://numpy.org/doc/
- Python: https://docs.python.org/3/
