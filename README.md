# Votos por município: Lula no Brasil e PT no Rio Grande do Norte

Mapa, gráficos de dispersão e tabelas com os votos, a abstenção, os brancos e os nulos de cada município, com dados abertos do TSE. O site tem dois recortes:

- **Lula no Brasil:** os votos de Lula para presidente em cada um dos 5.570 municípios, no 1º e no 2º turno de 2022 e no 1º turno de 2026.
- **PT no Rio Grande do Norte:** os votos de todos os candidatos do PT no RN que concorreram em 2020 (prefeito e vereador) e em 2022 (governador, deputado federal e deputado estadual), mais Lula com os votos que recebeu no estado.

**Site:** https://victorantunes.github.io/votos-por-municipio/

O site tem um mapa por município (em polígonos da malha do IBGE ou em círculos), um gráfico de dispersão (a candidatura A no eixo X, a B no eixo Y, com a linha de paridade), a mesma dispersão separada por região, UF ou porte do município, uma lista de candidatos (no recorte do RN) e uma aba com tabelas, método e downloads.

## Como os dados estão organizados
Uma pessoa pode concorrer a cargos diferentes ao longo dos anos, então os dados separam três coisas:

| Conceito | O que é | Exemplo |
|---|---|---|
| **Disputa** | a eleição de um cargo em um ano e turno | Governador 2022, Vereador 2020 |
| **Candidatura** | um candidato em uma disputa | Fátima Bezerra, Governador 2022 |
| **Pessoa** | todas as candidaturas de um mesmo candidato, ligadas pelo CPF do cadastro do TSE (o CPF não é publicado) | quem foi candidato a prefeito em 2020 e a deputado em 2022 |

Em cada município e em cada disputa, os dados trazem também o **contexto**: eleitores aptos, comparecimento, abstenções, brancos, nulos e votos válidos. Na página, a candidatura **A** é a base e a **B** é a comparação (opcional): pode ser outro cargo da mesma pessoa, a soma dos candidatos do PT em uma disputa, ou Lula na mesma eleição.

Quem concorreu a prefeito ou vereador em 2020 só recebeu votos no seu município, então o mapa de um candidato municipal destaca um único município. A "soma do PT" reúne os votos nominais de todos os candidatos do partido em cada disputa e mostra a força do PT nos municípios em que ele lançou candidatos.

## Participação: abstenção, brancos e nulos
| Medida | Cálculo |
|---|---|
| **Abstenção** | `(aptos − comparecimento) ÷ aptos`. Eleitores de seções que não puderam ser instaladas contam como abstenção. |
| **Brancos** | `votos em branco ÷ comparecimento` |
| **Nulos** | `(comparecimento − válidos − brancos) ÷ comparecimento`. Inclui os nulos digitados pelo eleitor, os anulados depois da eleição e os anulados sub judice. Nos boletins de urna de 2026 só há válidos, brancos e nulos. |
| **Votos válidos** | votos nominais, mais os votos de legenda nas eleições proporcionais (deputado e vereador) |
| **% dos votos válidos** | `votos do candidato ÷ votos válidos do município` |

Em cada município, aptos = abstenções + comparecimento, e comparecimento = válidos + brancos + nulos. O mapa e os gráficos podem ser coloridos por essas medidas e pela variação delas entre A e B.

## Métricas de comparação
Valem quando há uma candidatura B para comparar com a A. O valor é sempre B menos A: um número negativo quer dizer que B teve menos votos do que A naquele município.

| Métrica | Cálculo | Como ler |
|---|---|---|
| **Variação em pontos percentuais** (padrão) | `% de B − % de A`, em que `% = votos ÷ votos válidos` | Compara a participação. Não depende do tamanho do município nem do comparecimento, então é a mais comparável entre cidades grandes e pequenas. |
| **Saldo em votos** | `votos de B − votos de A` | Quantos votos o município ganhou ou perdeu. Depende do tamanho do município. Serve para ver o peso de cada município no total. |
| **Retenção** | `(votos de B ÷ votos de A − 1) × 100` | Variação percentual dos votos. Uma retenção de −17% quer dizer que B ficou com 83% dos votos de A. Reflete também mudanças no comparecimento e nos votos brancos e nulos. |

Exemplo, São Paulo, Lula de 2022 (2º turno) para 2026 (1º turno): em 2022 Lula teve 3.677.921 votos entre 6.869.405 válidos (53,54%), e em 2026 teve 3.052.349 entre 6.553.181 (46,58%). O saldo é de −625.572 votos, a variação é de −6,96 pontos percentuais e a retenção é de −17,0%.

### Percentis e as seis cores
O percentil mostra a posição de um município em relação aos demais. Os municípios com dados são colocados em ordem, do menor valor ao maior. O percentil 15 (P15) é o valor abaixo do qual ficam 15% dos municípios, o P50 é a mediana e o P85 é o valor acima do qual ficam os 15% maiores. Os cinco cortes P15, P35, P50, P65 e P85 dividem os municípios em seis classes, com 15%, 20%, 15%, 15%, 20% e 15% deles.

Nas comparações da mesma pessoa ou do mesmo partido ao longo do tempo, as classes vão de Queda Severa a Destaque Positivo (vermelho a verde). Nas demais medidas vão de Menores 15% a Maiores 15% (azul, mais escuro quanto maior o valor). Municípios sem dados ficam em cinza, e quando há poucos municípios com dados (por exemplo, um candidato a vereador) não há percentis. As classes são relativas: dizem se o município está acima ou abaixo dos outros, e não se o valor é positivo ou negativo.

## O que entrou e o que ficou de fora (recorte do RN)
- Entraram as pessoas que foram candidatas pelo PT no RN em 2020 ou 2022, com todas as candidaturas delas que tiveram votos próprios, inclusive as de outro partido no outro ano, e Lula (1º e 2º turnos de 2022 e 1º turno de 2026, só com os votos do estado).
- Ficaram de fora vice-prefeitos, vice-governadores e suplentes de senador (os votos vão para o titular), os votos de legenda, candidatos de aliados do PT, e as eleições de 2024 e de 2026, exceto Lula em 2026. Nos arquivos do TSE não há candidato do PT ao Senado com votos no RN em 2022.
- Em 2022 o PT formou federação com o PCdoB e o PV. A soma do PT considera só os candidatos registrados pelo próprio partido.

## Cuidados na leitura
- O 2º turno de 2022 teve dois candidatos e o 1º turno de 2026 teve vários, então parte da queda em pontos percentuais de Lula vem da mudança no número de candidatos.
- Comparar cargos diferentes mistura efeitos distintos. Uma eleição para deputado tem dezenas de candidatos disputando os mesmos votos, então a % dos votos válidos de um deputado é sempre pequena.
- O saldo em votos depende também do comparecimento.
- O exterior não entra. Boa Esperança do Norte (MT) foi desmembrada de Sorriso e só existe em 2026, então os votos dos dois foram somados para manter o território de 2022.
- Os dados de 2026 são dos boletins de urna de 05/10/2026 e o TSE pode atualizar os arquivos. Para uso oficial, confira no site do TSE.

## Estrutura
```
docs/                     site publicado (GitHub Pages)
  index.html              página única, gerada por scripts/analisar.py
  dados/                  dados lidos pela página (escopo_br.json, escopo_rn.json), malhas (municipios.geojson, municipios_rn.geojson, ufs.geojson, uf_rn.geojson)
                          e tabelas para baixar (resultado_municipios.csv, resumo_uf.csv, rn_candidaturas.csv, rn_votos_por_municipio.csv, rn_participacao.csv)
dados/
  br/                     Lula no Brasil: contexto.csv (participação por município e eleição) e lula.csv (votos)
  rn/                     PT no RN: disputas.csv, contexto.csv, pessoas.csv, candidaturas.csv, votos.csv
  agg_2026/               votos de presidente em 2026, agregados por município e UF (boletins de urna do TSE)
  centroides_ibge.csv     ponto representativo de cada município (malha IBGE 2022)
  correspondencia_tse_ibge.csv
  tse/                    arquivos brutos do TSE (não versionados, porque o cadastro de candidatos traz CPF e e-mail)
scripts/
  coletar_tse.py          baixa do TSE os resultados de 2020 e 2022 e extrai o RN e o Presidente de 2022
  coletar_bu_2026.py      baixa os boletins de urna de 2026 e agrega os votos de presidente
  preparar.py             organiza tudo em tabelas simples (dados/br e dados/rn)
  centroides.py           extrai as coordenadas da malha do IBGE
  malha.py                simplifica a malha municipal (polígonos do mapa), preservando as fronteiras entre vizinhos
  analisar.py             gera os dados da página, as tabelas para baixar e o site
  templates/app.html      modelo da página
```

## Como refazer
```bash
pip install pandas geopandas
python scripts/coletar_tse.py       # baixa cerca de 700 MB do TSE (2020 e 2022) para dados/tse/
python scripts/coletar_bu_2026.py   # baixa cerca de 5 GB do TSE e grava dados/agg_2026/ (opcional, os agregados já estão no repositório)
python scripts/preparar.py          # gera dados/br e dados/rn
python scripts/malha.py             # gera os polígonos do mapa (precisa da malha do IBGE em dados/malha_ibge/)
python scripts/analisar.py          # gera docs/index.html, docs/dados/*.json e docs/dados/*.csv
```

## Fonte
- Tribunal Superior Eleitoral (dados abertos): https://dadosabertos.tse.jus.br
- IBGE, malha municipal 2022: https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip
