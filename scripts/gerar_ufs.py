"""Gera, para cada estado, o arquivo de dados da página (docs/dados/uf/<uf>.json), o detalhe por local de votação (docs/dados/granular/<uf>/),
as tabelas para baixar e os índices nacionais (estados e busca de candidatos).

Cada estado é um "escopo" com a mesma forma: municípios, disputas (com a participação do eleitorado), pessoas e candidaturas.
A pessoa que concorreu em mais de um estado aparece no escopo de cada um deles, com a lista das candidaturas dos outros em "fora".
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import ABREV, D, DISPUTAS, OUT, base, bloco_disputa, bonito, jdump, montar_mun, pares, registro_mun  # noqa: E402
from preparar import ORDEM_DISP  # noqa: E402
from preparar_uf import PARTIDO, UF_NOME, UFS  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
PROPRIA = ('Vereador', 'Prefeito')  # cargos cuja circunscrição é o município


def nomes_com_turno(blocos):
    """Quando o estado teve 2º turno de uma disputa, o 1º turno passa a se chamar "(1º turno)"."""
    ids = {b['id'] for b in blocos}
    for b in blocos:
        if (b['id'] + 't2') in ids:
            b['nome'] += ' (1º turno)'
            b['curto'] += ' 1ºT'
    return blocos


def construir(sg):
    """Monta o escopo de um estado. A referência às pessoas de outros estados (fora) é preenchida depois."""
    pasta = D / 'uf' / sg
    ctx = pd.read_csv(pasta / 'contexto.csv')
    disp = pd.read_csv(pasta / 'disputas.csv')
    pess_df = pd.read_csv(pasta / 'pessoas.csv')
    cand = pd.read_csv(pasta / 'candidaturas.csv', dtype={'numero': str, 'sq': str}).fillna({'situacao': '', 'sq': ''})
    votos = pd.read_csv(pasta / 'votos.csv')
    mun = montar_mun(set(base[base.uf == sg].cd_tse))
    cds = [int(c) for c in mun.cd_tse]
    ordem = [d for d in disp.id if d in DISPUTAS]
    idx_d = {d: k for k, d in enumerate(ordem)}
    cand = cand[cand.disp.isin(idx_d)].copy()
    cand['d'] = cand.disp.map(idx_d)
    pess_df['maior'] = pess_df.pessoa.map(cand.groupby('pessoa').tot.max())
    pess_df = pess_df.dropna(subset=['maior']).sort_values('maior', ascending=False).reset_index(drop=True)
    idx_p = {p: k + 1 for k, p in enumerate(pess_df.pessoa)}  # 0 = soma do partido
    votos_por_cid = {cid: g for cid, g in votos.groupby('cid')}
    cands, cid_ordem = [], []
    for r in cand.sort_values(['pessoa', 'd']).itertuples():
        v = votos_por_cid.get(r.cid, votos.iloc[0:0])
        c = {'p': idx_p[r.pessoa], 'd': int(r.d), 'n': r.nome_urna, 'num': str(r.numero), 'par': r.partido, 'sit': r.situacao, 'tot': int(r.tot),
             'nm': int(r.nmun), 'rk': int(r.rk), 'nc': int(r.nc), 'ue': r.ue if DISPUTAS[r.disp][2] in PROPRIA else '', 'v': pares(v, cds)}
        if r.anulados:
            c['an'] = int(r.anulados)
        cands.append(c)
        cid_ordem.append(r.cid)
    do_partido = cand[cand.partido == PARTIDO]
    soma = []
    for d in ordem:
        cs = do_partido[do_partido.disp == d]
        if cs.empty:
            continue
        v = votos[votos.cid.isin(cs.cid)].groupby('cd_tse', as_index=False).votos.sum()
        soma.append({'p': 0, 'd': idx_d[d], 'n': f'{PARTIDO} (soma)', 'num': '13', 'par': PARTIDO, 'sit': f"{len(cs)} candidato{'s' if len(cs) > 1 else ''}",
                     'tot': int(cs.tot.sum()), 'nm': int((v.votos > 0).sum()), 'npt': int(len(cs)), 'neleitos': int((cs.situacao == 'Eleito').sum()),
                     'agg': True, 'v': pares(v, cds)})
    cid_idx = {cid: len(soma) + i for i, cid in enumerate(cid_ordem)}
    cands = soma + cands
    por_pessoa = {0: []}
    for k, c in enumerate(cands):
        por_pessoa.setdefault(c['p'], []).append(k)
    pess = [{'n': f'{PARTIDO} (soma dos candidatos)', 'nc': f'Todos os candidatos do {PARTIDO} em cada disputa', 'ext': False, 'agg': True, 'c': por_pessoa[0]}]
    gids = [None]
    for r in pess_df.itertuples():
        pess.append({'n': r.nome_urna, 'nc': r.nome, 'ext': bool(r.externo), 'c': por_pessoa[idx_p[r.pessoa]]})
        gids.append(r.pessoa)
    blocos = nomes_com_turno([bloco_disputa(ctx, d, cds) for d in ordem])
    esc = {'id': sg.lower(), 'uf': sg, 'nome_uf': UF_NOME[sg], 'mun': registro_mun(mun), 'disp': blocos, 'pess': pess, 'cand': cands}
    return {'esc': esc, 'gids': gids, 'cand_df': cand, 'ctx': ctx, 'mun': mun, 'cds': cds, 'ordem': ordem, 'idx_d': idx_d, 'cid_idx': cid_idx, 'soma': soma,
            'do_partido': do_partido, 'votos': votos, 'cid_ordem': cid_ordem}


def granular(sg, est, bairros_ok):
    """Detalhe por local de votação (um arquivo por ano e um por disputa) para os estados em que já foi processado."""
    pasta = D / 'uf' / sg
    if not (pasta / 'locais.csv').exists():
        return False
    pasta_out = OUT / 'dados' / 'granular' / sg.lower()
    pasta_out.mkdir(parents=True, exist_ok=True)
    for f in pasta_out.glob('*.json'):
        f.unlink()
    loc = pd.read_csv(pasta / 'locais.csv')
    ctx_loc = pd.read_csv(pasta / 'contexto_local.csv')
    vot_loc = pd.read_csv(pasta / 'votos_local.csv')
    cds, ordem, idx_d, soma, cid_idx = est['cds'], est['ordem'], est['idx_d'], est['soma'], est['cid_idx']
    pos_mun = {c: i for i, c in enumerate(cds)}
    tam = {}
    for ano, g in loc.groupby('ano'):
        g = g.sort_values('lid')
        tam[int(ano)] = len(g)
        grade = {'n': len(g), 'lat': [round(v, 5) for v in g.lat], 'lon': [round(v, 5) for v in g.lon], 'nome': [bonito(n) for n in g.nome],
                 'bt': [bonito(str(n)) for n in g.bairro_tse], 'mi': [pos_mun[int(c)] for c in g.cd_tse], 'b': [int(v) for v in g.bairro], 'ap': [int(v) for v in g.aptos]}
        jdump(grade, f'granular/{sg.lower()}/grade_{int(ano)}.json')
    por_cid = {cid: g for cid, g in vot_loc.groupby('cid')}
    cids_pt = set(est['do_partido'].cid)
    cand = est['cand_df']
    for did in ordem:
        ano = DISPUTAS[did][3]
        if ano not in tam:
            continue
        n = tam[ano]
        cl = ctx_loc[ctx_loc.disp == did]
        blocos = {}
        for chave in ('va', 'br', 'nu', 'cp'):
            arr = [None] * n
            for lid, v in zip(cl.lid, cl[chave]):
                arr[int(lid)] = int(v)
            blocos[chave] = arr
        candidaturas = {}
        da_disp = cand[cand.disp == did]
        for cid in da_disp.cid:
            v = por_cid.get(cid)
            if v is not None and cid in cid_idx:
                candidaturas[cid_idx[cid]] = [[int(a), int(b)] for a, b in zip(v.lid, v.votos)]
        pts = [por_cid[c] for c in da_disp.cid if c in cids_pt and c in por_cid]
        if pts:
            soma_pt = pd.concat(pts).groupby('lid').votos.sum()
            idx_soma = next(k for k, c in enumerate(soma) if c['d'] == idx_d[did])
            candidaturas[idx_soma] = [[int(a), int(b)] for a, b in soma_pt.items()]
        jdump({**blocos, 'c': candidaturas}, f'granular/{sg.lower()}/disp_{did}.json')
    return True


def tabelas_para_baixar(sg, est):
    mun, ctx, cand = est['mun'], est['ctx'], est['cand_df']
    nomes_disp = {d: DISPUTAS[d][0] for d in est['ordem']}
    csv = OUT / 'dados' / 'csv'
    csv.mkdir(parents=True, exist_ok=True)
    c = ctx.assign(municipio=ctx.cd_tse.map(mun.set_index('cd_tse').nome), disputa=ctx.disp.map(nomes_disp))
    c['pct_abstencao'] = c.abst / c.aptos * 100
    c['pct_brancos'] = c.brancos / c.votos * 100
    c['pct_nulos'] = c.nulos / c.votos * 100
    c = c.merge(mun[['cd_tse', 'CD_IBGE']], on='cd_tse')
    c[['disputa', 'CD_IBGE', 'cd_tse', 'municipio', 'aptos', 'comparec', 'votos', 'abst', 'brancos', 'nulos', 'validos', 'pct_abstencao', 'pct_brancos', 'pct_nulos']].rename(
        columns={'comparec': 'comparecimento', 'votos': 'votos_dados', 'abst': 'abstencoes', 'validos': 'votos_validos'}).round(4).to_csv(csv / f'{sg.lower()}_participacao.csv', index=False, encoding='utf-8')
    cand.assign(disputa=cand.disp.map(nomes_disp))[['cid', 'nome_urna', 'nome', 'numero', 'partido', 'disputa', 'ue', 'situacao', 'tot', 'nmun', 'rk', 'nc', 'anulados']].rename(
        columns={'cid': 'candidatura', 'nome_urna': 'nome_de_urna', 'nome': 'nome_completo', 'ue': 'circunscricao', 'tot': 'votos_validos', 'nmun': 'municipios_com_votos',
                 'rk': 'posicao', 'nc': 'candidatos_na_disputa', 'anulados': 'votos_anulados'}).to_csv(csv / f'{sg.lower()}_candidaturas.csv', index=False, encoding='utf-8')


def bairros_do_estado(sg, est):
    """Quantos municípios do estado têm bairros do IBGE e que parte do eleitorado eles reúnem (arquivo gerado por secoes.py)."""
    arq = OUT / 'dados' / 'bairros' / f'{sg.lower()}.geojson'
    if not arq.exists():
        return 0, 0
    com = {f['properties']['m'] for f in json.loads(arq.read_text(encoding='utf-8'))['features']}
    ctx, mun, ordem = est['ctx'], est['mun'], est['ordem']
    d0 = 'pres22t1' if 'pres22t1' in ordem else ordem[0]
    ap = ctx[ctx.disp == d0].groupby('cd_tse').aptos.sum()
    ibge = dict(zip(mun.cd_tse.astype(int), mun.CD_IBGE.astype(str)))
    dentro = [c for c in ap.index if ibge.get(int(c)) in com]
    return len(com), int(round(ap[dentro].sum() / ap.sum() * 100))


def gerar():
    ufs = [u for u in UFS if (D / 'uf' / u / 'candidaturas.csv').exists()]
    (OUT / 'dados' / 'uf').mkdir(parents=True, exist_ok=True)
    estados = {sg: construir(sg) for sg in ufs}
    # pessoas que concorreram em mais de um estado: cada escopo lista as candidaturas dos outros
    onde = {}
    for sg, est in estados.items():
        for i, g in enumerate(est['gids']):
            if g is not None and not est['esc']['pess'][i]['ext']:
                onde.setdefault(g, []).append((sg, i))
    multi = 0
    for sg, est in estados.items():
        for i, g in enumerate(est['gids']):
            if g is None or est['esc']['pess'][i]['ext'] or len(onde[g]) < 2:
                continue
            fora = []
            for (u, j) in onde[g]:
                if u == sg:
                    continue
                o = estados[u]['esc']
                cs = [[o['disp'][o['cand'][k]['d']]['nome'], o['cand'][k]['par'], o['cand'][k]['tot'], o['cand'][k]['sit'], o['cand'][k]['ue']] for k in o['pess'][j]['c']]
                fora.append({'u': u, 'i': j, 'c': cs})
            est['esc']['pess'][i]['fora'] = fora
            multi += 1
    indice, info = [], []
    for sg, est in estados.items():
        esc = est['esc']
        jdump(esc, f'uf/{sg.lower()}.json')
        tabelas_para_baixar(sg, est)
        tem_gran = granular(sg, est, False)
        nb, pb = bairros_do_estado(sg, est)
        for i, p in enumerate(esc['pess']):
            if i == 0 or p['ext']:
                continue
            resumo = ' '.join(f"{ABREV[esc['disp'][esc['cand'][k]['d']]['cargo']]}{str(esc['disp'][esc['cand'][k]['d']]['ano'])[2:]}" for k in p['c'])
            indice.append([p['n'], len(info), i, resumo])
        info.append({'sg': sg, 'id': sg.lower(), 'nome': UF_NOME[sg], 'municipios': len(esc['mun']), 'pessoas': len(esc['pess']) - 1,
                     'candidaturas': sum(1 for c in esc['cand'] if not c.get('agg')), 'granular': tem_gran, 'bairros': nb > 0, 'bairros_n': nb, 'bairros_pct': pb})
    jdump({'ufs': info}, 'ufs.json')
    jdump({'ufs': [i['sg'] for i in info], 'p': sorted(indice, key=lambda r: r[0])}, 'indice_pessoas.json')
    print(f'{len(info)} estados; {len(indice):,} pessoas no índice; {multi} pessoas com candidaturas em mais de um estado (contadas por estado)')
    return info
