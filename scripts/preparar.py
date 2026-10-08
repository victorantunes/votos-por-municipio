"""Organiza os dados do TSE em tabelas simples (uma linha por disputa, candidatura ou município).

Entradas
  dados/tse/csv/*.csv        RN de 2020, 2022, 2024 e 2026 e Presidente de 2022 (scripts/coletar_tse.py)
  dados/agg_2026/agg_*.csv   boletins de urna de 2026, Presidente, por município (scripts/coletar_bu_2026.py)
  dados/correspondencia_tse_ibge.csv
Saídas
  dados/br/contexto.csv, dados/br/lula.csv                       Lula no Brasil (2022 1º e 2º turnos, 2026 1º turno)
  dados/rn/disputas.csv, contexto.csv                            disputas do RN e participação (aptos, abstenção, brancos, nulos)
  dados/rn/pessoas.csv, candidaturas.csv, votos.csv              candidatos do PT no RN em 2020, 2022, 2024 e 2026 (e Lula)

Conceitos
  disputa      eleição de um cargo em um ano e turno (por exemplo, Governador 2022 ou Vereador 2020)
  candidatura  um candidato em uma disputa
  pessoa       o mesmo candidato ao longo das disputas (ligado pelo título de eleitor, que não é publicado)
  contexto     por município e disputa: aptos, comparecimento, abstenções, brancos, nulos e votos válidos
"""
import hashlib
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent.parent
D = ROOT / 'dados'
TSE = D / 'tse' / 'csv'
for sub in ('br', 'rn'):
    (D / sub).mkdir(exist_ok=True)

NOVO_MUN = 73709  # Boa Esperança do Norte (MT), criada a partir de Sorriso depois de 2022


def ler(nome):
    return pd.read_csv(TSE / nome, sep=';', encoding='latin-1', dtype=str)


def inteiro(s):
    return pd.to_numeric(s, errors='coerce').fillna(0).astype('int64')


def contexto(det, disp, filtro_chave='CD_MUNICIPIO'):
    """Soma as zonas de cada município. Abstenção = aptos - comparecimento. Nulos = tudo o que compareceu e não virou voto válido nem branco
    (inclui votos nulos, anulados depois da eleição e anulados sub judice)."""
    g = pd.DataFrame({
        'cd_tse': inteiro(det[filtro_chave]), 'aptos': inteiro(det.QT_APTOS), 'comparec': inteiro(det.QT_COMPARECIMENTO),
        'votos': inteiro(det.QT_VOTOS), 'brancos': inteiro(det.QT_VOTOS_BRANCOS), 'validos': inteiro(det.QT_TOTAL_VOTOS_VALIDOS)})
    g = g.groupby('cd_tse', as_index=False).sum()
    g['nulos'] = g.votos - g.brancos - g.validos  # votos = comparecimento, ou o dobro quando o eleitor tem dois votos (Senador 2026)
    g['abst'] = g.aptos - g.comparec  # eleitores de seções não instaladas entram como abstenção
    assert (g.nulos >= 0).all()
    g.insert(0, 'disp', disp)
    return g[['disp', 'cd_tse', 'aptos', 'comparec', 'votos', 'abst', 'brancos', 'nulos', 'validos']]


def ctx_2026(uf=None):
    """Contexto do 1º turno de 2026 a partir dos boletins de urna agregados."""
    arqs = sorted((D / 'agg_2026').glob('agg_??.csv'))
    agg = pd.concat([pd.read_csv(f, dtype={'CD_MUNICIPIO': int}) for f in arqs], ignore_index=True)
    agg = agg[agg.SG_UF != 'ZZ']
    if uf:
        agg = agg[agg.SG_UF == uf]
    base = agg.groupby('CD_MUNICIPIO')[['QT_APTOS', 'QT_COMPARECIMENTO']].first()
    tipo = agg.groupby(['CD_MUNICIPIO', 'DS_TIPO_VOTAVEL']).QT_VOTOS.sum().unstack(fill_value=0)
    out = pd.DataFrame({'aptos': base.QT_APTOS, 'comparec': base.QT_COMPARECIMENTO, 'brancos': tipo.get('Branco', 0),
                        'nulos': tipo.get('Nulo', 0), 'validos': tipo['Nominal']}).astype('int64')
    assert (out.validos + out.brancos + out.nulos == out.comparec).all(), 'boletins de urna: soma diferente do comparecimento'
    out['abst'] = out.aptos - out.comparec
    out['votos_dados'] = out.comparec
    lula = agg[(agg.DS_TIPO_VOTAVEL == 'Nominal') & (agg.NR_VOTAVEL == 13)].groupby('CD_MUNICIPIO').QT_VOTOS.sum().rename('votos')
    out = out.join(lula).fillna({'votos': 0}).astype('int64')
    return out


def anexar_sorriso(tab, cd_sorriso):
    """Soma Boa Esperança do Norte a Sorriso, para manter o território de 2022."""
    t = tab.rename(index={NOVO_MUN: cd_sorriso})
    return t.groupby(level=0).sum()


# ============================================================ Brasil: Lula
def brasil():
    cand = ler('votacao_candidato_munzona_2022_BR.csv')
    cand = cand[(cand.NR_CANDIDATO == '13') & (cand.SG_UF != 'ZZ')]
    det = ler('detalhe_votacao_munzona_2022_BR.csv')
    det = det[(det.DS_CARGO == 'Presidente') & (det.SG_UF != 'ZZ')]
    ctx, lula = [], []
    for turno in ('1', '2'):
        disp = f'pres22t{turno}'
        c = contexto(det[det.NR_TURNO == turno], disp)
        v = cand[cand.NR_TURNO == turno].assign(votos=lambda x: inteiro(x.QT_VOTOS_NOMINAIS_VALIDOS)).groupby(inteiro(cand[cand.NR_TURNO == turno].CD_MUNICIPIO)).votos.sum()
        lv = c[['cd_tse']].assign(disp=disp, votos=c.cd_tse.map(v).fillna(0).astype(int))
        assert len(c) == 5570, (disp, len(c))
        ctx.append(c)
        lula.append(lv[['disp', 'cd_tse', 'votos']])
    cd_sorriso = int(inteiro(det[(det.NM_MUNICIPIO == 'SORRISO') & (det.SG_UF == 'MT')].CD_MUNICIPIO).iloc[0])
    t26 = anexar_sorriso(ctx_2026(), cd_sorriso)
    assert len(t26) == 5570 and set(t26.index) == set(ctx[0].cd_tse), 'municípios de 2026 diferentes dos de 2022'
    c26 = t26.reset_index().rename(columns={'CD_MUNICIPIO': 'cd_tse'}).assign(disp='pres26t1')
    ctx.append(c26.assign(votos=c26.votos_dados)[['disp', 'cd_tse', 'aptos', 'comparec', 'votos', 'abst', 'brancos', 'nulos', 'validos']])
    lula.append(c26[['disp', 'cd_tse', 'votos']])
    ctx, lula = pd.concat(ctx, ignore_index=True), pd.concat(lula, ignore_index=True)
    ctx.to_csv(D / 'br' / 'contexto.csv', index=False)
    lula.to_csv(D / 'br' / 'lula.csv', index=False)
    for disp, g in ctx.groupby('disp'):
        v = lula[lula.disp == disp].votos.sum()
        print(f'{disp}: Lula {v:,} de {g.validos.sum():,} válidos ({v / g.validos.sum() * 100:.2f}%), abstenção {g.abst.sum() / g.aptos.sum() * 100:.2f}%, '
              f'brancos {g.brancos.sum() / g.comparec.sum() * 100:.2f}%, nulos {g.nulos.sum() / g.comparec.sum() * 100:.2f}%')


# ============================================================ RN: candidatos do PT
CARGOS = {  # (ano, DS_CARGO do TSE, turno) -> (id da disputa, cargo, tipo)
    (2022, 'Governador', '1'): ('gov22', 'Governador', 'maj'), (2022, 'Senador', '1'): ('sen22', 'Senador', 'maj'),
    (2022, 'Deputado Federal', '1'): ('df22', 'Deputado Federal', 'prop'), (2022, 'Deputado Estadual', '1'): ('de22', 'Deputado Estadual', 'prop'),
    (2020, 'Prefeito', '1'): ('pref20', 'Prefeito', 'maj'), (2020, 'Vereador', '1'): ('ver20', 'Vereador', 'prop'),
    (2024, 'Prefeito', '1'): ('pref24t1', 'Prefeito', 'maj'), (2024, 'Prefeito', '2'): ('pref24t2', 'Prefeito', 'maj'), (2024, 'Vereador', '1'): ('ver24', 'Vereador', 'prop'),
    (2026, 'Governador', '1'): ('gov26', 'Governador', 'maj'), (2026, 'Senador', '1'): ('sen26', 'Senador', 'maj'),
    (2026, 'Deputado Federal', '1'): ('df26', 'Deputado Federal', 'prop'), (2026, 'Deputado Estadual', '1'): ('de26', 'Deputado Estadual', 'prop')}
ORDEM_DISP = ['ver20', 'pref20', 'de22', 'df22', 'sen22', 'gov22', 'pres22t1', 'pres22t2', 'ver24', 'pref24t1', 'pref24t2', 'de26', 'df26', 'sen26', 'gov26', 'pres26t1']
NOMES_DISP = {'ver20': 'Vereador 2020', 'pref20': 'Prefeito 2020', 'de22': 'Deputado Estadual 2022', 'df22': 'Deputado Federal 2022',
              'sen22': 'Senador 2022', 'gov22': 'Governador 2022', 'pres22t1': 'Presidente 2022 (1º turno)',
              'pres22t2': 'Presidente 2022 (2º turno)', 'pres26t1': 'Presidente 2026 (1º turno)', 'de26': 'Deputado Estadual 2026',
              'df26': 'Deputado Federal 2026', 'ver24': 'Vereador 2024', 'pref24t1': 'Prefeito 2024 (1º turno)', 'pref24t2': 'Prefeito 2024 (2º turno)', 'sen26': 'Senador 2026', 'gov26': 'Governador 2026'}
SITUACAO = {'ELEITO': 'Eleito', 'ELEITO POR QP': 'Eleito', 'ELEITO POR MÉDIA': 'Eleito', 'SUPLENTE': 'Suplente', 'NÃO ELEITO': 'Não eleito',
            '2º TURNO': '2º turno'}


def titulo(txt):
    part = {'De', 'Da', 'Do', 'Das', 'Dos', 'E'}
    p = str(txt).strip().title().split(' ')
    return ' '.join(w.lower() if (i > 0 and w in part) else w for i, w in enumerate(p))


def rn():
    cad = {}
    votos_all = {}
    for ano in (2020, 2022, 2024, 2026):
        c = ler(f'consulta_cand_{ano}_RN.csv')
        c['ano'] = ano
        cad[ano] = c
        v = ler(f'votacao_candidato_munzona_{ano}_RN.csv')
        v['ano'] = ano
        votos_all[ano] = v
    cons = pd.concat(cad.values(), ignore_index=True)
    # o TSE esconde o CPF a partir de 2024, então as pessoas são ligadas pelo título de eleitor (que coincide com o CPF onde os dois existem)
    cons['chave'] = cons.NR_TITULO_ELEITORAL_CANDIDATO.where(cons.NR_TITULO_ELEITORAL_CANDIDATO.str.len() == 12, 'sq' + cons.SQ_CANDIDATO)
    vot = pd.concat(votos_all.values(), ignore_index=True)
    vot['v'] = inteiro(vot.QT_VOTOS_NOMINAIS_VALIDOS)
    vot['v_total'] = inteiro(vot.QT_VOTOS_NOMINAIS)
    vot['cd_tse'] = inteiro(vot.CD_MUNICIPIO)
    chaves = vot.apply(lambda r: CARGOS.get((r.ano, r.DS_CARGO, r.NR_TURNO)), axis=1)
    vot = vot[chaves.notna()].copy()
    vot['disp'] = chaves[chaves.notna()].map(lambda t: t[0])

    # --- somente candidatos com votos próprios (vices e suplentes não têm)
    por_cand = vot.groupby(['disp', 'SQ_CANDIDATO']).agg(tot=('v', 'sum'), tot_bruto=('v_total', 'sum')).reset_index()
    nmun = vot[vot.v > 0].groupby(['disp', 'SQ_CANDIDATO']).cd_tse.nunique().rename('nmun')
    por_cand = por_cand.merge(nmun, on=['disp', 'SQ_CANDIDATO'], how='left').fillna({'nmun': 0})
    info = cons.drop_duplicates('SQ_CANDIDATO').set_index('SQ_CANDIDATO')
    por_cand = por_cand.join(info[['chave', 'NM_CANDIDATO', 'NM_URNA_CANDIDATO', 'NR_CANDIDATO', 'SG_PARTIDO', 'DS_SIT_TOT_TURNO', 'NM_UE', 'SG_UE']], on='SQ_CANDIDATO')
    assert por_cand.chave.notna().all()

    # --- pessoas: quem foi candidato pelo PT em 2020, 2022 ou 2026
    chaves_pt = set(por_cand[por_cand.SG_PARTIDO == 'PT'].chave)
    por_cand = por_cand[por_cand.chave.isin(chaves_pt)].copy()
    ordem = sorted(por_cand.chave.unique(), key=lambda c: hashlib.sha1(c.encode()).hexdigest())
    ids = {c: f'p{n:04d}' for n, c in enumerate(ordem, 1)}
    por_cand['pessoa'] = por_cand.chave.map(ids)

    # --- posição na disputa (entre todos os candidatos do mesmo cargo e da mesma circunscrição)
    todos = vot.groupby(['disp', 'SG_UE', 'SQ_CANDIDATO']).v.sum().reset_index()
    todos['rk'] = todos.groupby(['disp', 'SG_UE']).v.rank(method='min', ascending=False).astype(int)
    todos['nc'] = todos.groupby(['disp', 'SG_UE']).v.transform('size')
    por_cand = por_cand.merge(todos[['disp', 'SQ_CANDIDATO', 'rk', 'nc']], on=['disp', 'SQ_CANDIDATO'], how='left')
    por_cand['situacao'] = por_cand.DS_SIT_TOT_TURNO.map(lambda s: SITUACAO.get(s, titulo(s)))
    por_cand['nome_urna'] = por_cand.NM_URNA_CANDIDATO.map(titulo)
    por_cand['nome'] = por_cand.NM_CANDIDATO.map(titulo)
    por_cand['anulados'] = por_cand.tot_bruto - por_cand.tot
    por_cand['ue'] = por_cand.NM_UE.map(titulo)
    por_cand['cid'] = [f'c{n:04d}' for n in range(1, len(por_cand) + 1)]

    # --- votos por município das candidaturas
    vot2 = vot.merge(por_cand[['SQ_CANDIDATO', 'disp', 'cid']], on=['SQ_CANDIDATO', 'disp'])
    votos = vot2.groupby(['cid', 'cd_tse']).v.sum().reset_index().rename(columns={'v': 'votos'})

    # --- contexto das disputas do RN
    ctx = []
    det22 = ler('detalhe_votacao_munzona_2022_RN.csv')
    det20 = ler('detalhe_votacao_munzona_2020_RN.csv')
    det26 = ler('detalhe_votacao_munzona_2026_RN.csv')
    det24 = ler('detalhe_votacao_munzona_2024_RN.csv')
    for (ano, cargo, turno), (disp, _, _) in CARGOS.items():
        det = {2020: det20, 2022: det22, 2024: det24, 2026: det26}[ano]
        det = det[(det.DS_CARGO == cargo) & (det.NR_TURNO == turno)]
        if disp in set(por_cand.disp) and len(det):
            ctx.append(contexto(det, disp))
    # presidente 2022 (RN) e 2026
    brd = ler('detalhe_votacao_munzona_2022_BR.csv')
    brd = brd[(brd.DS_CARGO == 'Presidente') & (brd.SG_UF == 'RN')]
    brv_all = ler('votacao_candidato_munzona_2022_BR.csv')
    brv_all = brv_all[brv_all.SG_UF == 'RN']
    extras = []
    for turno in ('1', '2'):
        disp = f'pres22t{turno}'
        ctx.append(contexto(brd[brd.NR_TURNO == turno], disp))
        v = brv_all[brv_all.NR_TURNO == turno].assign(votos=lambda x: inteiro(x.QT_VOTOS_NOMINAIS_VALIDOS))
        por_nr = v.groupby('NR_CANDIDATO').votos.sum().sort_values(ascending=False)
        lula = v[v.NR_CANDIDATO == '13'].groupby(inteiro(v[v.NR_CANDIDATO == '13'].CD_MUNICIPIO)).votos.sum()
        extras.append((disp, lula, int(list(por_nr.index).index('13') + 1), len(por_nr), {'1': 'Foi ao 2º turno', '2': 'Eleito'}[turno]))
    t26 = ctx_2026('RN')
    c26 = t26.reset_index().rename(columns={'CD_MUNICIPIO': 'cd_tse'}).assign(disp='pres26t1')
    ctx.append(c26.assign(votos=c26.votos_dados)[['disp', 'cd_tse', 'aptos', 'comparec', 'votos', 'abst', 'brancos', 'nulos', 'validos']])
    agg26 = pd.concat([pd.read_csv(D / 'agg_2026' / 'agg_RN.csv')])
    nom26 = agg26[agg26.DS_TIPO_VOTAVEL == 'Nominal'].groupby('NR_VOTAVEL').QT_VOTOS.sum().sort_values(ascending=False)
    extras.append(('pres26t1', t26.votos.rename_axis('cd_tse'), int(list(nom26.index).index(13) + 1), len(nom26), ''))
    ctx = pd.concat(ctx, ignore_index=True)

    # --- Lula como pessoa, com as três disputas presidenciais (votos no RN)
    pid_lula = f'p{len(ids) + 1:04d}'
    novas_c, novos_v = [], []
    for disp, serie, rk, nc, sit in extras:
        cid = f'c{len(por_cand) + len(novas_c) + 1:04d}'
        novas_c.append({'cid': cid, 'pessoa': pid_lula, 'disp': disp, 'nome_urna': 'Lula', 'nome': 'Luiz Inácio Lula da Silva', 'NR_CANDIDATO': '13',
                        'SG_PARTIDO': 'PT', 'situacao': sit, 'tot': int(serie.sum()), 'nmun': int((serie > 0).sum()), 'rk': rk, 'nc': nc,
                        'anulados': 0, 'ue': 'Rio Grande do Norte'})
        novos_v.append(serie.rename('votos').rename_axis('cd_tse').reset_index().assign(cid=cid))
    por_cand = pd.concat([por_cand, pd.DataFrame(novas_c)], ignore_index=True)
    votos = pd.concat([votos] + [v[['cid', 'cd_tse', 'votos']] for v in novos_v], ignore_index=True)

    por_cand['ano'] = 2000 + por_cand.disp.str.extract(r'(\d\d)')[0].astype(int)
    # o nome da pessoa é o da candidatura mais recente
    pess = por_cand.sort_values(['ano', 'cid']).groupby('pessoa').agg(nome=('nome', 'last'), nome_urna=('nome_urna', 'last')).reset_index()
    pess['externo'] = pess.pessoa == pid_lula
    por_cand = por_cand.rename(columns={'NR_CANDIDATO': 'numero', 'SG_PARTIDO': 'partido'})
    por_cand['situacao'] = por_cand.situacao.fillna('')
    for c in ('tot', 'nmun', 'rk', 'nc', 'anulados'):
        por_cand[c] = por_cand[c].astype(int)
    cols = ['cid', 'pessoa', 'disp', 'nome_urna', 'nome', 'numero', 'partido', 'situacao', 'tot', 'nmun', 'rk', 'nc', 'anulados', 'ue']
    por_cand[cols].to_csv(D / 'rn' / 'candidaturas.csv', index=False)
    pess[['pessoa', 'nome', 'nome_urna', 'externo']].to_csv(D / 'rn' / 'pessoas.csv', index=False)
    votos.sort_values(['cid', 'cd_tse']).to_csv(D / 'rn' / 'votos.csv', index=False)
    ctx.to_csv(D / 'rn' / 'contexto.csv', index=False)
    usadas = [d for d in ORDEM_DISP if d in set(ctx.disp)]
    pd.DataFrame({'id': usadas, 'nome': [NOMES_DISP[d] for d in usadas]}).to_csv(D / 'rn' / 'disputas.csv', index=False)

    print(f'\nRN: {len(pess)} pessoas, {len(por_cand)} candidaturas, {len(votos)} linhas de votos')
    print(por_cand.groupby(['disp', 'partido']).size().unstack(fill_value=0).loc[:, ['PT']] if 'PT' in set(por_cand.partido) else '')
    print(por_cand[por_cand.anulados > 0][['nome_urna', 'disp', 'partido', 'tot', 'anulados']].to_string())
    print(ctx.groupby('disp').agg(municipios=('cd_tse', 'nunique'), validos=('validos', 'sum'), brancos=('brancos', 'sum'), nulos=('nulos', 'sum')))


if __name__ == '__main__':
    brasil()
    rn()
