"""Gera o site: dados dos recortes (Lula no Brasil e candidatos do PT em cada estado) e a página.

Entradas
  dados/br/contexto.csv, dados/br/lula.csv                       (scripts/preparar.py)
  dados/uf/<UF>/*.csv                                            (scripts/preparar_uf.py e scripts/secoes.py)
  dados/centroides_ibge.csv, dados/correspondencia_tse_ibge.csv
Saídas
  docs/dados/escopo_br.json, docs/dados/uf/<uf>.json             dados lidos pela página
  docs/dados/ufs.json, docs/dados/indice_pessoas.json            índices (estados e busca nacional de candidatos)
  docs/dados/granular/<uf>/, docs/dados/csv/                     detalhe por local de votação e tabelas para baixar
  docs/index.html                                                página única (modelo em scripts/templates/app.html)
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import *  # noqa: F401,F403,E402
from comum import BUILD, D, DISPUTAS, OUT, REPO, base, bloco_disputa, decimal, inteiro, jdump, montar_mun, pares, pct, pyval, registro_mun, resumo_part  # noqa: E402,F401
import gerar_ufs  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')

# ================================================================ Brasil: Lula
ctx_br = pd.read_csv(D / 'br' / 'contexto.csv')
lula = pd.read_csv(D / 'br' / 'lula.csv')
mun_br = montar_mun(set(ctx_br.cd_tse))
assert len(mun_br) == 5570
cds_br = [int(c) for c in mun_br.cd_tse]
ORD_BR = ['pres22t1', 'pres22t2', 'pres26t1']
esc_br = {'id': 'br', 'mun': registro_mun(mun_br), 'disp': [bloco_disputa(ctx_br, d, cds_br) for d in ORD_BR],
          'pess': [{'n': 'Lula', 'nc': 'Luiz Inácio Lula da Silva', 'ext': False, 'c': [0, 1, 2]}], 'cand': []}
for k, d in enumerate(ORD_BR):
    v = lula[lula.disp == d]
    tot = int(v.votos.sum())
    esc_br['cand'].append({'p': 0, 'd': k, 'n': 'Lula', 'num': '13', 'par': 'PT', 'sit': {'pres22t1': 'Foi ao 2º turno', 'pres22t2': 'Eleito', 'pres26t1': ''}[d],
                           'tot': tot, 'nm': int((v.votos > 0).sum()), 'v': pares(v, cds_br)})
jdump(esc_br, 'escopo_br.json')

# ---- tabela de resultados para baixar (Brasil)
wide = mun_br.copy()
SUF = {'pres22t1': '2022_1t', 'pres22t2': '2022_2t', 'pres26t1': '2026_1t'}
for d in ORD_BR:
    c = ctx_br[ctx_br.disp == d].set_index('cd_tse')
    w = pd.DataFrame({f'votos_{SUF[d]}': lula[lula.disp == d].set_index('cd_tse').votos, f'validos_{SUF[d]}': c.validos,
                      f'pct_{SUF[d]}': lula[lula.disp == d].set_index('cd_tse').votos / c.validos * 100,
                      f'aptos_{SUF[d]}': c.aptos, f'comparecimento_{SUF[d]}': c.comparec, f'abstencoes_{SUF[d]}': c.abst,
                      f'brancos_{SUF[d]}': c.brancos, f'nulos_{SUF[d]}': c.nulos,
                      f'pct_abstencao_{SUF[d]}': c.abst / c.aptos * 100, f'pct_brancos_{SUF[d]}': c.brancos / c.comparec * 100,
                      f'pct_nulos_{SUF[d]}': c.nulos / c.comparec * 100})
    wide = wide.merge(w, left_on='cd_tse', right_index=True, how='left')
wide['saldo'] = wide.votos_2026_1t - wide.votos_2022_2t
wide['var_pp'] = wide.pct_2026_1t - wide.pct_2022_2t
wide['ret_pct'] = (wide.votos_2026_1t / wide.votos_2022_2t - 1) * 100
cols = ['CD_IBGE', 'cd_tse', 'nome', 'uf', 'regiao'] + [c for c in wide.columns if c.endswith(('_2022_1t', '_2022_2t', '_2026_1t'))] + ['saldo', 'var_pp', 'ret_pct', 'lat', 'lon']
wide[cols].round(4).to_csv(OUT / 'dados' / 'resultado_municipios.csv', index=False, encoding='utf-8')


def resumo_lula(g):
    return pd.Series({
        'municipios': len(g), 'lula_2022_2T': g.votos_2022_2t.sum(), 'lula_2026_1T': g.votos_2026_1t.sum(),
        'saldo': g.votos_2026_1t.sum() - g.votos_2022_2t.sum(),
        'pct_2022_2T': g.votos_2022_2t.sum() / g.validos_2022_2t.sum() * 100, 'pct_2026_1T': g.votos_2026_1t.sum() / g.validos_2026_1t.sum() * 100,
        'var_pp': g.votos_2026_1t.sum() / g.validos_2026_1t.sum() * 100 - g.votos_2022_2t.sum() / g.validos_2022_2t.sum() * 100,
        'mediana_var_pp_municipios': g.var_pp.median(),
        'abstencao_2022_2T': g.abstencoes_2022_2t.sum() / g.aptos_2022_2t.sum() * 100, 'abstencao_2026_1T': g.abstencoes_2026_1t.sum() / g.aptos_2026_1t.sum() * 100})


por_uf = wide.groupby('uf').apply(resumo_lula).round(2)
por_uf.to_csv(OUT / 'dados' / 'resumo_uf.csv', encoding='utf-8')
nacional = resumo_lula(wide)
print('NACIONAL (soma dos municípios):'); print(nacional.round(2).to_string())
neg, pos = wide.var_pp[wide.var_pp < 0], wide.var_pp[wide.var_pp > 0]
corte_neg, corte_pos = np.percentile(neg, [100 / 3, 200 / 3]), np.percentile(pos, [100 / 3, 200 / 3])  # cortes da legenda: o zero separa quem caiu de quem subiu
print('Cortes de var_pp (queda | alta):', corte_neg.round(2).tolist(), corte_pos.round(2).tolist(), '| sem coordenada:', int(wide.lat.isna().sum()))


# ================================================================ candidatos do PT em cada estado
UFS_INFO = gerar_ufs.gerar()

# ================================================================ tabelas estáticas da página
def linhas_lula(tabela):
    out = []
    for nome, r in tabela.iterrows():
        out.append(f"<tr><td>{nome}</td><td class='n'>{inteiro(r.municipios)}</td><td class='n'>{inteiro(r.lula_2022_2T)}</td>"
                   f"<td class='n'>{inteiro(r.lula_2026_1T)}</td><td class='n'>{inteiro(r.saldo)}</td>"
                   f"<td class='n'>{decimal(r.pct_2022_2T)}%</td><td class='n'>{decimal(r.pct_2026_1T)}%</td>"
                   f"<td class='n'>{decimal(r.var_pp, 1, True)}</td></tr>")
    return '\n'.join(out)


def linhas_part_br():
    out = []
    for d in ORD_BR:
        g = ctx_br[ctx_br.disp == d]
        r = resumo_part(g)
        v = lula[lula.disp == d].votos.sum()
        out.append(f"<tr><td>{DISPUTAS[d][0]}</td><td class='n'>{inteiro(r['aptos'])}</td><td class='n'>{decimal(r['abst'], 2)}%</td><td class='n'>{decimal(r['brancos'], 2)}%</td>"
                   f"<td class='n'>{decimal(r['nulos'], 2)}%</td><td class='n'>{inteiro(r['validos'])}</td><td class='n'>{inteiro(v)}</td><td class='n'>{decimal(pct(v, r['validos']), 2)}%</td></tr>")
    return '\n'.join(out)


def linhas_part_regiao():
    out = []
    m = ctx_br.merge(base[['cd_tse', 'regiao']], on='cd_tse')
    for reg in ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']:
        cel = []
        for d in ('pres22t2', 'pres26t1'):
            r = resumo_part(m[(m.disp == d) & (m.regiao == reg)])
            cel += [decimal(r['abst'], 1) + '%', decimal(r['brancos'], 1) + '%', decimal(r['nulos'], 1) + '%']
        out.append(f"<tr><td>{reg}</td>" + ''.join(f"<td class='n'>{c}</td>" for c in cel) + '</tr>')
    return '\n'.join(out)


por_regiao = wide.groupby('regiao').apply(resumo_lula).loc[['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']]
flavio = pd.concat([pd.read_csv(f, dtype={'CD_MUNICIPIO': int}) for f in sorted((D / 'agg_2026').glob('agg_??.csv'))])
flavio = flavio[(flavio.SG_UF != 'ZZ') & (flavio.DS_TIPO_VOTAVEL == 'Nominal')]
flavio_pct = flavio[flavio.NR_VOTAVEL == 22].QT_VOTOS.sum() / flavio.QT_VOTOS.sum() * 100
trocas = {
    '__N_NEG__': inteiro(len(neg)), '__N_POS__': inteiro(len(pos)), '__CORTE_NEG__': ' e '.join(decimal(v, 2) for v in corte_neg), '__CORTE_POS__': ' e '.join(decimal(v, 2) for v in corte_pos),
    '__N_MUN__': inteiro(len(wide)), '__L22__': inteiro(nacional.lula_2022_2T), '__L26__': inteiro(nacional.lula_2026_1T),
    '__SALDO__': decimal(nacional.saldo / 1e6, 2, True) + ' mi', '__P22__': decimal(nacional.pct_2022_2T), '__P26__': decimal(nacional.pct_2026_1T),
    '__VARPP__': decimal(nacional.var_pp, 1, True), '__FLAVIO__': decimal(flavio_pct),
    '__TAB_REGIAO__': linhas_lula(por_regiao), '__TAB_UF__': linhas_lula(por_uf), '__TAB_PART_BR__': linhas_part_br(), '__TAB_PART_REG__': linhas_part_regiao(),
    '__REPO__': REPO, '__BUILD__': BUILD}
idx = (ROOT / 'scripts' / 'templates' / 'app.html').read_text(encoding='utf-8')
for k, v in trocas.items():
    idx = idx.replace(k, v)
assert not re.search(r'__[A-Z0-9_]+__', idx), 'token sem substituição: ' + str(set(re.findall(r'__[A-Z0-9_]+__', idx)))
(OUT / 'index.html').write_text(idx, encoding='utf-8')
tam = sum(f.stat().st_size for f in (OUT / 'dados').rglob('*') if f.is_file())
print('gerado', OUT / 'index.html', f'| docs/dados: {tam / 1e6:.0f} MB')
