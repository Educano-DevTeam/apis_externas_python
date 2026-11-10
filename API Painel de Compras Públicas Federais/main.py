"""
Painel de Compras Públicas Federais
Fonte: API de Dados Abertos do Compras.gov.br.
Python 3.11
"""
from __future__ import annotations

from pathlib import Path
import re
import unicodedata

import pandas as pd
import plotly.express as px
import requests

BASE_DIR = Path(__file__).resolve().parent
BASE_URL = "https://dadosabertos.compras.gov.br"
ENDPOINT_CONTRATOS = "/modulo-contratos/1_consultarContratos"
ENDPOINT_FORNECEDORES = "/modulo-fornecedor/1_consultarFornecedor"
TIMEOUT = 40
HEADERS = {"accept": "application/json", "User-Agent": "PainelComprasPublicas/1.0"}


def requisitar_pagina(endpoint: str, pagina: int, filtros: dict | None = None) -> dict:
    params = {"pagina": pagina, "tamanhoPagina": 500}
    if filtros:
        params.update({k: v for k, v in filtros.items() if v not in (None, "")})
    resposta = requests.get(BASE_URL + endpoint, params=params, headers=HEADERS, timeout=TIMEOUT)
    resposta.raise_for_status()
    return resposta.json()


def extrair_registros(payload) -> list[dict]:
    """Normaliza respostas que podem envolver uma lista dentro de uma chave."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for chave in ("resultado", "data", "dados", "items", "content", "registros"):
            valor = payload.get(chave)
            if isinstance(valor, list):
                return valor
    return []


def consultar_todas_paginas(endpoint: str, filtros: dict | None = None, limite: int = 5) -> pd.DataFrame:
    registros = []
    for pagina in range(1, limite + 1):
        payload = requisitar_pagina(endpoint, pagina, filtros)
        lote = extrair_registros(payload)
        if not lote:
            break
        registros.extend(lote)
        # A API pode informar o total de páginas; caso contrário, página vazia encerra.
        total = payload.get("totalPaginas") if isinstance(payload, dict) else None
        if total and pagina >= int(total):
            break
    if not registros:
        return pd.DataFrame()
    return pd.json_normalize(registros)


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold()


def localizar_coluna(df: pd.DataFrame, candidatos: list[str]) -> str | None:
    mapa = {normalizar(col): col for col in df.columns}
    for candidato in candidatos:
        for chave, original in mapa.items():
            if candidato in chave:
                return original
    return None


def converter_valor(serie: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce")
    texto = serie.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(texto.str.replace(r"[^0-9.-]", "", regex=True), errors="coerce")


def consultar_contratos():
    print("\nConsulta de contratos — API Compras.gov.br")
    codigo_orgao = input("Código do órgão (obrigatório pela API): ").strip()
    data_min = input("Início da vigência a partir de (AAAA-MM-DD): ").strip()
    data_max = input("Início da vigência até (AAAA-MM-DD): ").strip()
    limite = int(input("Número máximo de páginas para consultar (1 a 20): "))
    if not codigo_orgao or not data_min or not data_max:
        raise ValueError("Código do órgão e as duas datas são obrigatórios.")
    if not 1 <= limite <= 20:
        raise ValueError("O limite deve estar entre 1 e 20.")
    filtros = {
        "codigoOrgao": codigo_orgao,
        "dataVigenciaInicialMin": data_min,
        "dataVigenciaInicialMax": data_max,
    }
    df = consultar_todas_paginas(ENDPOINT_CONTRATOS, filtros, limite)
    if df.empty:
        print("A API não retornou contratos com os filtros informados.")
        return
    print(f"\nRegistros recebidos: {len(df)}")
    print("Campos disponíveis:", ", ".join(df.columns[:20]))
    print(df.head(10).to_string(index=False))
    df.to_csv(BASE_DIR / "contratos_consultados.csv", index=False, encoding="utf-8-sig")
    print("Arquivo salvo: contratos_consultados.csv")
    gerar_graficos_contratos(df)


def gerar_graficos_contratos(df: pd.DataFrame):
    coluna_valor = localizar_coluna(df, ["valorglobal", "valor global"])
    coluna_orgao = localizar_coluna(df, ["nomeorgao", "orgao", "nome unidade"])
    if coluna_valor:
        df = df.copy()
        df["_valor"] = converter_valor(df[coluna_valor])
        if coluna_orgao:
            ranking = (df.groupby(coluna_orgao, dropna=True)["_valor"].sum()
                       .sort_values(ascending=False).head(10).reset_index())
            fig = px.bar(ranking, x="_valor", y=coluna_orgao, orientation="h",
                         title="Órgãos com maior valor contratado (amostra consultada)",
                         labels={"_valor": "Valor total (R$)", coluna_orgao: "Órgão"})
            fig.write_html(BASE_DIR / "ranking_orgaos.html")
            print("Gráfico salvo: ranking_orgaos.html")
        else:
            print("Não foi identificada coluna de órgão para gerar ranking.")
    else:
        print("Não foi identificada coluna de valor; confira os campos retornados pela API.")


def consultar_fornecedores():
    print("\nConsulta de fornecedores")
    cnpj = input("CNPJ (opcional, Enter para consultar sem filtro): ").strip()
    limite = int(input("Número máximo de páginas (1 a 20): "))
    if not 1 <= limite <= 20:
        raise ValueError("O limite deve estar entre 1 e 20.")
    filtros = {"cnpj": re.sub(r"\D", "", cnpj)} if cnpj else {}
    df = consultar_todas_paginas(ENDPOINT_FORNECEDORES, filtros, limite)
    if df.empty:
        print("Nenhum fornecedor retornado. Verifique os filtros e a documentação do endpoint.")
        return
    print(f"\nFornecedores encontrados: {len(df)}")
    print(df.head(15).to_string(index=False))
    df.to_csv(BASE_DIR / "fornecedores_consultados.csv", index=False, encoding="utf-8-sig")
    print("Arquivo salvo: fornecedores_consultados.csv")


def ranking_fornecedores():
    print("\nRanking de fornecedores por valor contratado")
    limite = int(input("Número máximo de páginas de contratos (1 a 20): "))
    if not 1 <= limite <= 20:
        raise ValueError("O limite deve estar entre 1 e 20.")
    codigo_orgao = input("Código do órgão (obrigatório pela API): ").strip()
    data_min = input("Início da vigência a partir de (AAAA-MM-DD): ").strip()
    data_max = input("Início da vigência até (AAAA-MM-DD): ").strip()
    if not codigo_orgao or not data_min or not data_max:
        raise ValueError("Código do órgão e as duas datas são obrigatórios.")
    filtros = {
        "codigoOrgao": codigo_orgao,
        "dataVigenciaInicialMin": data_min,
        "dataVigenciaInicialMax": data_max,
    }
    df = consultar_todas_paginas(ENDPOINT_CONTRATOS, filtros, limite)
    if df.empty:
        print("A API não retornou contratos.")
        return
    coluna_fornecedor = localizar_coluna(df, ["nomerazaosocialfornecedor", "fornecedor", "razaosocial"])
    coluna_valor = localizar_coluna(df, ["valorglobal", "valor global"])
    if not coluna_fornecedor or not coluna_valor:
        print("Não foi possível identificar automaticamente fornecedor e valor.")
        print("Campos recebidos:", ", ".join(df.columns))
        return
    df["_valor"] = converter_valor(df[coluna_valor])
    ranking = (df.dropna(subset=["_valor"])
               .groupby(coluna_fornecedor)["_valor"].sum()
               .sort_values(ascending=False).head(10).reset_index())
    if ranking.empty:
        print("Não há valores numéricos suficientes para o ranking.")
        return
    print(ranking.to_string(index=False))
    fig = px.bar(ranking.sort_values("_valor"), x="_valor", y=coluna_fornecedor,
                 orientation="h", title="10 fornecedores com maior valor contratado",
                 labels={"_valor": "Valor total (R$)", coluna_fornecedor: "Fornecedor"})
    destino = BASE_DIR / "top_10_fornecedores.html"
    fig.write_html(destino)
    ranking.to_csv(BASE_DIR / "top_10_fornecedores.csv", index=False, encoding="utf-8-sig")
    print(f"Gráfico interativo salvo: {destino}")


def executar():
    print("=" * 62)
    print(" PAINEL DE COMPRAS PÚBLICAS FEDERAIS")
    print("=" * 62)
    print("1 - Consultar contratos")
    print("2 - Consultar fornecedores")
    print("3 - Gerar ranking dos 10 fornecedores")
    print("0 - Sair")
    while True:
        opcao = input("\nOpção: ").strip()
        if opcao == "0":
            print("Encerrando.")
            break
        try:
            if opcao == "1":
                consultar_contratos()
            elif opcao == "2":
                consultar_fornecedores()
            elif opcao == "3":
                ranking_fornecedores()
            else:
                print("Opção inválida.")
        except (requests.RequestException, ValueError, KeyError, TypeError) as erro:
            print(f"\nErro na consulta: {erro}")
            print("Confira a conexão e os parâmetros na documentação oficial da API.")


if __name__ == "__main__":
    executar()
