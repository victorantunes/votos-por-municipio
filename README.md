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

## Métricas
Todas comparam o mesmo município nas duas eleições. Valor negativo significa que Lula teve menos votos no 1º turno de 2026 do que no 2º turno de 2022. As seis cores do mapa e dos gráficos usam os percentis P15, P35, P50, P65 e P85 da métrica escolhida, calculados entre os 5.570 municípios.

| Métrica | Cálculo | Como ler |
|---|---|---|
| **Variação em pontos percentuais** (padrão) | `% 2026 − % 2022`, em que `% = votos de Lula ÷ votos nominais de todos os candidatos` | Compara a participação de Lula. Não depende do tamanho do município nem do comparecimento, então é a mais comparável entre cidades grandes e pequenas. |
| **Saldo em votos** | `votos 2026 − votos 2022` | Quantos votos o município ganhou ou perdeu. Depende do tamanho do município (as maiores perdas ficam nas cidades grandes) e do comparecimento. Serve para ver o peso de cada município no total nacional. |
| **Retenção** | `(votos 2026 ÷ votos 2022 − 1) × 100` | Variação percentual dos votos do próprio Lula. Uma retenção de −17% quer dizer que ele manteve 83% dos votos de 2022. Reflete também mudanças no comparecimento e nos votos brancos e nulos. |

Exemplo, São Paulo: em 2022 (2º turno) Lula teve 3.677.921 votos entre 6.869.405 nominais (53,54%), e em 2026 (1º turno) teve 3.052.349 entre 6.553.181 (46,58%). O saldo é de −625.572 votos, a variação é de −6,96 pontos percentuais e a retenção é de −17,0%. A retenção cai mais do que os pontos percentuais porque o total de votos nominais da cidade também diminuiu.

Nos dados, o saldo quase não se relaciona com as outras duas métricas (correlação próxima de zero), enquanto a variação em pontos percentuais e a retenção andam juntas (correlação de 0,57).

### Percentis e as seis cores
O percentil mostra a posição de um município em relação aos demais. Para a métrica escolhida, os 5.570 municípios são colocados em ordem, do pior valor ao melhor. O percentil 15 (P15) é o valor abaixo do qual ficam 15% dos municípios, o P50 é a mediana (metade fica abaixo e metade acima) e o P85 é o valor acima do qual ficam os 15% melhores. Os cinco cortes P15, P35, P50, P65 e P85 dividem os municípios em seis classes:

| Classe | Faixa | Parcela dos municípios |
|---|---|---|
| Queda Severa | do P0 ao P15 (os piores) | 15% |
| Queda Forte | do P15 ao P35 | 20% |
| Abaixo da Mediana | do P35 ao P50 | 15% |
| Acima da Mediana | do P50 ao P65 | 15% |
| Retenção Forte | do P65 ao P85 | 20% |
| Destaque Positivo | do P85 ao P100 (os melhores) | 15% |

Os limites de cada classe aparecem na legenda e mudam conforme a métrica. Na variação em pontos percentuais, com os dados atuais, os cortes P15, P35, P50, P65 e P85 são −10,51, −8,23, −7,14, −6,19 e −4,64 pontos percentuais. Os percentis são calculados entre todos os municípios do país, então as cores têm o mesmo significado no mapa, na dispersão e em cada painel por região ou UF.

As classes são relativas, e não absolutas. Elas dizem se o município foi melhor ou pior do que os outros, e não se ele ganhou ou perdeu votos. Com os dados atuais, até o limite inferior do Destaque Positivo é negativo (−4,64 pontos percentuais), o que significa que muitos municípios dessa classe também tiveram queda, só que menor do que a da maioria.

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
