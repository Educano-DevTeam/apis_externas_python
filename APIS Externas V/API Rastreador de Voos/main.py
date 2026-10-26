import os
import time
import requests
import pandas as pd

from datetime import datetime, timezone, timedelta


# ============================================================
# CONFIGURACAO
# ============================================================


BASE_URL = "https://opensky-network.org/api"
TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/"
    "protocol/openid-connect/token"
)

# Credenciais da OpenSky Network
CLIENT_ID = "michael27-api-client"
CLIENT_SECRET = "WdSrRKYHvIP5EcmJsgvgjH8Qp6LJUKG3"

BRASIL = {
    "lamin": -34.0,
    "lomin": -74.0,
    "lamax": 5.5,
    "lomax": -34.0
}

# Categorias conforme a documentacao atual da OpenSky.
CATEGORIAS = {
    0: "Desconhecida",
    1: "Sem categoria ADS-B",
    2: "Leve",
    3: "Pequena",
    4: "Grande",
    5: "Grande - alta esteira de vortices",
    6: "Pesada",
    7: "Alta performance",
    8: "Asas rotativas",
    9: "Planador",
    10: "Mais leve que o ar",
    11: "Paraquedista",
    12: "Ultraleve / parapente",
    13: "Reservada",
    14: "Drone / UAV",
    15: "Espacial",
    16: "Veiculo de emergencia",
    17: "Veiculo de servico",
    18: "Obstaculo pontual",
    19: "Obstaculo agrupado",
    20: "Obstaculo linear"
}

sessao = requests.Session()
token_acesso = None
token_expira_em = 0


# ============================================================
# AUTENTICACAO
# ============================================================

def obter_token(forcar_renovacao=False):
    """Obtem e reutiliza um token OAuth2 da OpenSky."""
    global token_acesso, token_expira_em

    if not CLIENT_ID or not CLIENT_SECRET:
        print(
            "Credenciais ausentes. Confira o arquivo .env e "
            "as variaveis OPENSKY_CLIENT_ID e OPENSKY_CLIENT_SECRET."
        )
        return None

    if (
        not forcar_renovacao
        and token_acesso
        and time.time() < token_expira_em - 60
    ):
        return token_acesso

    try:
        resposta = sessao.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            },
            timeout=30
        )
        resposta.raise_for_status()

        dados = resposta.json()
        token_acesso = dados["access_token"]
        duracao = int(dados.get("expires_in", 1800))
        token_expira_em = time.time() + duracao

        print("Autenticacao OpenSky realizada com sucesso.")
        return token_acesso

    except requests.exceptions.HTTPError as erro:
        print(f"Erro HTTP na autenticacao: {erro}")
        if erro.response is not None:
            print("Resposta:", erro.response.text[:300])
    except requests.exceptions.RequestException as erro:
        print(f"Falha de conexao na autenticacao: {erro}")
    except (ValueError, KeyError):
        print("A resposta de autenticacao nao continha um token valido.")

    return None


# ============================================================
# REQUISICOES HTTP
# ============================================================

def consultar_api(endpoint, parametros=None):
    """Consulta a API com autenticacao e tratamento de erros."""
    token = obter_token()

    if not token:
        return None

    for tentativa in range(2):
        try:
            resposta = sessao.get(
                f"{BASE_URL}/{endpoint}",
                params=parametros,
                headers={"Authorization": f"Bearer {token}"},
                timeout=40
            )

            if resposta.status_code == 401 and tentativa == 0:
                token = obter_token(forcar_renovacao=True)
                if not token:
                    return None
                continue

            if resposta.status_code == 404:
                # Alguns endpoints usam 404 quando nao ha resultados.
                print("A API nao encontrou registros para essa consulta.")
                return []

            if resposta.status_code == 400:
                print("Parametros rejeitados pela API (HTTP 400).")
                print("Confira o intervalo de datas e os parametros.")
                print("Detalhe:", resposta.text[:300])
                return None

            if resposta.status_code == 403:
                print("Acesso negado (HTTP 403). Confira as permissoes.")
                print("Detalhe:", resposta.text[:300])
                return None

            if resposta.status_code == 429:
                espera = resposta.headers.get(
                    "X-Rate-Limit-Retry-After-Seconds",
                    "nao informado"
                )
                print(
                    "Limite de requisicoes atingido. "
                    f"Tempo indicado para aguardar: {espera} segundos."
                )
                return None

            resposta.raise_for_status()
            return resposta.json()

        except requests.exceptions.Timeout:
            print("Tempo limite excedido na consulta.")
            return None
        except requests.exceptions.ConnectionError:
            print("Nao foi possivel conectar a OpenSky.")
            return None
        except requests.exceptions.HTTPError as erro:
            print(f"Erro HTTP: {erro}")
            return None
        except requests.exceptions.RequestException as erro:
            print(f"Erro na requisicao: {erro}")
            return None
        except ValueError:
            print("A API retornou uma resposta JSON invalida.")
            return None

    print("Nao foi possivel concluir a consulta apos renovar o token.")
    return None


# ============================================================
# FORMATACAO E UTILIDADES
# ============================================================

def formatar_horario(timestamp):
    """Converte timestamp Unix para horario UTC."""
    if timestamp is None:
        return "N/I"

    try:
        return datetime.fromtimestamp(
            float(timestamp), tz=timezone.utc
        ).strftime("%d/%m/%Y %H:%M:%S UTC")
    except (ValueError, TypeError, OSError, OverflowError):
        return "N/I"


def numero(valor, casas=2):
    """Formata numeros sem quebrar quando o valor e nulo."""
    if valor is None:
        return None

    try:
        if pd.isna(valor):
            return None
        return round(float(valor), casas)
    except (ValueError, TypeError):
        return None


def ler_numero(mensagem, minimo, maximo):
    """Solicita um numero dentro de um intervalo."""
    try:
        valor = float(input(mensagem).strip())
        if not minimo <= valor <= maximo:
            print(f"Informe um valor entre {minimo} e {maximo}.")
            return None
        return valor
    except ValueError:
        print("Valor invalido.")
        return None


def exibir_tabela(tabela, nome_arquivo=None):
    """Exibe uma tabela no terminal e permite salvar em CSV."""
    if tabela is None or tabela.empty:
        print("Nenhum registro para exibir.")
        return

    print(f"\nTotal de registros: {len(tabela)}")
    print(tabela.to_string(index=False, na_rep="N/I"))

    salvar = input("\nSalvar resultado em CSV? (s/n): ").strip().lower()

    if salvar == "s":
        if not nome_arquivo:
            nome_arquivo = "resultado_opensky.csv"

        try:
            tabela.to_csv(
                nome_arquivo,
                index=False,
                encoding="utf-8-sig"
            )
            print(f"Arquivo salvo: {os.path.abspath(nome_arquivo)}")
        except OSError as erro:
            print(f"Nao foi possivel salvar o CSV: {erro}")


# ============================================================
# 1. AERONAVES EM TEMPO REAL
# ============================================================

def consultar_voos_brasil():
    """Consulta aeronaves na bounding box e filtra por categoria."""
    print("\nConsultando aeronaves na regiao do Brasil...")

    instante_consulta = datetime.now(timezone.utc)

    print(
        "Consulta realizada em:",
        instante_consulta.strftime("%d/%m/%Y %H:%M:%S UTC")
    )
    print("Região: bounding box aproximada do Brasil continental")

    dados = consultar_api(
        "states/all",
        {**BRASIL, "extended": 1}
    )

    if dados is None:
        return

    estados = dados.get("states") or []

    if not estados:
        print("A OpenSky nao retornou aeronaves nessa regiao.")
        return

    registros = []

    for estado in estados:
        # Indices oficiais do state vector:
        # 0 ICAO24, 1 callsign, 2 pais, 3 posicao em timestamp,
        # 4 ultimo contato, 5 longitude, 6 latitude, 7 altitude,
        # 8 no solo, 9 velocidade m/s, 10 direcao,
        # 11 razao vertical, 16 fonte, 17 categoria.
        if len(estado) < 17:
            continue

        latitude = estado[6]
        longitude = estado[5]
        no_solo = estado[8]

        if latitude is None or longitude is None:
            continue

        # None significa estado no solo desconhecido.
        if no_solo is not False:
            continue

        categoria = estado[17] if len(estado) > 17 else None

        registros.append({
            "ICAO24": estado[0],
            "Identificacao": (estado[1] or "").strip() or "N/I",
            "Pais_origem": estado[2] or "N/I",
            "Latitude": numero(latitude, 5),
            "Longitude": numero(longitude, 5),
            "Altitude_m": numero(estado[7]),
            "Velocidade_kmh": numero(
                estado[9] * 3.6 if estado[9] is not None else None
            ),
            "Direcao_graus": numero(estado[10]),
            "Subida_descida_ms": numero(estado[11]),
            "Ultimo_contato_UTC": formatar_horario(estado[4]),
            "Categoria_codigo": categoria,
            "Categoria": CATEGORIAS.get(
                categoria, "Sem informacao"
            )
        })

    if not registros:
        print(
            "A API retornou estados, mas nenhum registro passou "
            "pelos filtros de posicao conhecida e estado no ar."
        )
        return

    tabela = pd.DataFrame(registros)

    print("\n========== FILTROS DE AERONAVES ==========")
    print("A - Todas as categorias")
    print("H - Helicópteros e outras aeronaves de asas rotativas")
    print("G - Aeronaves grandes, pesadas ou de alta performance")
    print("D - Categoria desconhecida (código 0)")
    print("N - Categoria sem informação (nula)")
    print("Ou informe um código de categoria de 1 a 20.")

    opcao = input("Filtro: ").strip().upper()

    if opcao == "A":
        pass

    elif opcao == "H":
        tabela = tabela[tabela["Categoria_codigo"] == 8]

    elif opcao == "G":
        tabela = tabela[
            tabela["Categoria_codigo"].isin([4, 5, 6, 7])
        ]

    elif opcao == "D":
        tabela = tabela[tabela["Categoria_codigo"] == 0]

    elif opcao == "N":
        tabela = tabela[tabela["Categoria_codigo"].isna()]

    else:
        try:
            codigo = int(opcao)

            if codigo not in CATEGORIAS or codigo == 0:
                print("Categoria inválida. Exibindo todas.")
            else:
                tabela = tabela[
                    tabela["Categoria_codigo"] == codigo
                ]

        except ValueError:
            print("Filtro inválido. Exibindo todas.")

    if tabela.empty:
        print(
            "Nenhuma aeronave corresponde ao filtro neste momento. "
            "Tente outra categoria."
        )
        return

    if tabela.empty:
        print(
            "Nenhuma aeronave corresponde a esse filtro neste momento. "
            "Isso nao significa que a consulta falhou."
        )
        return

    tabela = tabela.sort_values(
        by="Identificacao", na_position="last"
    ).reset_index(drop=True)

    print("\n========== AERONAVES DETECTADAS ==========")
    print(
        "Aviso: a bounding box inclui partes de paises vizinhos "
        "e areas maritimas."
    )

    exibir_tabela(tabela, "aeronaves_brasil.csv")


# ============================================================
# 2. TRAJETORIA POR ICAO24
# ============================================================

def consultar_trajetoria():
    """Consulta a trajetoria ao vivo ou proxima de um horario."""
    icao24 = input(
        "\nInforme o ICAO24 (6 caracteres hexadecimais): "
    ).strip().lower()

    if (
        len(icao24) != 6
        or any(c not in "0123456789abcdef" for c in icao24)
    ):
        print("ICAO24 invalido. Exemplo de formato: 3c4b26.")
        return

    print("\n1 - Trajetoria ao vivo (se houver voo ativo)")
    print("2 - Trajetoria proxima de um horario nas ultimas 24 horas")
    modo = input("Escolha: ").strip()

    if modo == "1":
        timestamp = 0
    elif modo == "2":
        horas = ler_numero(
            "Quantas horas atras? (0 a 24): ", 0, 24
        )
        if horas is None:
            return

        timestamp = int(
            (datetime.now(timezone.utc) -
             timedelta(hours=horas)).timestamp()
        )
    else:
        print("Opcao invalida.")
        return

    dados = consultar_api(
        "tracks/all",
        {"icao24": icao24, "time": timestamp}
    )

    if not dados:
        print(
            "Nenhuma trajetoria foi encontrada. Tente outro ICAO24 "
            "ou outro horario. O voo precisa estar registrado pela API."
        )
        return

    pontos = dados.get("path") or []

    # Organiza os pontos do mais antigo para o mais recente.
    pontos = sorted(
        pontos,
        key=lambda ponto: (
            ponto[0] if ponto[0] is not None else 0
        )
    )

    print(f"Quantidade de pontos recebidos: {len(pontos)}")

    if not pontos:
        print("A resposta nao possui pontos de trajetoria.")
        return

    registros = []

    for ponto in pontos:
        if len(ponto) < 6:
            continue

        registros.append({
            "Horario_UTC": formatar_horario(ponto[0]),
            "Latitude": numero(ponto[1], 6),
            "Longitude": numero(ponto[2], 6),
            "Altitude_m": numero(ponto[3]),
            "Direcao_graus": numero(ponto[4]),
            "No_solo": ponto[5]
        })

    tabela = pd.DataFrame(registros)

    if tabela.empty:
        print("Nao ha pontos validos para exibir.")
        return

    print("\n========== TRAJETORIA ==========")
    print(f"ICAO24: {dados.get('icao24', icao24)}")
    print(
        "Identificacao: "
        f"{(dados.get('callsign') or '').strip() or 'N/I'}"
    )
    print(f"Inicio: {formatar_horario(dados.get('startTime'))}")
    print(f"Fim: {formatar_horario(dados.get('endTime'))}")
    print(
        "Observacao: os pontos sao waypoints selecionados pela OpenSky, "
        "nao necessariamente cada posicao registrada."
    )

    exibir_tabela(tabela, f"trajetoria_{icao24}.csv")


# ============================================================
# 3. CHEGADAS E PARTIDAS
# ============================================================

def consultar_chegadas_partidas():
    """Consulta voos historicos de chegada ou partida por aeroporto."""
    aeroporto = input(
        "\nCodigo ICAO do aeroporto (ex.: SBGR): "
    ).strip().upper()

    if (
        len(aeroporto) != 4
        or not aeroporto.isalnum()
    ):
        print("Codigo ICAO invalido. Exemplo: SBGR.")
        return

    print("\n1 - Chegadas")
    print("2 - Partidas")
    tipo = input("Escolha: ").strip()

    if tipo not in ("1", "2"):
        print("Opcao invalida.")
        return

    # A API disponibiliza chegadas e partidas processadas.
    # Para evitar pedir dados do futuro ou do periodo atual,
    # usamos um intervalo de dois dias encerrado ha 1 dia.
    
    agora = datetime.now(timezone.utc)

    # Os endpoints históricos não garantem dados do dia atual.
    fim_dt = agora - timedelta(days=1)

    if tipo == "1":
        # Chegadas: intervalo de até 2 dias.
        duracao_dias = 2
    else:
        # Partidas: a documentação exige mais de 2 dias UTC.
        duracao_dias = 3

    inicio_dt = fim_dt - timedelta(days=duracao_dias)

    inicio = int(inicio_dt.timestamp())
    fim = int(fim_dt.timestamp())


    endpoint = (
        "flights/arrival" if tipo == "1"
        else "flights/departure"
    )

    print(
        f"\nIntervalo UTC: {formatar_horario(inicio)} "
        f"ate {formatar_horario(fim)}"
    )
    print("Consultando voos processados para o aeroporto...")

    dados = consultar_api(
        endpoint,
        {
            "airport": aeroporto,
            "begin": inicio,
            "end": fim
        }
    )

    if not dados:
        print(
            "Nenhum voo foi retornado. Verifique o codigo ICAO, "
            "tente outro aeroporto ou consulte novamente mais tarde. "
            "A OpenSky nao e uma tabela comercial de horarios de voos."
        )
        return

    registros = []

    for voo in dados:
        registros.append({
            "ICAO24": voo.get("icao24") or "N/I",
            "Identificacao": (
                voo.get("callsign") or ""
            ).strip() or "N/I",
            "Aeroporto_partida": (
                voo.get("estDepartureAirport") or "N/I"
            ),
            "Aeroporto_chegada": (
                voo.get("estArrivalAirport") or "N/I"
            ),
            "Partida_UTC": formatar_horario(voo.get("firstSeen")),
            "Chegada_UTC": formatar_horario(voo.get("lastSeen"))
        })

    tabela = pd.DataFrame(registros)

    print(f"\n========== VOOS: {aeroporto} ==========")
    exibir_tabela(
        tabela,
        f"voos_{aeroporto}_{'chegadas' if tipo == '1' else 'partidas'}.csv"
    )


# ============================================================
# MENU PRINCIPAL
# ============================================================

def menu():
    while True:
        print("\n========== RASTREADOR DE VOOS ==========")
        print("1 - Aeronaves sobre a regiao do Brasil")
        print("2 - Trajetoria de uma aeronave por ICAO24")
        print("3 - Chegadas e partidas historicas por aeroporto")
        print("0 - Encerrar")

        opcao = input("Escolha uma opcao: ").strip()

        if opcao == "1":
            consultar_voos_brasil()
        elif opcao == "2":
            consultar_trajetoria()
        elif opcao == "3":
            consultar_chegadas_partidas()
        elif opcao == "0":
            print("Programa encerrado.")
            break
        else:
            print("Opcao invalida. Tente novamente.")


if __name__ == "__main__":
    menu()
