"""
Monitor de Indicadores Agropecuários e Climáticos
Fontes: SIDRA/IBGE e serviços XML do CPTEC/INPE.
Python 3.11
"""
from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import requests

BASE_DIR = Path(__file__).resolve().parent
SIDRA_URL = "https://apisidra.ibge.gov.br/values"
CPTEC_URL = "https://servicos.cptec.inpe.br/XML"
TIMEOUT = 30
HEADERS = {"User-Agent": "MonitorAgroClima/1.0 (projeto educacional)"}

ESTADOS = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29, "MG": 31, "ES": 32, "RJ": 33, "SP": 35, "PR": 41,
    "SC": 42, "RS": 43, "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}
# Tabela SIDRA 1612: lavouras temporárias. Variável 214: quantidade produzida.
TABELA_PAM = "1612"
VAR_PRODUCAO = "214"
CLASSIFICACAO_CULTURA = "81"


def get_json(url: str, params: dict | None = None):
    resposta = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    resposta.raise_for_status()
    return resposta.json()


def get_xml(url: str, params: dict | None = None):
    resposta = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    resposta.raise_for_status()
    return ET.fromstring(resposta.content)


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold().strip()


def escolher_estado() -> tuple[str, int]:
    print("\nEstados disponíveis:", ", ".join(ESTADOS))
    while True:
        uf = input("UF do estado: ").strip().upper()
        if uf in ESTADOS:
            return uf, ESTADOS[uf]
        print("UF inválida. Tente novamente.")


def obter_producao(uf: str, anos: int = 5) -> pd.DataFrame:
    """Consulta quantidade produzida na PAM para todas as culturas do estado."""
    url = f"{SIDRA_URL}/t/{TABELA_PAM}/n3/{ESTADOS[uf]}/v/{VAR_PRODUCAO}/p/last%20{anos}/c{CLASSIFICACAO_CULTURA}/all"
    dados = get_json(url)
    if not isinstance(dados, list) or len(dados) < 2:
        raise ValueError("A API SIDRA não retornou registros para os filtros informados.")
    df = pd.DataFrame(dados[1:])
    # Os nomes das colunas vêm na primeira linha do retorno da API.
    df.columns = dados[0].keys()
    colunas = list(df.columns)
    periodo = next((c for c in colunas if "período" in normalizar(c)), colunas[0])
    cultura = next((c for c in colunas if "produto das lavouras" in normalizar(c) or "variavel" in normalizar(c)), None)
    valor = next((c for c in colunas if normalizar(c) == "valor"), colunas[-1])
    if cultura is None:
        # A API geralmente nomeia a classificação com "Produto das lavouras temporárias".
        cultura = next((c for c in colunas if c not in (periodo, valor) and "unidade" not in normalizar(c)), colunas[-2])
    df["Ano"] = pd.to_numeric(df[periodo].astype(str).str.extract(r"(\d{4})")[0], errors="coerce")
    df["Cultura"] = df[cultura].astype(str)
    df["Producao"] = pd.to_numeric(df[valor].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False), errors="coerce")
    df = df.dropna(subset=["Ano", "Producao"])
    return df[["Ano", "Cultura", "Producao"]].sort_values("Ano")


def obter_previsao_cptec(nome_cidade: str) -> pd.DataFrame:
    """Busca município no CPTEC e consulta previsão estendida (até 14 dias)."""
    raiz = get_xml(f"{CPTEC_URL}/listaCidades", {"city": nome_cidade})
    cidades = raiz.findall(".//cidade")
    if not cidades:
        raise ValueError("Município não localizado no CPTEC. Tente outro nome sem acentos.")
    cidade = cidades[0]
    codigo = cidade.findtext("id")
    if not codigo:
        raise ValueError("O CPTEC não informou o código do município.")
    previsao = get_xml(f"{CPTEC_URL}/cidade/{codigo}/estendida.xml")
    registros = []
    for item in previsao.findall(".//previsao"):
        registros.append({
            "Data": item.findtext("dia"),
            "Minima": item.findtext("minima"),
            "Maxima": item.findtext("maxima"),
            "Probabilidade_chuva": item.findtext("probabilidade"),
            "Resumo": item.findtext("tempo"),
        })
    df = pd.DataFrame(registros)
    if df.empty:
        raise ValueError("A previsão do CPTEC veio vazia.")
    df["Minima"] = pd.to_numeric(df["Minima"], errors="coerce")
    df["Maxima"] = pd.to_numeric(df["Maxima"], errors="coerce")
    df["Probabilidade_chuva"] = pd.to_numeric(df["Probabilidade_chuva"], errors="coerce")
    return df


def filtrar_cultura(df: pd.DataFrame, cultura: str) -> pd.DataFrame:
    encontrados = df[df["Cultura"].map(normalizar).str.contains(normalizar(cultura), na=False)]
    if encontrados.empty:
        amostras = ", ".join(df["Cultura"].drop_duplicates().head(12).tolist())
        raise ValueError(f"Cultura '{cultura}' não encontrada. Exemplos retornados: {amostras}")
    return encontrados


def grafico_comparativo(df: pd.DataFrame, uf: str, cultura: str):
    serie = filtrar_cultura(df, cultura)
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(serie["Ano"], serie["Producao"], alpha=0.75, label="Produção (toneladas)")
    ax1.set_xlabel("Ano")
    ax1.set_ylabel("Produção (toneladas)")
    ax1.set_title(f"Produção agrícola — {cultura.title()} ({uf})")
    ax1.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    destino = BASE_DIR / "producao_agricola.png"
    fig.savefig(destino, dpi=140)
    plt.close(fig)
    print(f"Gráfico salvo em: {destino}")


def mapa_produtividade(df: pd.DataFrame, cultura: str):
    """Comparativo estadual da produção; não confundir produção total com produtividade."""
    # Consulta por estado para comparar a produção estadual no ano mais recente disponível.
    valores = []
    for uf, codigo in ESTADOS.items():
        try:
            url = f"{SIDRA_URL}/t/{TABELA_PAM}/n3/{codigo}/v/{VAR_PRODUCAO}/p/last%201/c{CLASSIFICACAO_CULTURA}/all"
            dados = get_json(url)
            if len(dados) > 1:
                cabecalho = list(dados[0].keys())
                registros = pd.DataFrame(dados[1:])
                registros.columns = cabecalho
                col_cultura = next((c for c in cabecalho if "produto das lavouras" in normalizar(c)), cabecalho[-2])
                col_valor = cabecalho[-1]
                filtrado = registros[registros[col_cultura].map(normalizar).str.contains(normalizar(cultura), na=False)]
                if not filtrado.empty:
                    numero = pd.to_numeric(filtrado.iloc[0][col_valor].replace(".", "").replace(",", "."), errors="coerce")
                    if pd.notna(numero):
                        valores.append({"UF": uf, "Producao": numero})
        except (requests.RequestException, ValueError, KeyError, IndexError):
            continue
    if not valores:
        raise ValueError("Não foi possível reunir dados estaduais suficientes para o mapa.")
    mapa = pd.DataFrame(valores)
    fig = px.bar(
        mapa.sort_values("Producao", ascending=False), x="UF", y="Producao",
        title=f"Produção de {cultura.title()} por estado (SIDRA/IBGE)",
        labels={"UF": "Estado", "Producao": "Produção (toneladas)"},
    )
    destino = BASE_DIR / "comparativo_estadual.html"
    fig.write_html(destino)
    print(f"Mapa interativo salvo em: {destino}")


def executar():
    print("=" * 65)
    print(" MONITOR DE INDICADORES AGROPECUÁRIOS E CLIMÁTICOS")
    print("=" * 65)
    print("1 - Consultar produção agrícola por estado e cultura")
    print("2 - Consultar previsão climática CPTEC/INPE")
    print("3 - Gerar mapa de produção por estado")
    print("0 - Sair")
    while True:
        opcao = input("\nOpção: ").strip()
        if opcao == "0":
            print("Encerrando.")
            break
        try:
            if opcao == "1":
                uf, _ = escolher_estado()
                cultura = input("Cultura (ex.: soja, milho): ").strip()
                anos = int(input("Quantidade de anos (1 a 20): "))
                if not 1 <= anos <= 20:
                    raise ValueError("Informe um período entre 1 e 20 anos.")
                dados = obter_producao(uf, anos)
                resultado = filtrar_cultura(dados, cultura)
                print(resultado.to_string(index=False))
                grafico_comparativo(dados, uf, cultura)
            elif opcao == "2":
                cidade = input("Município para consulta (ex.: Campinas): ").strip()
                previsao = obter_previsao_cptec(cidade)
                print(previsao.to_string(index=False))
                destino = BASE_DIR / "previsao_cptec.csv"
                previsao.to_csv(destino, index=False, encoding="utf-8-sig")
                print(f"Previsão exportada para: {destino}")
            elif opcao == "3":
                cultura = input("Cultura (ex.: soja, milho): ").strip()
                # O mapa consulta a série mais recente disponível para cada UF.
                mapa_produtividade(pd.DataFrame(), cultura)
            else:
                print("Opção inválida.")
        except (requests.RequestException, ValueError, KeyError, IndexError, ET.ParseError) as erro:
            print(f"\nNão foi possível concluir a consulta: {erro}")


if __name__ == "__main__":
    executar()
