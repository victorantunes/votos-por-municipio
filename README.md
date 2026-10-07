# Lula em 2022 e 2026, município a município

Comparação dos votos nominais de Lula para presidente em cada um dos 5.570 municípios brasileiros, entre o **2º turno de 2022** e o **1º turno de 2026**, com dados abertos do TSE.

**Site:** https://victorantunes.github.io/lula-2022-2026/

O site tem um mapa por município (em polígonos da malha do IBGE ou em círculos), um gráfico de dispersão (2022 no eixo X, 2026 no eixo Y, com a linha de paridade), a mesma dispersão separada por região, UF ou faixa de tamanho, e uma aba com tabelas, método e downloads.

## Resultado em uma linha
Somando os municípios (sem o exterior), Lula passou de 60.193.094 votos nominais em 2022 (2º turno) para 53.722.151 em 2026 (1º turno), o que equivale a ir de 50,9% para 45,2% dos votos nominais.

## Como foi calculado
- Votos nominais de Lula (número 13) para presidente por município. O percentual é calculado sobre os votos nominais, que excluem brancos e nulos.
- 2022: resultados de votação por município do TSE (2º turno).
- 2026: boletins de urna do 1º turno divulgados pelo TSE em 05/10/2026, somados por município.
- As cores usam os percentis P15, P35, P50, P65 e P85 da métrica escolhida (variação em pontos percentuais, saldo em votos ou retenção) entre todos os municípios.
- O exterior não entra. Boa Esperança do Norte (MT) foi desmembrada de Sorriso e só existe em 2026, então os votos dos dois foram somados para manter o território de 2022.

## Cuidados na leitura
- O 2º turno de 2022 teve dois candidatos e o 1º turno de 2026 teve vários, então parte da queda em pontos percentuais vem da mudança no número de candidatos.
- O saldo em votos depende também do comparecimento.
- Os dados são dos boletins de urna de 05/10/2026 e o TSE pode atualizar os arquivos. Para uso oficial, confira no site do TSE.

## Estrutura
```
docs/                     site publicado (GitHub Pages)
  index.html              página única, gerada por scripts/analisar.py
  dados/                  resultado_municipios.csv, resumo_uf.csv e a malha simplificada (municipios.geojson, ufs.geojson)
dados/
  2022/                   resultado de 2022 por município (TSE)
  agg_2026/               votos de presidente em 2026, agregados por município e UF (TSE)
  centroides_ibge.csv     ponto representativo de cada município (malha IBGE 2022)
  correspondencia_tse_ibge.csv
scripts/
  coletar_bu_2026.py      baixa os boletins de urna e agrega os votos de presidente
  centroides.py           extrai as coordenadas da malha do IBGE
  malha.py                simplifica a malha municipal (polígonos do mapa), preservando as fronteiras entre vizinhos
  analisar.py             calcula as métricas e gera o site
  templates/app.html      modelo da página
```

## Como refazer
```bash
pip install pandas geopandas
python scripts/coletar_bu_2026.py   # baixa cerca de 5 GB do TSE e grava dados/agg_2026/ (opcional, os agregados já estão no repositório)
python scripts/analisar.py          # gera docs/index.html e docs/dados/*.csv
python scripts/malha.py             # gera os polígonos do mapa (precisa da malha do IBGE em dados/malha_ibge/)
```

## Fonte
Tribunal Superior Eleitoral (dados abertos): https://dadosabertos.tse.jus.br. Malha municipal: IBGE.
