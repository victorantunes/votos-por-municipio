"""Funções e tabelas usadas por analisar.py e gerar_ufs.py: municípios, disputas e gravação dos arquivos do site."""
import json
import re
import sys
from datetime import datetime
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
PARTICULAS = {'De', 'Da', 'Do', 'Das', 'Dos', 'E'}
BUILD = datetime.now().strftime('%Y%m%d%H%M%S')  # evita que o navegador use dados antigos em cache
REPO = 'votos-por-municipio'  # nome do repositório no GitHub, usado nos links da página
CTX = ['aptos', 'comparec', 'abst', 'brancos', 'nulos', 'validos']

# nome completo, nome curto (listas e eixos) e tipo (maj = majoritária, prop = proporcional)
DISPUTAS = {
    'ver20': ('Vereador 2020', 'Vereador 2020', 'Vereador', 2020, 'prop'),
    'pref20': ('Prefeito 2020', 'Prefeito 2020', 'Prefeito', 2020, 'maj'),
    'pref20t2': ('Prefeito 2020 (2º turno)', 'Prefeito 2020 2ºT', 'Prefeito', 2020, 'maj'),
    'de22': ('Deputado Estadual 2022', 'Dep. Estadual 2022', 'Deputado Estadual', 2022, 'prop'),
    'df22': ('Deputado Federal 2022', 'Dep. Federal 2022', 'Deputado Federal', 2022, 'prop'),
    'dd22': ('Deputado Distrital 2022', 'Dep. Distrital 2022', 'Deputado Distrital', 2022, 'prop'),
    'sen22': ('Senador 2022', 'Senador 2022', 'Senador', 2022, 'maj'),
    'gov22': ('Governador 2022', 'Governador 2022', 'Governador', 2022, 'maj'),
    'gov22t2': ('Governador 2022 (2º turno)', 'Governador 2022 2ºT', 'Governador', 2022, 'maj'),
    'pres22t1': ('Presidente 2022 (1º turno)', 'Presidente 2022 1ºT', 'Presidente', 2022, 'maj'),
    'pres22t2': ('Presidente 2022 (2º turno)', 'Presidente 2022 2ºT', 'Presidente', 2022, 'maj'),
    'ver24': ('Vereador 2024', 'Vereador 2024', 'Vereador', 2024, 'prop'),
    'pref24': ('Prefeito 2024', 'Prefeito 2024', 'Prefeito', 2024, 'maj'),
    'pref24t2': ('Prefeito 2024 (2º turno)', 'Prefeito 2024 2ºT', 'Prefeito', 2024, 'maj'),
    'de26': ('Deputado Estadual 2026', 'Dep. Estadual 2026', 'Deputado Estadual', 2026, 'prop'),
    'df26': ('Deputado Federal 2026', 'Dep. Federal 2026', 'Deputado Federal', 2026, 'prop'),
    'dd26': ('Deputado Distrital 2026', 'Dep. Distrital 2026', 'Deputado Distrital', 2026, 'prop'),
    'sen26': ('Senador 2026', 'Senador 2026', 'Senador', 2026, 'maj'),
    'gov26': ('Governador 2026', 'Governador 2026', 'Governador', 2026, 'maj'),
    'pres26t1': ('Presidente 2026 (1º turno)', 'Presidente 2026 1ºT', 'Presidente', 2026, 'maj')}
ABREV = {'Vereador': 'Ver', 'Prefeito': 'Pref', 'Deputado Estadual': 'DE', 'Deputado Federal': 'DF', 'Deputado Distrital': 'DD', 'Senador': 'Sen', 'Governador': 'Gov', 'Presidente': 'Pres'}


def bonito(nome):
    palavras = nome.title().split(' ')
    return ' '.join(p.lower() if (i > 0 and p in PARTICULAS) else p for i, p in enumerate(palavras))


def pyval(v):
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return None if pd.isna(v) else round(float(v), 4)
    return v


def inteiro(n):
    return f'{int(round(n)):,}'.replace(',', '.')


def decimal(n, casas=1, sinal=False):
    t = f'{n:+.{casas}f}' if sinal else f'{n:.{casas}f}'
    return t.replace('.', ',').replace('-', '−')


def pct(a, b):
    return a / b * 100 if b else float('nan')


# ---------------------------------------------------------------- municípios
corr = pd.read_csv(D / 'correspondencia_tse_ibge.csv', dtype=str)
corr['cd_tse'] = corr.CD_MUNICIPIO.astype(int)
cen = pd.read_csv(D / 'centroides_ibge.csv', dtype={'CD_MUN': str})
base = corr.merge(cen[['CD_MUN', 'lat', 'lon']], left_on='CD_IBGE', right_on='CD_MUN', how='left').drop(columns='CD_MUN')
base['nome'] = base.NM_MUNICIPIO.map(bonito)
base['uf'] = base.SG_UF
base['regiao'] = base.uf.map(REGIAO)
# Boa Esperança do Norte (MT) foi desmembrada de Sorriso e só existe em 2026; os votos dos dois foram somados em Sorriso
base.loc[(base.nome == 'Sorriso') & (base.uf == 'MT'), 'nome'] = 'Sorriso (com Boa Esperança do Norte)'
base = base[['cd_tse', 'CD_IBGE', 'nome', 'uf', 'regiao', 'lat', 'lon']]


def montar_mun(cds):
    m = base[base.cd_tse.isin(cds)].sort_values(['uf', 'nome']).reset_index(drop=True)
    return m


def registro_mun(m):
    return [{'c': r.CD_IBGE, 'n': r.nome, 'u': r.uf, 'g': r.regiao, 'lat': pyval(r.lat), 'lon': pyval(r.lon)} for r in m.itertuples()]


def serie(df, cds, col):
    """Valores de uma coluna alinhados à lista de municípios (cds), com None onde não há linha."""
    s = df.set_index('cd_tse')[col].reindex(cds)
    return [None if pd.isna(v) else int(v) for v in s]


def bloco_disputa(ctx, did, cds):
    nome, curto, cargo, ano, tipo = DISPUTAS[did]
    g = ctx[ctx.disp == did]
    b = {'id': did, 'nome': nome, 'curto': curto, 'cargo': cargo, 'ano': ano, 'tipo': tipo,
         'ap': serie(g, cds, 'aptos'), 'cp': serie(g, cds, 'comparec'), 'br': serie(g, cds, 'brancos'),
         'nu': serie(g, cds, 'nulos'), 'va': serie(g, cds, 'validos')}
    if g.votos.sum() > 1.5 * g.comparec.sum():
        b['v2'] = 1  # cada eleitor tem dois votos (Senador 2026)
    return b


def pares(votos, cds):
    pos = {c: i for i, c in enumerate(cds)}
    return [[pos[int(c)], int(v)] for c, v in zip(votos.cd_tse, votos.votos) if int(c) in pos]


def jdump(obj, nome):
    (OUT / 'dados' / nome).write_text(json.dumps(obj, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')


def resumo_part(g):
    """Participação agregada de um conjunto de linhas de contexto."""
    return {'aptos': g.aptos.sum(), 'abst': pct(g.abst.sum(), g.aptos.sum()), 'brancos': pct(g.brancos.sum(), g.votos.sum()),
            'nulos': pct(g.nulos.sum(), g.votos.sum()), 'validos': g.validos.sum(), 'comparec': g.comparec.sum()}

