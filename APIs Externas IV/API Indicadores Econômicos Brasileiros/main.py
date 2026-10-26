
import requests
import pandas as pd
import numpy as np

from datetime import date, datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# CONFIGURACOES GERAIS
# ============================================================

DATA_INICIAL = date(2020, 1, 1)
DATA_FINAL = date.today()

URL_BCB = (
    "https://api.bcb.gov.br/dados/serie/"
    "bcdata.sgs.{codigo}/dados"
)

URL_IPEA = "https://www.ipeadata.gov.br/api/odata4"

TIMEOUT = 30

# Resultados sao armazenados para evitar consultas repetidas.
RESULTADOS_CACHE = None


# ============================================================
# CATALOGO DE INDICADORES
# ============================================================

INDICADORES_BCB = [
    {
        "nome": "Meta Selic",
        "codigo": 432,
        "frequencia": "diaria",
    },
    {
        "nome": "IPCA mensal",
        "codigo": 433,
        "frequencia": "mensal",
    },
    {
        "nome": "Dolar comercial - venda",
        "codigo": 1,
        "frequencia": "diaria",
    },
    {
        "nome": "IGP-M",
        "codigo": 189,
        "frequencia": "mensal",
    },
]

INDICADORES_IPEA = [
    {
        "nome": "IPCA mensal",
        "codigo": "PRECOS12_IPCAG12",
        "frequencia": "mensal",
    },
    {
        "nome": "CDI mensal",
        "codigo": "BM12_TJCDI12",
        "frequencia": "mensal",
    },
    {
        "nome": "IGP-M mensal",
        "codigo": "IGP12_IGPMG12",
        "frequencia": "mensal",
    },
]


# ============================================================
# UTILIDADES
# ============================================================

def criar_resultado(indicador, fonte, dados=None, erro=None):
    """Padroniza os resultados das duas APIs."""

    return {
        "indicador": indicador["nome"],
        "codigo": indicador["codigo"],
        "frequencia": indicador["frequencia"],
        "fonte": fonte,
        "dados": dados or [],
        "erro": erro,
    }


def nome_completo(indicador):
    """Identifica unicamente um indicador, inclusive series homonimas."""

    return (
        f"{indicador['indicador']} "
        f"[{indicador['fonte']} - {indicador['codigo']}]"
    )


def converter_data_ipea(valor):
    """Converte datas ISO ou timestamps OData."""

    if not valor:
        return None

    try:
        return date.fromisoformat(str(valor)[:10])
    except ValueError:
        pass

    try:
        texto = str(valor)
        inicio = texto.index("(") + 1
        fim = texto.index(")", inicio)

        milissegundos = int(texto[inicio:fim])

        return datetime.fromtimestamp(
            milissegundos / 1000,
            tz=timezone.utc,
        ).date()

    except (ValueError, IndexError, OSError, OverflowError):
        return None


def dentro_do_periodo(data_registro):
    """Verifica se a data esta no periodo selecionado."""

    return (
        data_registro is not None
        and DATA_INICIAL <= data_registro <= DATA_FINAL
    )


def ler_inteiro(mensagem, minimo, maximo):
    """Le um numero inteiro dentro do intervalo permitido."""

    try:
        valor = int(input(mensagem).strip())

        if not minimo <= valor <= maximo:
            print(f"Informe um numero entre {minimo} e {maximo}.")
            return None

        return valor

    except ValueError:
        print("Entrada invalida. Digite um numero inteiro.")
        return None


# ============================================================
# CONSULTA AO BANCO CENTRAL
# ============================================================

def consultar_bcb(indicador):
    """Consulta uma serie SGS do Banco Central."""

    url = URL_BCB.format(codigo=indicador["codigo"])

    parametros = {
        "formato": "json",
        "dataInicial": DATA_INICIAL.strftime("%d/%m/%Y"),
        "dataFinal": DATA_FINAL.strftime("%d/%m/%Y"),
    }

    try:
        resposta = requests.get(
            url,
            params=parametros,
            timeout=TIMEOUT,
        )
        resposta.raise_for_status()

        dados_originais = resposta.json()

        if not isinstance(dados_originais, list):
            raise ValueError(
                "Formato inesperado na resposta do Banco Central."
            )

        dados = []

        for registro in dados_originais:
            data_texto = registro.get("data")
            valor = registro.get("valor")

            if not data_texto or valor in (None, ""):
                continue

            try:
                data_registro = datetime.strptime(
                    data_texto, "%d/%m/%Y"
                ).date()

                valor_numerico = float(
                    str(valor).replace(",", ".")
                )

            except (ValueError, TypeError):
                continue

            if dentro_do_periodo(data_registro):
                dados.append({
                    "data": data_registro.isoformat(),
                    "valor": valor_numerico,
                })

        dados.sort(key=lambda item: item["data"])

        return criar_resultado(indicador, "BCB", dados)

    except (requests.RequestException, ValueError) as erro:
        return criar_resultado(
            indicador, "BCB", erro=str(erro)
        )


# ============================================================
# CONSULTA AO IPEADATA
# ============================================================

def consultar_ipea(indicador):
    """Consulta uma serie OData, incluindo paginas seguintes."""

    codigo = indicador["codigo"]

    url = (
        f"{URL_IPEA}/ValoresSerie"
        f"(SERCODIGO='{codigo}')"
    )

    dados_filtrados = []
    paginas_visitadas = set()

    try:
        while url:
            # Protege contra eventual ciclo de links de paginacao.
            if url in paginas_visitadas:
                raise ValueError(
                    "A API retornou um link de paginacao repetido."
                )

            paginas_visitadas.add(url)

            resposta = requests.get(
                url,
                timeout=TIMEOUT,
                headers={"Accept": "application/json"},
            )
            resposta.raise_for_status()

            resposta_json = resposta.json()

            if not isinstance(resposta_json, dict):
                raise ValueError(
                    "Formato inesperado na resposta do IpeaData."
                )

            registros = resposta_json.get("value", [])

            if not isinstance(registros, list):
                raise ValueError(
                    "A propriedade 'value' nao contem uma lista."
                )

            for registro in registros:
                data_registro = converter_data_ipea(
                    registro.get("VALDATA")
                )

                valor = registro.get("VALVALOR")

                if not dentro_do_periodo(data_registro):
                    continue

                if valor is None or valor == "":
                    continue

                try:
                    valor_numerico = float(
                        str(valor).replace(",", ".")
                    )
                except (ValueError, TypeError):
                    continue

                dados_filtrados.append({
                    "data": data_registro.isoformat(),
                    "valor": valor_numerico,
                })

            url = resposta_json.get("@odata.nextLink")

        # Evita datas duplicadas caso a API repita algum registro.
        unicos = {
            item["data"]: item
            for item in dados_filtrados
        }

        dados_filtrados = sorted(
            unicos.values(),
            key=lambda item: item["data"],
        )

        return criar_resultado(
            indicador, "IPEADATA", dados_filtrados
        )

    except (requests.RequestException, ValueError) as erro:
        return criar_resultado(
            indicador, "IPEADATA", erro=str(erro)
        )


# ============================================================
# CONSULTA SIMULTANEA E CACHE
# ============================================================

def consultar_indicadores():
    """Busca todos os indicadores em paralelo."""

    resultados = []
    tarefas = {}

    with ThreadPoolExecutor(max_workers=5) as executor:

        for indicador in INDICADORES_BCB:
            tarefa = executor.submit(consultar_bcb, indicador)
            tarefas[tarefa] = "BCB"

        for indicador in INDICADORES_IPEA:
            tarefa = executor.submit(consultar_ipea, indicador)
            tarefas[tarefa] = "IPEADATA"

        for tarefa in as_completed(tarefas):
            try:
                resultados.append(tarefa.result())

            except Exception as erro:
                print(
                    f"Falha inesperada em {tarefas[tarefa]}: {erro}"
                )

    ordem = {
        ("BCB", str(item["codigo"])): posicao
        for posicao, item in enumerate(INDICADORES_BCB)
    }

    deslocamento = len(INDICADORES_BCB)

    for posicao, item in enumerate(INDICADORES_IPEA):
        ordem[("IPEADATA", str(item["codigo"]))] = (
            deslocamento + posicao
        )

    resultados.sort(
        key=lambda item: ordem.get(
            (item["fonte"], str(item["codigo"])), 999
        )
    )

    return resultados


def obter_resultados():
    """Consulta as APIs na primeira utilizacao e reutiliza o cache."""

    global RESULTADOS_CACHE

    if RESULTADOS_CACHE is None:
        print("\nConsultando as APIs. Aguarde...")

        RESULTADOS_CACHE = consultar_indicadores()

        if not RESULTADOS_CACHE:
            print("Nenhum resultado foi recebido das APIs.")

    return RESULTADOS_CACHE


# ============================================================
# EXIBICAO GERAL
# ============================================================

def exibir_resultados(resultados):
    """Exibe os indicadores e seus registros mais recentes."""

    print("\n" + "=" * 65)
    print("       INDICADORES ECONOMICOS BRASILEIROS")
    print("=" * 65)

    print(
        f"Periodo: {DATA_INICIAL.strftime('%d/%m/%Y')} "
        f"ate {DATA_FINAL.strftime('%d/%m/%Y')}"
    )

    for indicador in resultados:
        print("\n" + "-" * 65)
        print(f"Indicador: {indicador['indicador']}")
        print(f"Codigo: {indicador['codigo']}")
        print(f"Fonte: {indicador['fonte']}")
        print(f"Frequencia: {indicador['frequencia']}")

        if indicador["erro"]:
            print(f"Erro: {indicador['erro']}")
            continue

        dados = indicador["dados"]

        print(f"Registros recebidos: {len(dados)}")

        if not dados:
            print("Nenhum registro encontrado no periodo.")
            continue

        print("Tres registros mais recentes:")

        for registro in dados[-3:]:
            data_formatada = datetime.strptime(
                registro["data"], "%Y-%m-%d"
            ).strftime("%d/%m/%Y")

            print(
                f"  Data: {data_formatada} | "
                f"Valor: {registro['valor']:.6f}"
            )


# ============================================================
# SELECAO DE INDICADORES
# ============================================================

def selecionar_indicadores(resultados, minimo, maximo):
    """Permite selecionar indicadores pelo numero apresentado."""

    disponiveis = [
        item for item in resultados
        if not item["erro"] and item["dados"]
    ]

    if len(disponiveis) < minimo:
        print(
            f"Sao necessarios pelo menos {minimo} indicadores "
            "com dados validos."
        )
        return None

    print("\nIndicadores disponiveis:")

    for indice, indicador in enumerate(disponiveis, start=1):
        print(
            f"{indice}. {nome_completo(indicador)} "
            f"| {len(indicador['dados'])} registros"
        )

    print(
        f"\nDigite de {minimo} a {maximo} numeros, "
        "separados por virgula."
    )

    entrada = input("Selecao: ").strip()

    try:
        indices = [
            int(parte.strip())
            for parte in entrada.split(",")
        ]
    except ValueError:
        print("Selecao invalida.")
        return None

    if not minimo <= len(indices) <= maximo:
        print(
            f"Selecione de {minimo} a {maximo} indicadores."
        )
        return None

    if len(set(indices)) != len(indices):
        print("Nao repita o mesmo indicador.")
        return None

    if any(indice < 1 or indice > len(disponiveis)
           for indice in indices):
        print("Um ou mais numeros estao fora da lista.")
        return None

    return [disponiveis[indice - 1] for indice in indices]


# ============================================================
# PREPARACAO E ALINHAMENTO DAS SERIES
# ============================================================

def preparar_serie_mensal(indicador):
    """
    Converte uma serie para frequencia mensal.

    Diaria: media dos valores de cada mes.
    Mensal: valor mensal disponivel.
    Trimestral/anual: mantem o ultimo valor conhecido ate
    a proxima observacao.

    A frequencia comum facilita comparacoes entre fontes.
    """

    dados = indicador["dados"]

    tabela = pd.DataFrame(dados)

    if tabela.empty:
        return pd.Series(dtype=float, name=nome_completo(indicador))

    tabela["data"] = pd.to_datetime(
        tabela["data"], errors="coerce"
    )

    tabela["valor"] = pd.to_numeric(
        tabela["valor"], errors="coerce"
    )

    tabela = tabela.dropna(subset=["data", "valor"])

    if tabela.empty:
        return pd.Series(dtype=float, name=nome_completo(indicador))

    tabela = tabela.sort_values("data")
    tabela = tabela.drop_duplicates(
        subset=["data"], keep="last"
    )

    tabela = tabela.set_index("data")

    serie = tabela["valor"].resample("MS").mean()

    frequencia = indicador["frequencia"].lower()

    if frequencia in ("trimestral", "anual"):
        # Expande observacoes menos frequentes para meses.
        indice_mensal = pd.date_range(
            start=serie.index.min(),
            end=serie.index.max(),
            freq="MS",
        )

        serie = serie.reindex(indice_mensal).ffill()

    serie.name = nome_completo(indicador)

    return serie


def alinhar_series(indicadores):
    """Combina series pela data mensal em comum."""

    series = [
        preparar_serie_mensal(indicador)
        for indicador in indicadores
    ]

    tabela = pd.concat(series, axis=1, join="inner")
    tabela = tabela.sort_index()
    tabela = tabela.dropna()

    return tabela


# ============================================================
# DESAFIO 1 - COMPARACAO NORMALIZADA
# ============================================================

def comparar_indicadores(resultados):
    """Compara ate cinco indicadores com base inicial 100."""

    selecionados = selecionar_indicadores(
        resultados, minimo=2, maximo=5
    )

    if not selecionados:
        return

    tabela_original = alinhar_series(selecionados)

    if tabela_original.empty:
        print(
            "Nao ha datas em comum entre as series selecionadas."
        )
        return

    if len(tabela_original) < 2:
        print(
            "Sao necessarios pelo menos dois periodos mensais "
            "em comum para comparar tendencias."
        )
        return

    print("\n" + "=" * 65)
    print("COMPARACAO DE INDICADORES - BASE 100")
    print("=" * 65)

    print(
        f"Periodos mensais em comum: {len(tabela_original)}"
    )

    print(
        "A comparacao utiliza a media mensal para series diarias "
        "e o ultimo valor conhecido para series trimestrais/anuais."
    )

    # Cada serie comeca em 100 na primeira data comum.
    tabela_normalizada = pd.DataFrame(index=tabela_original.index)
    indicadores_validos = []

    for indicador in selecionados:
        nome = nome_completo(indicador)
        valores = tabela_original[nome]

        valor_base = valores.iloc[0]

        # O indice base 100 exige valor inicial positivo.
        if pd.isna(valor_base) or valor_base <= 0:
            print(
                f"\nSerie ignorada: {nome}. "
                "O primeiro valor comum precisa ser positivo "
                "para normalizacao em base 100."
            )
            continue

        tabela_normalizada[nome] = (
            valores / valor_base
        ) * 100

        indicadores_validos.append(nome)

    if len(indicadores_validos) < 2:
        print(
            "\nNao foi possivel comparar pelo menos duas series "
            "com valores-base positivos."
        )
        return

    tabela_normalizada = tabela_normalizada[
        indicadores_validos
    ]

    print("\nResumo da variacao no periodo:")

    for nome in indicadores_validos:
        valores = tabela_normalizada[nome]

        primeiro = valores.iloc[0]
        ultimo = valores.iloc[-1]
        variacao = ultimo - primeiro

        print(f"\nIndicador: {nome}")
        print(f"Indice inicial: {primeiro:.4f}")
        print(f"Indice final: {ultimo:.4f}")
        print(f"Variacao do indice: {variacao:+.4f} pontos")

        print(
            f"Variacao relativa ao valor-base: "
            f"{((ultimo / primeiro) - 1) * 100:+.2f}%"
        )

    print("\nSerie normalizada por mes:")
    print(tabela_normalizada.round(4).to_string())

    print(
        "\nInterpretacao: base 100 significa que cada serie "
        "foi comparada com seu proprio valor inicial comum."
    )

    print(
        "Atencao: indicadores que ja representam taxas ou "
        "variacoes percentuais podem exigir interpretacao "
        "diferente de indices de nivel de preco."
    )


# ============================================================
# DESAFIO 2 - CORRELACAO E REGRESSAO LINEAR
# ============================================================

def classificar_correlacao(correlacao):
    """Descreve a intensidade e o sentido da correlacao."""

    intensidade = abs(correlacao)

    if intensidade < 0.20:
        grau = "muito fraca"
    elif intensidade < 0.40:
        grau = "fraca"
    elif intensidade < 0.60:
        grau = "moderada"
    elif intensidade < 0.80:
        grau = "forte"
    else:
        grau = "muito forte"

    sentido = (
        "positiva" if correlacao > 0
        else "negativa" if correlacao < 0
        else "nula"
    )

    return f"{grau} e {sentido}"


def calcular_correlacao(resultados):
    """Calcula Pearson e a reta de tendencia entre duas series."""

    selecionados = selecionar_indicadores(
        resultados, minimo=2, maximo=2
    )

    if not selecionados:
        return

    tabela = alinhar_series(selecionados)

    if tabela.empty or len(tabela) < 3:
        print(
            "Sao necessarios pelo menos tres periodos mensais "
            "em comum para calcular a correlacao."
        )
        return

    nome_x = nome_completo(selecionados[0])
    nome_y = nome_completo(selecionados[1])

    x = tabela[nome_x].astype(float)
    y = tabela[nome_y].astype(float)

    # Pearson nao e definido se uma serie for constante.
    if x.nunique() < 2 or y.nunique() < 2:
        print(
            "Nao e possivel calcular a correlacao: "
            "uma das series nao apresenta variacao."
        )
        return

    correlacao = x.corr(y)

    if pd.isna(correlacao):
        print("Nao foi possivel calcular a correlacao.")
        return

    # Regressao linear: y = coeficiente * x + intercepto.
    coeficiente, intercepto = np.polyfit(
        x.to_numpy(),
        y.to_numpy(),
        1,
    )

    valores_estimados = (
        coeficiente * x + intercepto
    )

    # R-quadrado da regressao linear simples.
    r_quadrado = correlacao ** 2

    print("\n" + "=" * 65)
    print("ANALISE DE CORRELACAO")
    print("=" * 65)

    print(f"Variavel X: {nome_x}")
    print(f"Variavel Y: {nome_y}")
    print(f"Observacoes mensais alinhadas: {len(tabela)}")

    print(f"\nCorrelacao de Pearson: {correlacao:.4f}")
    print(
        "Classificacao: "
        f"{classificar_correlacao(correlacao)}"
    )

    print(f"Coeficiente angular: {coeficiente:.6f}")
    print(f"Intercepto: {intercepto:.6f}")
    print(
        f"Equacao da tendencia: Y = "
        f"{coeficiente:.6f} * X + {intercepto:.6f}"
    )
    print(f"R-quadrado: {r_quadrado:.4f}")

    print(
        "\nPontos para dispersao e linha de tendencia "
        "(sem gerar grafico):"
    )

    tabela_pontos = pd.DataFrame({
        "Data": tabela.index.strftime("%Y-%m"),
        "X": x.values,
        "Y": y.values,
        "Y_estimado": valores_estimados.values,
    })

    print(tabela_pontos.round(6).to_string(index=False))

    print(
        "\nInterpretacao: a correlacao mede associacao linear, "
        "nao causalidade. A reta estima a relacao linear entre "
        "as duas variaveis na amostra selecionada."
    )


# ============================================================
# MENU PRINCIPAL
# ============================================================

def menu():
    while True:
        print("\n" + "=" * 55)
        print("INDICADORES ECONOMICOS - BCB + IPEADATA")
        print("=" * 55)

        print("1 - Consultar todos os indicadores")
        print("2 - Comparar de 2 a 5 indicadores (base 100)")
        print("3 - Correlacao entre 2 indicadores")
        print("4 - Atualizar dados das APIs")
        print("0 - Encerrar")

        opcao = input("\nEscolha uma opcao: ").strip()

        if opcao == "1":
            resultados = obter_resultados()
            exibir_resultados(resultados)

        elif opcao == "2":
            resultados = obter_resultados()
            comparar_indicadores(resultados)

        elif opcao == "3":
            resultados = obter_resultados()
            calcular_correlacao(resultados)

        elif opcao == "4":
            global RESULTADOS_CACHE
            RESULTADOS_CACHE = None
            print("Cache limpo. Os dados serao consultados novamente.")

        elif opcao == "0":
            print("Programa encerrado.")
            break

        else:
            print("Opcao invalida. Tente novamente.")


if __name__ == "__main__":
    try:
        menu()

    except KeyboardInterrupt:
        print("\nPrograma interrompido pelo usuario.")
