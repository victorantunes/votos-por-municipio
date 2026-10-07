"""Compara os votos nominais de Lula no 2º turno de 2022 e no 1º turno de 2026, por município.

Entradas
  dados/2022/presidente_2t_por_municipio.csv  (TSE, votacao_candidato_munzona_2022, 2º turno, Presidente)
  dados/agg_2026/agg_<UF>.csv                 (TSE, boletim de urna 2026 1T, Presidente, agregado por município)
  dados/centroides_ibge.csv                   (ponto representativo de cada município, malha IBGE 2022)
  dados/correspondencia_tse_ibge.csv          (código TSE -> código IBGE)
Saídas
  docs/index.html, docs/dados/resultado_municipios.csv, docs/dados/resumo_uf.csv
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent.parent
D = ROOT / 'dados'
OUT = ROOT / 'docs'
(OUT / 'dados').mkdir(parents=True, exist_ok=True)

REGIAO = {**dict.fromkeys(['AC', 'AM', 'AP', 'PA', 'RO', 'RR', 'TO'], 'Norte'),
          **dict.fromkeys(['AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE'], 'Nordeste'),
          **dict.fromkeys(['DF', 'GO', 'MS', 'MT'], 'Centro-Oeste'),
          **dict.fromkeys(['ES', 'MG', 'RJ', 'SP'], 'Sudeste'),
          **dict.fromkeys(['PR', 'RS', 'SC'], 'Sul')}

# ---------------------------------------------------------------- 2022, 2º turno
p22 = pd.read_csv(D / '2022' / 'presidente_2t_por_municipio.csv')
lula22 = p22[p22.NR_CANDIDATO == 13][['CD_MUNICIPIO', 'NM_MUNICIPIO', 'SG_UF', 'QT_VOTOS_NOMINAIS', 'total']].rename(
    columns={'CD_MUNICIPIO': 'cd_tse', 'NM_MUNICIPIO': 'nome22', 'SG_UF': 'uf', 'QT_VOTOS_NOMINAIS': 'votos22', 'total': 'total22'})
assert lula22.cd_tse.is_unique

# ---------------------------------------------------------------- 2026, 1º turno
agg = pd.concat([pd.read_csv(f, dtype={'CD_MUNICIPIO': int}) for f in sorted((D / 'agg_2026').glob('agg_??.csv'))], ignore_index=True)
agg = agg[agg.SG_UF != 'ZZ']

# Boa Esperança do Norte (MT) foi desmembrada de Sorriso e só aparece em 2026. Para manter o mesmo território de 2022,
# os votos dela são somados aos de Sorriso (código TSE 2022 de Sorriso encontrado abaixo).
NOVO_MUN = 73709
cd_sorriso = int(lula22.loc[(lula22.nome22 == 'SORRISO') & (lula22.uf == 'MT'), 'cd_tse'].iloc[0])
ctx_orig = agg.groupby('CD_MUNICIPIO')[['QT_APTOS', 'QT_COMPARECIMENTO', 'QT_SECOES']].first()
agg['CD_MUNICIPIO'] = agg['CD_MUNICIPIO'].replace({NOVO_MUN: cd_sorriso})
ctx_orig.index = ctx_orig.index.to_series().replace({NOVO_MUN: cd_sorriso})
ctx = ctx_orig.groupby(level=0).sum().rename(
    columns={'QT_APTOS': 'aptos26', 'QT_COMPARECIMENTO': 'comparec26', 'QT_SECOES': 'secoes26'})

nom = agg[agg.DS_TIPO_VOTAVEL == 'Nominal']
tot26 = nom.groupby('CD_MUNICIPIO').QT_VOTOS.sum().rename('total26')
lula26 = nom[nom.NR_VOTAVEL == 13].groupby('CD_MUNICIPIO').QT_VOTOS.sum().rename('votos26')
flav26 = nom[nom.NR_VOTAVEL == 22].groupby('CD_MUNICIPIO').QT_VOTOS.sum().rename('flavio26')
v26 = pd.concat([lula26, flav26, tot26, ctx], axis=1).reset_index().rename(columns={'CD_MUNICIPIO': 'cd_tse'})
nm26 = agg.drop_duplicates('CD_MUNICIPIO').set_index('CD_MUNICIPIO')['NM_MUNICIPIO']
print('Boa Esperança do Norte somada a Sorriso (cd_tse %d)' % cd_sorriso)

# ---------------------------------------------------------------- comparecimento 2022 (2T), para contexto
det = D / '2022' / 'detalhe_votacao_munzona_2022_BR.csv'
if det.exists():
    dt = pd.read_csv(det, sep=';', encoding='latin-1', dtype=str)
    dt = dt[(dt.DS_CARGO == 'Presidente') & (dt.NR_TURNO == '2')]
    dt['cd_tse'] = dt.CD_MUNICIPIO.astype(int)
    c22 = dt.groupby('cd_tse')[['QT_APTOS', 'QT_COMPARECIMENTO']].agg(lambda s: s.astype(int).sum()).rename(
        columns={'QT_APTOS': 'aptos22', 'QT_COMPARECIMENTO': 'comparec22'}).reset_index()
else:
    c22 = pd.DataFrame(columns=['cd_tse', 'aptos22', 'comparec22'])

# ---------------------------------------------------------------- junção
df = lula22.merge(v26, on='cd_tse', how='outer', indicator=True)
print('junção 2022 x 2026:', df['_merge'].value_counts().to_dict())
assert (df['_merge'] == 'both').all(), 'municípios sem correspondência entre 2022 e 2026'
df = df.drop(columns='_merge').merge(c22, on='cd_tse', how='left')

corr = pd.read_csv(D / 'correspondencia_tse_ibge.csv', dtype=str)
corr['cd_tse'] = corr.CD_MUNICIPIO.astype(int)
df = df.merge(corr[['cd_tse', 'CD_IBGE', 'NM_IBGE']], on='cd_tse', how='left')
cen = pd.read_csv(D / 'centroides_ibge.csv', dtype={'CD_MUN': str})
df = df.merge(cen[['CD_MUN', 'lat', 'lon']], left_on='CD_IBGE', right_on='CD_MUN', how='left').drop(columns='CD_MUN')
PARTICULAS = {'De', 'Da', 'Do', 'Das', 'Dos', 'E'}


def bonito(nome):
    palavras = nome.title().split(' ')
    return ' '.join(p.lower() if (i > 0 and p in PARTICULAS) else p for i, p in enumerate(palavras))


df['nome'] = df.nome22.map(bonito)
df.loc[df.cd_tse == cd_sorriso, 'nome'] = 'Sorriso (com Boa Esperança do Norte)'
df['regiao'] = df.uf.map(REGIAO)

# ---------------------------------------------------------------- métricas
df['pct22'] = df.votos22 / df.total22 * 100
df['pct26'] = df.votos26 / df.total26 * 100
df['saldo'] = df.votos26 - df.votos22
df['var_pp'] = df.pct26 - df.pct22
df['ret_pct'] = (df.votos26 / df.votos22 - 1) * 100
df['pct_flavio26'] = df.flavio26 / df.total26 * 100

cols = ['CD_IBGE', 'cd_tse', 'nome', 'uf', 'regiao', 'votos22', 'total22', 'pct22', 'votos26', 'total26', 'pct26', 'saldo', 'var_pp',
        'ret_pct', 'flavio26', 'pct_flavio26', 'aptos22', 'comparec22', 'aptos26', 'comparec26', 'secoes26', 'lat', 'lon']
df = df[cols].sort_values(['uf', 'nome']).reset_index(drop=True)
df.to_csv(OUT / 'dados' / 'resultado_municipios.csv', index=False, encoding='utf-8')

# ---------------------------------------------------------------- resumos
def resumo(g):
    return pd.Series({
        'municipios': len(g), 'lula_2022_2T': g.votos22.sum(), 'lula_2026_1T': g.votos26.sum(),
        'saldo': g.votos26.sum() - g.votos22.sum(),
        'pct_2022_2T': g.votos22.sum() / g.total22.sum() * 100, 'pct_2026_1T': g.votos26.sum() / g.total26.sum() * 100,
        'var_pp': g.votos26.sum() / g.total26.sum() * 100 - g.votos22.sum() / g.total22.sum() * 100,
        'mediana_var_pp_municipios': g.var_pp.median()})


por_uf = df.groupby('uf').apply(resumo).round(2)
por_uf.to_csv(OUT / 'dados' / 'resumo_uf.csv', encoding='utf-8')
nacional = resumo(df)
print('NACIONAL (soma dos municípios):'); print(nacional.round(2).to_string())
print('\nPor região:'); print(df.groupby('regiao').apply(resumo).round(2).to_string())
print('\nPor UF (saldo e pp):'); print(por_uf[['municipios', 'lula_2022_2T', 'lula_2026_1T', 'saldo', 'var_pp']].to_string())
print('\nQuantis de var_pp:', np.percentile(df.var_pp, [15, 35, 50, 65, 85]).round(2).tolist())
print('sem coordenada:', int(df.lat.isna().sum()))

# ---------------------------------------------------------------- HTMLs
def pyval(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if pd.isna(v) else round(float(v), 4)
    return v


recs = []
for i, r in df.iterrows():
    recs.append({'i': i, 'n': r.nome, 'u': r.uf, 'g': r.regiao, 'x': int(r.votos22), 'px': pyval(r.pct22), 'y': int(r.votos26),
                 'py': pyval(r.pct26), 's': int(r.saldo), 'pp': pyval(r.var_pp), 'rt': pyval(r.ret_pct),
                 'ap26': None if pd.isna(r.aptos26) else int(r.aptos26), 'cp26': None if pd.isna(r.comparec26) else int(r.comparec26),
                 'ap22': None if pd.isna(r.aptos22) else int(r.aptos22), 'cp22': None if pd.isna(r.comparec22) else int(r.comparec22),
                 'sc': int(r.secoes26), 'lat': pyval(r.lat), 'lon': pyval(r.lon)})
payload = json.dumps(recs, ensure_ascii=False, separators=(',', ':'))
meta = {'nacional': {k: pyval(v) for k, v in nacional.items()}}
# ---------------------------------------------------------------- página inicial
def inteiro(n):
    return f'{int(round(n)):,}'.replace(',', '.')


def decimal(n, casas=1, sinal=False):
    t = f'{n:+.{casas}f}' if sinal else f'{n:.{casas}f}'
    return t.replace('.', ',').replace('-', '−')


def linhas(tabela, rotulo):
    out = []
    for nome, r in tabela.iterrows():
        out.append(f"<tr><td>{nome}</td><td class='n'>{inteiro(r.municipios)}</td><td class='n'>{inteiro(r.lula_2022_2T)}</td>"
                   f"<td class='n'>{inteiro(r.lula_2026_1T)}</td><td class='n'>{inteiro(r.saldo)}</td>"
                   f"<td class='n'>{decimal(r.pct_2022_2T)}%</td><td class='n'>{decimal(r.pct_2026_1T)}%</td>"
                   f"<td class='n'>{decimal(r.var_pp, 1, True)}</td></tr>")
    return chr(10).join(out)


por_regiao = df.groupby('regiao').apply(resumo).loc[['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']]
flavio_pct = df.flavio26.sum() / df.total26.sum() * 100
idx = (ROOT / 'scripts' / 'templates' / 'app.html').read_text(encoding='utf-8')
trocas = {'__DATA__': payload, '__N_MUN__': inteiro(len(df)), '__L22__': inteiro(nacional.lula_2022_2T), '__L26__': inteiro(nacional.lula_2026_1T),
          '__SALDO__': decimal(nacional.saldo / 1e6, 2, True) + ' mi', '__P22__': decimal(nacional.pct_2022_2T), '__P26__': decimal(nacional.pct_2026_1T),
          '__VARPP__': decimal(nacional.var_pp, 1, True), '__FLAVIO__': decimal(flavio_pct),
          '__TAB_REGIAO__': linhas(por_regiao, 'Região'), '__TAB_UF__': linhas(por_uf, 'UF')}
for k, v in trocas.items():
    idx = idx.replace(k, v)
(OUT / 'index.html').write_text(idx, encoding='utf-8')
print('gerado', OUT / 'index.html')
