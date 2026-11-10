# API Painel de Compras Públicas Federais

Aplicação de terminal em Python 3.11 para consultar dados públicos de contratos e fornecedores do Compras.gov.br.

## Funcionalidades
- Consultar contratos por código do órgão e intervalo de início de vigência, com paginação por `pagina` e `tamanhoPagina`.
- Consultar fornecedores, com opção de filtro por CNPJ.
- Exportar os registros recebidos para CSV.
- Gerar ranking dos 10 fornecedores com maior valor contratado.
- Gerar gráfico HTML de ranking de órgãos quando os campos necessários estiverem disponíveis.

## Tecnologias
`requests`, `pandas`, `plotly`, `re` e `unicodedata`.

## Instalação e execução
```bash
python -m pip install requests pandas plotly
python main.py
```

## API utilizada
- Base: `https://dadosabertos.compras.gov.br`
- Contratos: `/modulo-contratos/1_consultarContratos`
- Fornecedores: `/modulo-fornecedor/1_consultarFornecedor`
- Documentação interativa: https://dadosabertos.compras.gov.br/swagger-ui/index.html

## Paginação, filtros e limitações
A consulta percorre páginas sequenciais usando `pagina` e `tamanhoPagina` (até 500 registros por página). O endpoint de contratos exige `codigoOrgao`, `dataVigenciaInicialMin` e `dataVigenciaInicialMax`; por isso, o programa solicita esses filtros antes da consulta. O módulo de fornecedores aceita filtro por CNPJ. A API limita o volume de chamadas por minuto, então evite executar muitas consultas seguidas.

O ranking usa somente os contratos consultados para o órgão e período selecionados, não representa automaticamente todo o país. O endpoint de contratos não oferece filtro direto por UF. O mapa de calor por UF não é gerado nesta versão: seria necessário enriquecer os fornecedores com endereço/UF e padronizar esses dados antes de agregar os valores. O programa não inventa UF ausente.

O mapa de calor por UF não é gerado automaticamente nesta versão: a API de contratos pode não retornar UF do fornecedor em todos os registros. Para produzir um mapa correto, seria necessário enriquecer cada fornecedor com seu cadastro/endereço e padronizar os códigos estaduais antes de agregar os valores. O programa não inventa UF ausente.

## Arquivos gerados
- `contratos_consultados.csv`
- `fornecedores_consultados.csv`
- `top_10_fornecedores.csv`
- `top_10_fornecedores.html`
- `ranking_orgaos.html`
