# Votos por município: Lula no Brasil e PT em todos os estados

Mapa, gráficos de dispersão e tabelas com os votos, a abstenção, os brancos e os nulos de cada município, com dados abertos do TSE. O site tem dois recortes:

- **Lula no Brasil:** os votos de Lula para presidente em cada um dos 5.570 municípios, no 1º e no 2º turno de 2022 e no 1º turno de 2026.
- **PT em cada estado:** os votos de todos os candidatos do PT que concorreram em 2020 e 2024 (prefeito e vereador), em 2022 e em 2026 (governador, senador e deputados). Cada um dos 27 estados é um recorte, escolhido no topo da página. Há três modos: **comparar com 2026** (quem concorreu em 2020, 2022 ou 2024 e também em 2026), **analisar isoladamente** (uma candidatura sozinha, de qualquer candidato e ano, sem outros dados no mapa) e **qualquer cargo e ano** (comparar livremente quaisquer candidaturas do mesmo estado). Lula não entra nos recortes estaduais: ele tem o recorte "Lula no Brasil".

Uma pessoa que foi candidata em estados diferentes (por exemplo, vereadora em um estado em 2020 e deputada federal em outro em 2026) aparece em cada um deles, só com os votos que recebeu ali. Um aviso abaixo do mapa lista as candidaturas dos outros estados com um link, e a busca de candidatos também encontra pessoas de outros estados (índice nacional carregado só na primeira busca).

**Site:** https://victorantunes.github.io/votos-por-municipio/

O site tem um mapa por município (em polígonos da malha do IBGE ou em círculos), um gráfico de dispersão (a candidatura A no eixo X, a B no eixo Y, com a linha de paridade), a mesma dispersão separada por região, UF ou porte do município (no detalhe por local de votação, só por porte), uma lista de candidatos (nos recortes por estado, com paginação) e uma aba com tabelas, método e downloads.

## Como os dados estão organizados
Uma pessoa pode concorrer a cargos diferentes ao longo dos anos, então os dados separam três coisas:

| Conceito | O que é | Exemplo |
|---|---|---|
| **Disputa** | a eleição de um cargo em um ano e turno | Governador 2022, Vereador 2020 |
| **Candidatura** | um candidato em uma disputa | Fátima Bezerra, Governador 2022 |
| **Pessoa** | todas as candidaturas de um mesmo candidato, ligadas pelo título de eleitor do cadastro do TSE (o número não é publicado) | quem foi candidata a vereadora em 2020 e a deputada federal em 2026 |

Em cada município e em cada disputa, os dados trazem também o **contexto**: eleitores aptos, comparecimento, abstenções, brancos, nulos e votos válidos. Na página, a candidatura **A** é a base e a **B** é a comparação (opcional): pode ser outro cargo da mesma pessoa, a soma dos candidatos do PT em uma disputa, ou Lula na mesma eleição. No tipo "Comparar com 2026", A é a candidatura anterior (do mesmo cargo, quando existe, ou a mais recente) e B é a de 2026. No tipo "Analisar isoladamente" só existe a A, e o mapa mostra apenas essa candidatura, sem comparação com outros anos nem com outros candidatos.

Quem concorreu a prefeito ou vereador em 2020 ou 2024 só recebeu votos no seu município, então o mapa de um candidato municipal destaca um único município. A "soma do PT" reúne os votos nominais de todos os candidatos do partido em cada disputa e mostra a força do PT nos municípios em que ele lançou candidatos.

## Participação: abstenção, brancos e nulos
| Medida | Cálculo |
|---|---|
| **Abstenção** | `(aptos − comparecimento) ÷ aptos`. Eleitores de seções que não puderam ser instaladas contam como abstenção. |
| **Brancos** | `votos em branco ÷ comparecimento` (no Senado de 2026, sobre os votos dados, que são o dobro do comparecimento) |
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

Nas comparações da mesma pessoa ou do mesmo partido ao longo do tempo, as classes vão de Queda Severa a Destaque Positivo (vermelho a verde). Nas demais medidas vão de Menores 15% a Maiores 15%: os votos e a % dos votos do candidato usam a mesma escala de vermelho a verde (verde é mais votos), a abstenção, os brancos e os nulos usam azul (mais escuro é maior), e as diferenças que não são de desempenho usam marrom a verde-azulado. Municípios sem dados ficam em cinza, e quando há poucos municípios com dados (por exemplo, um candidato a vereador) não há percentis. As classes são relativas: dizem se o município está acima ou abaixo dos outros, e não se o valor é positivo ou negativo (nas comparações, "Destaque Positivo" pode incluir quem caiu menos que os demais). Além das seis classes, a legenda tem duas categorias, **Mínimo** (violeta) e **Máximo** (dourado), que marcam o município de menor e o de maior valor (P0 e P100), com um anel no mapa.

## Detalhe por bairro e local de votação
Marcando "Detalhar por bairro e local de votação", o mapa e o gráfico passam a mostrar os votos abaixo do município. O TSE publica os votos por seção eleitoral e, para cada local de votação, o bairro, as coordenadas e os eleitores por seção. As seções são somadas por local, e cada local é atribuído ao bairro do IBGE (Censo 2022) que o contém. O detalhe existe nos 27 estados. Nos recortes de estado o campo fica no topo do mapa, e em "Lula no Brasil" ele vale depois de escolher uma UF (os votos de Lula por local de votação nos três turnos), porque carregar o país inteiro de uma vez seria pesado.

- O IBGE só tem bairros para 895 municípios, quase sempre as capitais e as maiores cidades. Nos outros e fora dos bairros (zona rural), cada local de votação é um ponto quando se mostra uma única eleição.
- Ao comparar anos diferentes a unidade é o bairro e, fora dele, o município (ou a parte dele fora dos bairros), porque os locais de votação mudam de um ano para outro. A exceção é o Distrito Federal, um único município sem bairros no IBGE, onde a unidade é o local de votação que existe nos dois anos (mesmo nome e bairro no cadastro do TSE) e o restante aparece junto.
- O fundo do mapa mostra o município inteiro, mais claro e com as mesmas faixas de cor, para a parte que não pertence a nenhum bairro do IBGE (como a zona rural) não ficar em branco.
- O bairro é o do local de votação, não o de residência. Locais sem coordenada (cerca de 3%) recebem a média dos locais do mesmo bairro, e os fora de qualquer bairro vão para o mais próximo, até 2 km.
- A soma das seções pode diferir até cerca de 2% do total do município (votos anulados depois da eleição aparecem nas seções).
- Desempenho: o detalhe vem de arquivos estáticos em `docs/dados/granular/<uf>/`, baixados sob demanda só para as candidaturas A e B (e, em "Lula no Brasil", só para a UF escolhida). Não há servidor.

## O que entrou e o que ficou de fora
- Entraram as pessoas que foram candidatas pelo PT no estado em 2020, 2022, 2024 ou 2026, com todas as candidaturas delas que tiveram votos próprios, inclusive as de outro partido em outro ano. Lula fica de fora dos recortes estaduais.
- Ficaram de fora vice-prefeitos, vice-governadores e suplentes de senador (os votos vão para o titular), os votos de legenda e candidatos de aliados do PT.
- Em 2022 o PT formou federação com o PCdoB e o PV. A soma do PT considera só os candidatos registrados pelo próprio partido.

## Cuidados na leitura
- O 2º turno de 2022 teve dois candidatos e o 1º turno de 2026 teve vários, então parte da queda em pontos percentuais de Lula vem da mudança no número de candidatos.
- Comparar cargos diferentes mistura efeitos distintos. Uma eleição para deputado tem dezenas de candidatos disputando os mesmos votos, então a % dos votos válidos de um deputado é sempre pequena.
- O saldo em votos depende também do comparecimento.
- O exterior não entra. Boa Esperança do Norte (MT) foi desmembrada de Sorriso e só existe em 2026, então os votos dos dois foram somados para manter o território de 2022.
- Votos anulados depois da eleição (candidaturas indeferidas) não entram na votação do candidato, e o número de votos anulados aparece nos detalhes.
- Os dados de 2026 são do 1º turno. Os de Lula vêm dos boletins de urna de 05/10/2026, e os dos demais candidatos, dos resultados por candidato baixados do TSE em 07/10/2026. A situação de cada candidato é a daquele arquivo, e os votos anulados sub judice não entram. O TSE pode atualizar os arquivos. Para uso oficial, confira no site do TSE.
- Em 2026 o Senado tem duas vagas e cada eleitor dá dois votos. Os brancos e nulos dessa disputa são calculados sobre os votos dados (dois por eleitor), e a % dos votos válidos de um senador não é comparável com a de um governador.

## Estrutura
```
docs/                     site publicado (GitHub Pages)
  index.html              página única, gerada por scripts/analisar.py
  dados/                  dados lidos pela página: escopo_br.json (Lula), uf/<uf>.json (um por estado), ufs.json (estados) e indice_pessoas.json (busca nacional);
                          malhas (municipios.geojson, ufs.geojson, malha/<uf>.geojson, bairros/<uf>.geojson); granular/<uf>/ (locais de votação e votos por local,
                          carregados sob demanda); tabelas para baixar (resultado_municipios.csv, resumo_uf.csv, csv/<uf>_candidaturas.csv, csv/<uf>_participacao.csv)
dados/
  br/                     Lula no Brasil: contexto.csv (participação por município e eleição) e lula.csv (votos)
  uf/<UF>/                PT no estado: disputas.csv, contexto.csv, pessoas.csv, candidaturas.csv, votos.csv (e locais.csv, contexto_local.csv, votos_local.csv e bairros.csv)
  agg_2026/               votos de presidente em 2026, agregados por município e UF (boletins de urna do TSE)
  centroides_ibge.csv     ponto representativo de cada município (malha IBGE 2022)
  correspondencia_tse_ibge.csv
  tse/                    arquivos brutos do TSE (não versionados, porque o cadastro de candidatos traz CPF e e-mail)
scripts/
  coletar_tse.py          baixa do TSE os resultados de 2020, 2022, 2024 e 2026, os votos por seção e os locais de votação (cerca de 9 GB) e os bairros do IBGE
  coletar_bu_2026.py      baixa os boletins de urna de 2026 e agrega os votos de presidente
  preparar.py             organiza o recorte do Brasil (dados/br) e define as disputas
  preparar_uf.py          organiza os candidatos do PT de cada estado (dados/uf/<UF>); o partido é o parâmetro PARTIDO
  secoes.py               soma os votos por seção em locais de votação e bairros do IBGE de cada estado (python scripts/secoes.py RN DF ...), lendo direto dos zips
  centroides.py           extrai as coordenadas da malha do IBGE
  malha.py                simplifica a malha municipal (Brasil e um arquivo por estado), preservando as fronteiras entre vizinhos
  comum.py                funções usadas por analisar.py e gerar_ufs.py
  gerar_ufs.py            gera o arquivo de cada estado, o índice de pessoas e as tabelas para baixar
  analisar.py             gera os dados da página, as tabelas para baixar e o site
  templates/app.html      modelo da página
```

## Como refazer
```bash
pip install pandas geopandas
python scripts/coletar_tse.py       # baixa cerca de 2 GB do TSE (2020, 2022, 2024 e 2026) e os bairros do IBGE
python scripts/coletar_bu_2026.py   # baixa cerca de 5 GB do TSE e grava dados/agg_2026/ (opcional, os agregados já estão no repositório)
python scripts/preparar.py          # gera dados/br
python scripts/preparar_uf.py       # gera dados/uf/<UF> para os 27 estados (cerca de 4 minutos)
python scripts/secoes.py RN DF      # votos por local de votação e bairro de cada estado listado (precisa dos boletins de urna de 2026 e do coletar_tse.py)
python scripts/malha.py             # gera os polígonos do mapa (precisa da malha do IBGE em dados/malha_ibge/)
python scripts/analisar.py          # gera docs/index.html, docs/dados/*.json e docs/dados/csv/*.csv
```

## Fonte
- Tribunal Superior Eleitoral (dados abertos): https://dadosabertos.tse.jus.br
- IBGE, malha municipal 2022: https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip
