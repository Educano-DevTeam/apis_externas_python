# API Monitor de Indicadores Agropecuários e Climáticos

Projeto em Python 3.11 que integra dados da **Produção Agrícola Municipal (PAM/IBGE-SIDRA)** e previsões meteorológicas do **CPTEC/INPE**.

## Funcionalidades
- Consultar quantidade produzida por cultura e estado nos últimos anos.
- Gerar gráfico da série histórica de produção com Matplotlib.
- Consultar previsão estendida do CPTEC/INPE para um município (temperaturas e probabilidade de chuva).
- Exportar a previsão consultada para CSV.
- Gerar um comparativo estadual interativo em HTML para uma cultura.

## Tecnologias
`requests`, `pandas`, `matplotlib`, `plotly`, `xml.etree.ElementTree` e `datetime`.

## Instalação e execução
Na pasta deste projeto:

```bash
python -m pip install requests pandas matplotlib plotly
python main.py
```

## Fontes e observações metodológicas
- **IBGE/SIDRA:** API de valores, tabela 1612 (lavouras temporárias), variável 214 (quantidade produzida). A consulta filtra estados e períodos.
- **CPTEC/INPE:** serviço XML de busca de localidades e previsão estendida.

**Limitação importante:** a previsão pública XML do CPTEC/INPE é de curto prazo (até cerca de 14 dias), não uma série histórica anual de precipitação. Portanto, este projeto não calcula correlação histórica entre chuva acumulada e produção, nem apresenta probabilidade de chuva como se fosse precipitação em milímetros. Para esse estudo seria necessário incorporar uma base histórica meteorológica compatível (por exemplo, séries observadas de estações) e harmonizar município/estado, período e unidade. O gráfico atual mostra a série histórica agrícola; a previsão climática é consultada e exportada separadamente.

O comparativo estadual apresenta **produção total**, não produtividade por hectare. Para calcular produtividade corretamente, é necessário consultar também a variável de rendimento médio ou dividir produção pela área colhida, mantendo a unidade oficial da tabela.

## Arquivos gerados
- `producao_agricola.png`
- `previsao_cptec.csv`
- `comparativo_estadual.html`

Os arquivos são criados na própria pasta do projeto.
