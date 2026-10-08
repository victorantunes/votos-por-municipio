"""Gera o site: dados dos dois recortes (Lula no Brasil e candidatos do PT no RN) e a página.

Entradas
  dados/br/contexto.csv, dados/br/lula.csv                       (scripts/preparar.py)
  dados/rn/{disputas,contexto,pessoas,candidaturas,votos}.csv    (scripts/preparar.py)
  dados/centroides_ibge.csv, dados/correspondencia_tse_ibge.csv
Saídas
  docs/dados/escopo_br.json, docs/dados/escopo_rn.json           dados lidos pela página
  docs/dados/*.csv                                               tabelas para baixar
  docs/index.html                                                página única (modelo em scripts/templates/app.html)
"""
import json
import re
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
PARTICULAS = {'De', 'Da', 'Do', 'Das', 'Dos', 'E'}
REPO = 'votos-por-municipio'  # nome do repositório no GitHub, usado nos links da página
CTX = ['aptos', 'comparec', 'abst', 'brancos', 'nulos', 'validos']

# nome completo, nome curto (listas e eixos) e tipo (maj = majoritária, prop = proporcional)
DISPUTAS = {
    'ver20': ('Vereador 2020', 'Vereador 2020', 'Vereador', 2020, 'prop'),
    'pref20': ('Prefeito 2020', 'Prefeito 2020', 'Prefeito', 2020, 'maj'),
    'de22': ('Deputado Estadual 2022', 'Dep. Estadual 2022', 'Deputado Estadual', 2022, 'prop'),
    'df22': ('Deputado Federal 2022', 'Dep. Federal 2022', 'Deputado Federal', 2022, 'prop'),
    'sen22': ('Senador 2022', 'Senador 2022', 'Senador', 2022, 'maj'),
    'gov22': ('Governador 2022', 'Governador 2022', 'Governador', 2022, 'maj'),
    'pres22t1': ('Presidente 2022 (1º turno)', 'Presidente 2022 1ºT', 'Presidente', 2022, 'maj'),
    'pres22t2': ('Presidente 2022 (2º turno)', 'Presidente 2022 2ºT', 'Presidente', 2022, 'maj'),
    'pres26t1': ('Presidente 2026 (1º turno)', 'Presidente 2026 1ºT', 'Presidente', 2026, 'maj'),
    'de26': ('Deputado Estadual 2026', 'Dep. Estadual 2026', 'Deputado Estadual', 2026, 'prop'),
    'df26': ('Deputado Federal 2026', 'Dep. Federal 2026', 'Deputado Federal', 2026, 'prop'),
    'sen26': ('Senador 2026', 'Senador 2026', 'Senador', 2026, 'maj'),
    'gov26': ('Governador 2026', 'Governador 2026', 'Governador', 2026, 'maj')}


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
qs = np.percentile(wide.var_pp, [15, 35, 50, 65, 85])
print('Quantis de var_pp:', qs.round(2).tolist(), '| sem coordenada:', int(wide.lat.isna().sum()))

# ================================================================ RN: candidatos do PT
ctx_rn = pd.read_csv(D / 'rn' / 'contexto.csv')
disp_rn = pd.read_csv(D / 'rn' / 'disputas.csv')
pess_rn = pd.read_csv(D / 'rn' / 'pessoas.csv')
cand_rn = pd.read_csv(D / 'rn' / 'candidaturas.csv', dtype={'numero': str}).fillna({'situacao': ''})
votos_rn = pd.read_csv(D / 'rn' / 'votos.csv')
mun_rn = montar_mun(set(ctx_rn.cd_tse))
cds_rn = [int(c) for c in mun_rn.cd_tse]
ORD_RN = list(disp_rn.id)
idx_d = {d: k for k, d in enumerate(ORD_RN)}
cand_rn['d'] = cand_rn.disp.map(idx_d)

# pessoas: o agregado do PT vem primeiro, depois as demais por votos
pess_rn['maior'] = pess_rn.pessoa.map(cand_rn.groupby('pessoa').tot.max())
pess_rn = pess_rn.sort_values('maior', ascending=False).reset_index(drop=True)
idx_p = {p: k + 1 for k, p in enumerate(pess_rn.pessoa)}  # 0 = PT (soma)
cands = []
por_pessoa = {0: []}
for r in cand_rn.sort_values(['pessoa', 'd']).itertuples():
    v = votos_rn[votos_rn.cid == r.cid]
    c = {'p': idx_p[r.pessoa], 'd': int(r.d), 'n': r.nome_urna, 'num': str(r.numero), 'par': r.partido, 'sit': r.situacao, 'tot': int(r.tot),
         'nm': int(r.nmun), 'rk': int(r.rk), 'nc': int(r.nc), 'ue': r.ue if r.disp in ('ver20', 'pref20') else '',
         'v': pares(v, cds_rn)}
    if r.anulados:
        c['an'] = int(r.anulados)
    cands.append(c)
# candidaturas do PT somadas, uma por disputa
pt = cand_rn[cand_rn.partido == 'PT']
soma = []
for d in ORD_RN:
    cs = pt[pt.disp == d]
    if cs.empty:
        continue
    v = votos_rn[votos_rn.cid.isin(cs.cid)].groupby('cd_tse', as_index=False).votos.sum()
    soma.append({'p': 0, 'd': idx_d[d], 'n': 'PT (soma)', 'num': '13', 'par': 'PT', 'sit': f"{len(cs)} candidato{'s' if len(cs) > 1 else ''}",
                 'tot': int(cs.tot.sum()), 'nm': int((v.votos > 0).sum()), 'npt': int(len(cs)), 'neleitos': int((cs.situacao == 'Eleito').sum()),
                 'agg': True, 'v': pares(v, cds_rn)})
cands = soma + cands
for k, c in enumerate(cands):
    por_pessoa.setdefault(c['p'], []).append(k)
pess = [{'n': 'PT (soma dos candidatos)', 'nc': 'Todos os candidatos do PT em cada disputa', 'ext': False, 'agg': True, 'c': por_pessoa[0]}]
for r in pess_rn.itertuples():
    pess.append({'n': r.nome_urna, 'nc': r.nome, 'ext': bool(r.externo), 'c': por_pessoa[idx_p[r.pessoa]]})
esc_rn = {'id': 'rn', 'mun': registro_mun(mun_rn), 'disp': [bloco_disputa(ctx_rn, d, cds_rn) for d in ORD_RN], 'pess': pess, 'cand': cands}
jdump(esc_rn, 'escopo_rn.json')

# ---- tabelas para baixar (RN)
nomes_mun = mun_rn.set_index('cd_tse').nome
nomes_disp = {d: DISPUTAS[d][0] for d in ORD_RN}
ctx_out = ctx_rn.assign(municipio=ctx_rn.cd_tse.map(nomes_mun), disputa=ctx_rn.disp.map(nomes_disp))
ctx_out['pct_abstencao'] = ctx_out.abst / ctx_out.aptos * 100
ctx_out['pct_brancos'] = ctx_out.brancos / ctx_out.votos * 100
ctx_out['pct_nulos'] = ctx_out.nulos / ctx_out.votos * 100
ctx_out = ctx_out.merge(mun_rn[['cd_tse', 'CD_IBGE']], on='cd_tse')
ctx_out[['disputa', 'CD_IBGE', 'cd_tse', 'municipio', 'aptos', 'comparec', 'votos', 'abst', 'brancos', 'nulos', 'validos', 'pct_abstencao', 'pct_brancos', 'pct_nulos']].rename(
    columns={'comparec': 'comparecimento', 'votos': 'votos_dados', 'abst': 'abstencoes', 'validos': 'votos_validos'}).round(4).to_csv(OUT / 'dados' / 'rn_participacao.csv', index=False, encoding='utf-8')
cand_pub = cand_rn.assign(disputa=cand_rn.disp.map(nomes_disp))[['cid', 'nome_urna', 'nome', 'numero', 'partido', 'disputa', 'ue', 'situacao', 'tot', 'nmun', 'rk', 'nc', 'anulados']].rename(
    columns={'cid': 'candidatura', 'nome_urna': 'nome_de_urna', 'nome': 'nome_completo', 'ue': 'circunscricao', 'situacao': 'situacao', 'tot': 'votos_validos', 'nmun': 'municipios_com_votos',
             'rk': 'posicao', 'nc': 'candidatos_na_disputa', 'anulados': 'votos_anulados'})
cand_pub.to_csv(OUT / 'dados' / 'rn_candidaturas.csv', index=False, encoding='utf-8')
vp = votos_rn.merge(cand_rn[['cid', 'nome_urna', 'disp']], on='cid').merge(mun_rn[['cd_tse', 'CD_IBGE', 'nome']], on='cd_tse')
vp['disputa'] = vp.disp.map(nomes_disp)
vp[['cid', 'nome_urna', 'disputa', 'CD_IBGE', 'cd_tse', 'nome', 'votos']].rename(
    columns={'cid': 'candidatura', 'nome_urna': 'nome_de_urna', 'nome': 'municipio'}).to_csv(OUT / 'dados' / 'rn_votos_por_municipio.csv', index=False, encoding='utf-8')

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


def linhas_part_rn():
    """Uma linha por disputa, só com os municípios em que o PT teve candidatos (todos, nas disputas de 2022)."""
    out = []
    for d in ORD_RN:
        cs = pt[pt.disp == d]
        munis = set(votos_rn[votos_rn.cid.isin(cs.cid)].cd_tse)
        g = ctx_rn[(ctx_rn.disp == d) & ctx_rn.cd_tse.isin(munis)]
        r = resumo_part(g)
        votos = int(cs.tot.sum())
        eleitos = int((cs.situacao == 'Eleito').sum()) if d != 'pres26t1' else None
        out.append(f"<tr><td>{DISPUTAS[d][0]}</td><td class='n'>{len(g)}</td><td class='n'>{inteiro(r['aptos'])}</td><td class='n'>{decimal(r['abst'], 1)}%</td><td class='n'>{decimal(r['brancos'], 1)}%</td>"
                   f"<td class='n'>{decimal(r['nulos'], 1)}%</td><td class='n'>{inteiro(r['validos'])}</td><td class='n'>{len(cs)}</td><td class='n'>{inteiro(votos)}</td>"
                   f"<td class='n'>{decimal(pct(votos, r['validos']), 1)}%</td><td class='n'>{'-' if eleitos is None else eleitos}</td></tr>")
    return chr(10).join(out)


por_regiao = wide.groupby('regiao').apply(resumo_lula).loc[['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul']]
flavio = pd.concat([pd.read_csv(f, dtype={'CD_MUNICIPIO': int}) for f in sorted((D / 'agg_2026').glob('agg_??.csv'))])
flavio = flavio[(flavio.SG_UF != 'ZZ') & (flavio.DS_TIPO_VOTAVEL == 'Nominal')]
flavio_pct = flavio[flavio.NR_VOTAVEL == 22].QT_VOTOS.sum() / flavio.QT_VOTOS.sum() * 100
n_pt_cand = int((~pt.disp.str.startswith('pres')).sum())
trocas = {
    '__Q_PP__': ', '.join(decimal(v, 2) for v in qs[:-1]) + ' e ' + decimal(qs[-1], 2), '__Q85__': decimal(qs[-1], 2),
    '__N_MUN__': inteiro(len(wide)), '__L22__': inteiro(nacional.lula_2022_2T), '__L26__': inteiro(nacional.lula_2026_1T),
    '__SALDO__': decimal(nacional.saldo / 1e6, 2, True) + ' mi', '__P22__': decimal(nacional.pct_2022_2T), '__P26__': decimal(nacional.pct_2026_1T),
    '__VARPP__': decimal(nacional.var_pp, 1, True), '__FLAVIO__': decimal(flavio_pct),
    '__TAB_REGIAO__': linhas_lula(por_regiao), '__TAB_UF__': linhas_lula(por_uf), '__TAB_PART_BR__': linhas_part_br(), '__TAB_PART_REG__': linhas_part_regiao(),
    '__TAB_PART_RN__': linhas_part_rn(), '__RN_NPESS__': inteiro(len(pess_rn) - 1), '__RN_NCAND__': inteiro(n_pt_cand), '__RN_NMUN__': inteiro(len(mun_rn)), '__REPO__': REPO}
idx = (ROOT / 'scripts' / 'templates' / 'app.html').read_text(encoding='utf-8')
for k, v in trocas.items():
    idx = idx.replace(k, v)
assert not re.search(r'__[A-Z0-9_]+__', idx), 'token sem substituição: ' + str(set(re.findall(r'__[A-Z0-9_]+__', idx)))
(OUT / 'index.html').write_text(idx, encoding='utf-8')
print('gerado', OUT / 'index.html', '| JSON:', {f: round((OUT / 'dados' / f).stat().st_size / 1e3) for f in ('escopo_br.json', 'escopo_rn.json')}, 'kB')
