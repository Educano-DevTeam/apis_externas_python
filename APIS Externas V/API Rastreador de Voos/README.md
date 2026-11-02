# Documentação Técnica — API Rastreador de Voos

## 1. Objetivo

O projeto **API Rastreador de Voos** é um programa de integração de dados desenvolvido em Python. Seu objetivo é consultar informações de tráfego aéreo disponibilizadas pela OpenSky Network, tratar as respostas recebidas e apresentar os registros no terminal, com opção de exportação para CSV.

O programa não possui interface gráfica nem mapa. Seu foco é a comunicação com a API, o processamento dos dados e a disponibilização das informações em formato tabular.

## 2. Tecnologias e bibliotecas

- **Python 3:** implementação da aplicação.
- **Requests:** comunicação HTTP com os endpoints da OpenSky e com o serviço de autenticação.
- **Pandas:** organização dos registros em DataFrames, ordenação, apresentação tabular e exportação CSV.
- **Datetime:** conversão de timestamps Unix e manipulação de intervalos de tempo.
- **OS e Time:** bibliotecas padrão utilizadas para caminhos de arquivos, leitura de variáveis de ambiente e controle de tempo/expiração do token.

Instalação das dependências:

```bash
python -m pip install requests pandas
```

## 3. API utilizada: OpenSky Network

A OpenSky Network disponibiliza dados de vigilância aérea coletados por sua rede de receptores. O projeto utiliza a API REST da plataforma.

- Portal: https://opensky-network.org/
- Documentação: https://openskynetwork.github.io/opensky-api/
- Endpoints utilizados: `states/all`, `tracks/all`, `flights/arrival` e `flights/departure`.

### 3.1. Obtenção das credenciais

O fluxo implementado utiliza autenticação OAuth2 no modo `client_credentials`.

1. Acesse https://opensky-network.org/.
2. Crie uma conta ou entre na sua conta existente.
3. Consulte a área de gerenciamento de aplicações/credenciais e crie as credenciais de cliente disponibilizadas pela plataforma.
4. Guarde o `Client ID` e o `Client Secret` em local seguro.
5. Configure os dois valores como variáveis de ambiente antes de executar o programa.

A disponibilidade de cadastro e as regras de acesso podem mudar conforme as políticas da OpenSky. Consulte a documentação oficial caso a área de credenciais tenha mudado.

### 3.2. Configuração segura das credenciais

**Atenção à configuração do código:** na versão consultada do repositório, as credenciais aparecem como valores atribuídos às constantes `CLIENT_ID` e `CLIENT_SECRET`. Para que as variáveis de ambiente dos exemplos abaixo sejam utilizadas, substitua essas atribuições no início do `main.py` por:

```python
CLIENT_ID = os.getenv("OPENSKY_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET", "")
```

O módulo `os` já é importado pelo script. Essa alteração evita manter o segredo diretamente no código-fonte. Se você já fez essa alteração na sua versão local, não é necessário repeti-la.

No PowerShell, configure as variáveis para a sessão atual:

```powershell
$env:OPENSKY_CLIENT_ID="seu_client_id"
$env:OPENSKY_CLIENT_SECRET="seu_client_secret"
```

Depois, execute o programa na mesma janela do terminal. Não compartilhe os valores nem os envie ao GitHub.

O programa solicita um token OAuth2 ao endpoint de autenticação da OpenSky e reutiliza o token enquanto ele estiver válido. Quando uma consulta retorna HTTP 401, o programa tenta renovar o token uma vez.

## 4. Funcionamento geral

O fluxo de execução é:

1. O usuário inicia o programa pelo terminal.
2. O menu principal apresenta as funcionalidades disponíveis.
3. Quando necessário, o programa obtém um token de acesso OAuth2.
4. O script realiza uma requisição HTTP ao endpoint correspondente.
5. A resposta JSON é validada e transformada em registros organizados.
6. Os dados são apresentados no terminal.
7. Nas consultas tabulares, o usuário pode optar por salvar o resultado em CSV.

## 5. Funcionalidades implementadas

### 5.1. Aeronaves sobre a região do Brasil

Utiliza o endpoint `states/all` com uma bounding box aproximada do Brasil continental:

- Latitude mínima: `-34.0`
- Longitude mínima: `-74.0`
- Latitude máxima: `5.5`
- Longitude máxima: `-34.0`

A consulta solicita informações estendidas para obter a categoria da aeronave. O programa filtra registros sem coordenadas válidas e mantém somente estados identificados como aeronaves no ar.

Os campos organizados incluem:

- Código ICAO24 da aeronave;
- identificação/callsign;
- país de origem;
- latitude e longitude;
- altitude;
- velocidade convertida de m/s para km/h;
- direção;
- razão vertical de subida ou descida;
- horário do último contato em UTC;
- código e descrição da categoria.

O usuário pode selecionar todas as categorias, helicópteros/aeronaves de asas rotativas, aeronaves grandes/pesadas/de alta performance, categoria desconhecida, categoria sem informação ou um código específico.

**Observação:** a bounding box é uma área retangular aproximada. Ela também abrange áreas marítimas e partes de países vizinhos; portanto, não representa exatamente as fronteiras geográficas brasileiras.

### 5.2. Trajetória por ICAO24

Utiliza o endpoint `tracks/all`.

O usuário informa o código ICAO24, composto por seis caracteres hexadecimais, e escolhe:

- trajetória ao vivo, quando houver voo ativo;
- trajetória próxima de um horário nas últimas 24 horas.

Os pontos retornados são ordenados cronologicamente e organizados com horário UTC, latitude, longitude, altitude, direção e indicação de estado no solo.

A OpenSky retorna waypoints selecionados da trajetória, e não necessariamente todas as posições registradas pelo sistema.

### 5.3. Chegadas e partidas por aeroporto

Utiliza os endpoints:

- `flights/arrival` para chegadas;
- `flights/departure` para partidas.

O usuário informa o código ICAO do aeroporto (por exemplo, `SBGR`) e escolhe o tipo de consulta. O programa calcula um intervalo histórico compatível com as regras adotadas no código e organiza:

- ICAO24;
- identificação/callsign;
- aeroporto estimado de partida;
- aeroporto estimado de chegada;
- horário estimado de partida;
- horário estimado de chegada.

Esses registros são dados históricos processados pela OpenSky, não uma programação oficial de voos comerciais.

## 6. Tratamento de erros e limites

O código trata, entre outras situações:

- **HTTP 400:** parâmetros inválidos ou intervalo não aceito;
- **HTTP 401:** token inválido ou expirado, com tentativa de renovação;
- **HTTP 403:** acesso não permitido;
- **HTTP 404:** ausência de registros para a consulta;
- **HTTP 429:** limite de requisições atingido;
- timeout, falhas de conexão e respostas JSON inválidas.

A API pode impor limites de uso e de disponibilidade histórica. Uma consulta sem resultados não significa necessariamente erro no código: pode não haver dados para o período, aeronave ou aeroporto informado.

## 7. Exportação dos resultados

Ao apresentar uma tabela, o programa pergunta se o usuário deseja salvar os dados em CSV. Os arquivos são gravados no diretório de execução, com nomes como:

- `aeronaves_brasil.csv`
- `trajetoria_<icao24>.csv`
- `voos_<aeroporto>_chegadas.csv`
- `voos_<aeroporto>_partidas.csv`

A codificação `utf-8-sig` é utilizada para facilitar a abertura dos arquivos em planilhas, inclusive no Excel.

## 8. Como executar

1. Instale Python 3.
2. Instale as dependências:

```powershell
python -m pip install requests pandas
```

3. Configure `OPENSKY_CLIENT_ID` e `OPENSKY_CLIENT_SECRET` como variáveis de ambiente.
4. Abra o terminal na pasta `APIS Externas V/API Rastreador de Voos`.
5. Execute:

```powershell
python main.py
```

No menu:

```text
1 - Aeronaves sobre a região do Brasil
2 - Trajetória de uma aeronave por ICAO24
3 - Chegadas e partidas históricas por aeroporto
0 - Encerrar
```

## 9. Autoria

**Desenvolvimento e implementação do código: Miguel Soares de Sousa.**

A implementação contempla a autenticação, integração HTTP com a OpenSky Network, tratamento de respostas e erros, filtros por categoria, consulta de trajetórias, consulta de chegadas e partidas, formatação dos registros e exportação CSV.

A OpenSky Network é a provedora externa dos dados de tráfego aéreo; a autoria do código de integração e processamento é do desenvolvedor identificado acima.

## 10. Referências

- OpenSky Network: https://opensky-network.org/
- Documentação REST da OpenSky: https://openskynetwork.github.io/opensky-api/
- Requests: https://requests.readthedocs.io/
- Pandas: https://pandas.pydata.org/docs/
- Python: https://docs.python.org/3/
