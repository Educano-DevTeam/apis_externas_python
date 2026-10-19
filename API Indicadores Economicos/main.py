
import requests
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed


# ==========================================
# CONFIGURAÇÕES GERAIS
# ==========================================

DATA_INICIAL = date(2020, 1, 1)
DATA_FINAL = date.today()

URL_BCB = (
    "https://api.bcb.gov.br/dados/serie/"
    "bcdata.sgs.{codigo}/dados"
)

# Endpoint OData do IpeaData.
URL_IPEA = "https://www.ipeadata.gov.br/api/odata4"


# ==========================================
# CATÁLOGO DE INDICADORES
# ==========================================

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
        "nome": "Dólar comercial - venda",
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

# ==========================================
# CONSULTA AO BANCO CENTRAL
# ==========================================

def consultar_bcb(indicador):
    """Consulta uma série SGS e devolve seus dados."""

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
            timeout=30,
        )
        resposta.raise_for_status()

        dados = resposta.json()

        if not isinstance(dados, list):
            raise ValueError(
                f"Resposta inesperada da API: {dados}"
            )

        return {
            "indicador": indicador["nome"],
            "codigo": indicador["codigo"],
            "frequencia": indicador["frequencia"],
            "fonte": "BCB",
            "dados": dados,
            "erro": None,
        }

    except (requests.RequestException, ValueError) as erro:
        return {
            "indicador": indicador["nome"],
            "codigo": indicador["codigo"],
            "frequencia": indicador["frequencia"],
            "fonte": "BCB",
            "dados": [],
            "erro": str(erro),
        }


# ==========================================
# CONSULTA AO IPEADATA
# ==========================================


def consultar_ipea(indicador):
    """Consulta os valores históricos de uma série do IpeaData."""

    codigo = indicador["codigo"]

    url = (
        f"{URL_IPEA}/ValoresSerie"
        f"(SERCODIGO='{codigo}')"
    )

    try:
        resposta = requests.get(url, timeout=30)
        resposta.raise_for_status()

        resposta_json = resposta.json()

        # No OData, os registros ficam na propriedade "value".
        dados = resposta_json.get("value", [])

        if not isinstance(dados, list):
            raise ValueError(
                "Formato inesperado na resposta do IpeaData."
            )

        # Filtra o período configurado no início do programa.
        dados_filtrados = []

        for registro in dados:
            data_texto = registro.get("VALDATA")

            if not data_texto:
                continue

            # A data pode vir acompanhada de horário e fuso.
            data_iso = data_texto[:10]

            try:
                data_registro = date.fromisoformat(data_iso)
            except ValueError:
                continue

            if DATA_INICIAL <= data_registro <= DATA_FINAL:
                dados_filtrados.append({
                    "data": data_iso,
                    "valor": registro.get("VALVALOR"),
                })

        # Mantém a série em ordem cronológica.
        dados_filtrados.sort(key=lambda item: item["data"])

        return {
            "indicador": indicador["nome"],
            "codigo": codigo,
            "frequencia": indicador["frequencia"],
            "fonte": "IPEADATA",
            "dados": dados_filtrados,
            "erro": None,
        }

    except (requests.RequestException, ValueError) as erro:
        return {
            "indicador": indicador["nome"],
            "codigo": codigo,
            "frequencia": indicador["frequencia"],
            "fonte": "IPEADATA",
            "dados": [],
            "erro": str(erro),
        }
        
        
# ==========================================
# CONSULTA SIMULTÂNEA
# ==========================================

def consultar_indicadores():
    dados_bcb = []
    dados_ipea = []

    tarefas = []

    with ThreadPoolExecutor(max_workers=5) as executor:

        # Agenda as consultas do Banco Central.
        for indicador in INDICADORES_BCB:
            tarefa = executor.submit(
                consultar_bcb,
                indicador
            )
            tarefas.append(("BCB", tarefa))

        # Agenda as consultas do IpeaData.
        for indicador in INDICADORES_IPEA:
            tarefa = executor.submit(
                consultar_ipea,
                indicador
            )
            tarefas.append(("IPEADATA", tarefa))

        # Separa os resultados por fonte.
        for fonte, tarefa in tarefas:
            resultado = tarefa.result()

            if fonte == "BCB":
                dados_bcb.append(resultado)
            else:
                dados_ipea.append(resultado)

    return dados_bcb, dados_ipea


# ==========================================
# EXECUÇÃO
# ==========================================

def exibir_resultados(titulo, indicadores):
    print(f"\n========== {titulo} ==========")

    for indicador in indicadores:
        print(f"\nIndicador: {indicador['indicador']}")
        print(f"Código: {indicador['codigo']}")
        print(f"Fonte: {indicador['fonte']}")

        if indicador["erro"]:
            print(f"Erro: {indicador['erro']}")
            continue

        dados = indicador["dados"]

        print(f"Registros recebidos: {len(dados)}")
        print("Últimos registros:")
        print(dados[-3:] if dados else "Nenhum registro encontrado.")



if __name__ == "__main__":
    dados_bcb, dados_ipea = consultar_indicadores()

    exibir_resultados("BANCO CENTRAL", dados_bcb)
    exibir_resultados("IPEADATA", dados_ipea)
