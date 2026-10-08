"""Votos por seção eleitoral do RN, agrupados por local de votação e por bairro do IBGE.

Entradas
  dados/tse/csv/votacao_secao_<ano>_RN.csv             votos por candidato e seção (TSE)
  dados/tse/csv/votacao_secao_2022_RN_presidente.csv   Presidente de 2022 por seção (arquivo nacional filtrado pelo scripts/coletar_tse.py)
  dados/bu/bweb_1t_RN_*.zip                            boletins de urna de 2026 (Presidente por seção)
  dados/tse/csv/eleitorado_local_votacao_<ano>_RN.csv  locais de votação: bairro, coordenadas e eleitores por seção (TSE)
  dados/malha_ibge/BR_bairros_CD2022.shp               bairros do Censo 2022 (IBGE), que só existem para 19 municípios do RN
  dados/rn/candidaturas.csv                            candidaturas (scripts/preparar.py)
Saídas
  dados/rn/locais.csv           um local de votação por linha, em cada ano, com coordenadas, eleitores e bairro do IBGE
  dados/rn/contexto_local.csv   válidos, brancos, nulos e comparecimento de cada disputa em cada local
  dados/rn/votos_local.csv      votos de cada candidatura em cada local
  dados/rn/bairros.csv          bairros do IBGE usados (identificador, município, nome)
  docs/dados/bairros_rn.geojson polígonos simplificados dos bairros

Como um local entra no mapa
  1. o local de votação tem latitude e longitude no arquivo do TSE (97,5% válidas); os que não têm recebem a média dos locais do mesmo bairro
     (pelo nome do TSE) ou, se não houver, do município;
  2. se o município tem bairros no IBGE, o ponto é atribuído ao bairro que o contém ou, se cair fora de todos, ao mais próximo até 2 km;
  3. nos demais municípios o local fica como ponto.
"""
import json
import sys
import warnings
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preparar import CARGOS  # noqa: E402

warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent.parent
D = ROOT / 'dados'
TSE = D / 'tse' / 'csv'
ANOS = (2020, 2022, 2024, 2026)
BBOX = (-7.0, -4.8, -38.7, -34.9)  # lat mínima, lat máxima, lon mínima, lon máxima do RN
DISP = {k: v[0] for k, v in CARGOS.items()}
DISP.update({(2022, 'Presidente', '1'): 'pres22t1', (2022, 'Presidente', '2'): 'pres22t2', (2026, 'Presidente', '1'): 'pres26t1'})
DOIS_VOTOS = {'sen26': 'gov26', 'sen22': 'gov22'}  # no Senado de 2026 o eleitor dá dois votos: o comparecimento vem do governador
DIST_MAX = 2000  # metros para atribuir um local fora de todos os bairros ao bairro mais próximo do mesmo município
COLS = ['NR_TURNO', 'CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO', 'DS_CARGO', 'NR_VOTAVEL', 'SQ_CANDIDATO', 'QT_VOTOS']


def presidente_2026():
    """Presidente de 2026 por seção, a partir dos boletins de urna, no mesmo formato dos arquivos de votação por seção."""
    cache = TSE / 'bu_2026_RN_presidente_secao.csv'
    if cache.exists():
        return pd.read_csv(cache, sep=';', dtype=str)
    zip_bu = next((D / 'bu').glob('bweb_1t_RN_*.zip'), None)
    if zip_bu is None:
        raise SystemExit('faltam os boletins de urna do RN: rode scripts/coletar_bu_2026.py')
    z = zipfile.ZipFile(zip_bu)
    usar = ['CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO', 'DS_CARGO_PERGUNTA', 'DS_TIPO_VOTAVEL', 'NR_VOTAVEL', 'QT_VOTOS']
    with z.open(next(n for n in z.namelist() if n.endswith('.csv'))) as f:
        partes = [c[c.DS_CARGO_PERGUNTA == 'Presidente'] for c in pd.read_csv(f, sep=';', encoding='latin-1', dtype=str, usecols=usar, chunksize=400000)]
    b = pd.concat(partes)
    saida = pd.DataFrame({'NR_TURNO': '1', 'CD_MUNICIPIO': b.CD_MUNICIPIO, 'NR_ZONA': b.NR_ZONA, 'NR_SECAO': b.NR_SECAO, 'DS_CARGO': 'Presidente',
                          'NR_VOTAVEL': np.where(b.DS_TIPO_VOTAVEL == 'Branco', '95', np.where(b.DS_TIPO_VOTAVEL == 'Nulo', '96', b.NR_VOTAVEL)),
                          'SQ_CANDIDATO': np.where(b.DS_TIPO_VOTAVEL.isin(['Branco', 'Nulo']), '-1', '1'), 'QT_VOTOS': b.QT_VOTOS})
    saida.to_csv(cache, sep=';', index=False)
    return saida


def votos_secao(ano):
    s = pd.read_csv(TSE / f'votacao_secao_{ano}_RN.csv', sep=';', encoding='latin-1', dtype=str, usecols=COLS)
    if ano == 2022:
        s = pd.concat([s, pd.read_csv(TSE / 'votacao_secao_2022_RN_presidente.csv', sep=';', encoding='latin-1', dtype=str, usecols=COLS)], ignore_index=True)
    if ano == 2026:
        s = pd.concat([s, presidente_2026()], ignore_index=True)
    s['cargo'] = s.DS_CARGO.str.title()
    s['disp'] = [DISP.get((ano, c, t)) for c, t in zip(s.cargo, s.NR_TURNO)]
    s = s[s.disp.notna()].copy()
    for c in ('CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO', 'QT_VOTOS'):
        s[c] = pd.to_numeric(s[c]).astype('int64')
    # branco e nulo têm SQ -1 (números 95 e 96); o voto de legenda tem SQ -3; o resto é candidato
    s['tipo'] = np.select([(s.SQ_CANDIDATO == '-1') & (s.NR_VOTAVEL == '95'), (s.SQ_CANDIDATO == '-1') & (s.NR_VOTAVEL == '96'), s.SQ_CANDIDATO == '-3'],
                          ['branco', 'nulo', 'legenda'], default='candidato')
    return s


def locais_do_ano(ano, bairros):
    l = pd.read_csv(TSE / f'eleitorado_local_votacao_{ano}_RN.csv', sep=';', encoding='latin-1', dtype=str)
    l = l[l.NR_TURNO == '1'].copy()
    for c in ('CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO', 'NR_LOCAL_VOTACAO'):
        l[c] = pd.to_numeric(l[c]).astype('int64')
    l['ele'] = pd.to_numeric(l.QT_ELEITOR_SECAO, errors='coerce').fillna(0).astype(int)
    l['lat'] = pd.to_numeric(l.NR_LATITUDE.str.replace(',', '.'), errors='coerce')  # em 2026 o separador decimal é a vírgula
    l['lon'] = pd.to_numeric(l.NR_LONGITUDE.str.replace(',', '.'), errors='coerce')
    ok = l.lat.between(BBOX[0], BBOX[1]) & l.lon.between(BBOX[2], BBOX[3])
    l.loc[~ok, ['lat', 'lon']] = np.nan
    chave = ['CD_MUNICIPIO', 'NR_ZONA', 'NR_LOCAL_VOTACAO']
    secoes = l.drop_duplicates(['CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO'])[['CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO', 'NR_LOCAL_VOTACAO']]
    g = l.groupby(chave).agg(nome=('NM_LOCAL_VOTACAO', 'first'), bairro_tse=('NM_BAIRRO', 'first'), lat=('lat', 'mean'), lon=('lon', 'mean'), aptos=('ele', 'sum')).reset_index()
    g['aprox'] = 0
    sem = g.lat.isna()
    if sem.any():  # sem coordenada: média do mesmo bairro (nome do TSE) e, depois, do município
        for nivel in (['CD_MUNICIPIO', 'bairro_tse'], ['CD_MUNICIPIO']):
            med = g.groupby(nivel)[['lat', 'lon']].transform('mean')
            falta = g.lat.isna() & med.lat.notna()
            g.loc[falta, ['lat', 'lon']] = med.loc[falta, ['lat', 'lon']]
            g.loc[falta, 'aprox'] = 1
    g = g.dropna(subset=['lat', 'lon']).sort_values(chave).reset_index(drop=True)
    g.insert(0, 'ano', ano)
    g['lid'] = np.arange(len(g))
    # bairro do IBGE: ponto dentro do polígono; senão, o mais próximo do mesmo município até DIST_MAX
    pts = gpd.GeoDataFrame(g[['lid', 'CD_MUNICIPIO']], geometry=gpd.points_from_xy(g.lon, g.lat), crs='EPSG:4326').to_crs(bairros.crs)
    j = gpd.sjoin(pts, bairros[['b', 'geometry']], how='left', predicate='within').drop_duplicates('lid').set_index('lid')
    g['bairro'] = g.lid.map(j.b).fillna(-1).astype(int)
    com_bairros = set(bairros.cd_tse)
    fora = g[(g.bairro < 0) & g.CD_MUNICIPIO.isin(com_bairros)]
    if len(fora):
        pm = pts.set_index('lid').loc[fora.lid].to_crs('EPSG:31984')
        bm = bairros.to_crs('EPSG:31984')
        for cd, grupo in pm.groupby('CD_MUNICIPIO'):
            cand = bm[bm.cd_tse == cd]
            for lid, ponto in grupo.geometry.items():
                dist = cand.geometry.distance(ponto)
                if dist.min() <= DIST_MAX:
                    g.loc[g.lid == lid, 'bairro'] = int(cand.loc[dist.idxmin(), 'b'])
                    g.loc[g.lid == lid, 'aprox'] = 1
    return g, secoes


def main():
    corr = pd.read_csv(D / 'correspondencia_tse_ibge.csv', dtype=str)
    corr['cd_tse'] = corr.CD_MUNICIPIO.astype(int)
    ibge_para_tse = dict(zip(corr.CD_IBGE, corr.cd_tse))
    # ---- bairros do IBGE no RN
    bg = gpd.read_file(D / 'malha_ibge' / 'BR_bairros_CD2022.shp')
    bg = bg[bg.CD_MUN.astype(str).str.startswith('24')].copy()
    bg['cd_tse'] = bg.CD_MUN.astype(str).map(ibge_para_tse)
    bg = bg.sort_values(['CD_MUN', 'NM_BAIRRO']).reset_index(drop=True)
    bg['b'] = np.arange(len(bg))
    print(f'bairros do IBGE no RN: {len(bg)} em {bg.CD_MUN.nunique()} municípios')

    cand = pd.read_csv(D / 'rn' / 'candidaturas.csv', dtype={'numero': str, 'sq': str}).fillna({'sq': ''})
    cand = cand[cand.anulados == 0]  # candidaturas com votos anulados depois da eleição ficam sem detalhe por local
    lula = cand[(cand.nome_urna == 'Lula') & cand.disp.str.startswith('pres')].set_index('disp').cid.to_dict()
    por_sq = cand[cand.sq != ''][['cid', 'disp', 'sq']]

    locais, contexto, votos = [], [], []
    for ano in ANOS:
        g, secoes = locais_do_ano(ano, bg)
        locais.append(g)
        s = votos_secao(ano)
        chave = ['CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO']
        s = s.merge(secoes, on=chave, how='left')
        sem_local = s.NR_LOCAL_VOTACAO.isna()
        print(f'{ano}: {len(g)} locais, {len(s):,} linhas de votos, {sem_local.sum()} sem local ({sem_local.mean() * 100:.2f}%), {int((g.aprox == 1).sum())} locais com coordenada estimada')
        s = s[~sem_local].copy()
        s['NR_LOCAL_VOTACAO'] = s.NR_LOCAL_VOTACAO.astype('int64')
        s = s.merge(g[['CD_MUNICIPIO', 'NR_ZONA', 'NR_LOCAL_VOTACAO', 'lid']], on=['CD_MUNICIPIO', 'NR_ZONA', 'NR_LOCAL_VOTACAO'], how='inner')
        # contexto por disputa e local
        pv = s.pivot_table(index=['disp', 'lid'], columns='tipo', values='QT_VOTOS', aggfunc='sum', fill_value=0)
        for c in ('candidato', 'legenda', 'branco', 'nulo'):
            if c not in pv:
                pv[c] = 0
        ctx = pd.DataFrame({'va': pv.candidato + pv.legenda, 'br': pv.branco, 'nu': pv.nulo}).reset_index()
        ctx['cp'] = ctx.va + ctx.br + ctx.nu
        for dois, ref in DOIS_VOTOS.items():
            if dois in set(ctx.disp):
                base = ctx[ctx.disp == ref].set_index('lid').cp
                m = ctx.disp == dois
                ctx.loc[m, 'cp'] = ctx.loc[m, 'lid'].map(base).fillna(ctx.loc[m, 'cp'] / 2).values
        ctx.insert(0, 'ano', ano)
        contexto.append(ctx)
        # votos das candidaturas
        c1 = s[s.tipo == 'candidato'].merge(por_sq, left_on=['disp', 'SQ_CANDIDATO'], right_on=['disp', 'sq'])
        v1 = c1.groupby(['cid', 'lid']).QT_VOTOS.sum().reset_index()
        l1 = s[(s.tipo == 'candidato') & (s.cargo == 'Presidente') & (s.NR_VOTAVEL == '13')]
        l1 = l1.assign(cid=l1.disp.map(lula)).dropna(subset=['cid'])
        v2 = l1.groupby(['cid', 'lid']).QT_VOTOS.sum().reset_index()
        votos.append(pd.concat([v1, v2]).rename(columns={'QT_VOTOS': 'votos'}))

    loc = pd.concat(locais, ignore_index=True)
    ctx = pd.concat(contexto, ignore_index=True)
    vot = pd.concat(votos, ignore_index=True)
    vot = vot[vot.votos > 0]
    loc_out = loc.rename(columns={'CD_MUNICIPIO': 'cd_tse', 'NR_ZONA': 'zona', 'NR_LOCAL_VOTACAO': 'nr_local'})
    loc_out[['ano', 'lid', 'cd_tse', 'zona', 'nr_local', 'nome', 'bairro_tse', 'lat', 'lon', 'aptos', 'bairro', 'aprox']].round({'lat': 5, 'lon': 5}).to_csv(D / 'rn' / 'locais.csv', index=False)
    ctx.to_csv(D / 'rn' / 'contexto_local.csv', index=False)
    vot.sort_values(['cid', 'lid']).to_csv(D / 'rn' / 'votos_local.csv', index=False)
    bg[['b', 'cd_tse', 'NM_BAIRRO']].rename(columns={'NM_BAIRRO': 'nome'}).to_csv(D / 'rn' / 'bairros.csv', index=False)

    # ---- verificação: soma por seção contra o total de cada candidatura (município) e de cada disputa
    tot = cand.set_index('cid').tot
    soma = vot.groupby('cid').votos.sum()
    dif = (soma - tot.reindex(soma.index)).dropna()
    print(f'candidaturas com detalhe: {len(soma)} de {len(cand)}; diferença total vs soma por seção: {int((dif != 0).sum())} candidaturas, maior diferença {int(dif.abs().max())} votos')
    cm = pd.read_csv(D / 'rn' / 'contexto.csv')
    for disp, g in ctx.groupby('disp'):
        va_m = int(cm[cm.disp == disp].validos.sum())
        print(f'  {disp:9s} válidos por seção {int(g.va.sum()):>9,} | municipal {va_m:>9,} | diferença {(g.va.sum() / va_m - 1) * 100:+.2f}%')

    # ---- polígonos dos bairros, simplificados, para a página
    sim = shapely.coverage_simplify(bg.geometry.values, tolerance=0.0003)
    feats = []
    for r, geom in zip(bg.itertuples(), sim):
        geom = shapely.make_valid(shapely.set_precision(geom, 0.0001))
        if geom.is_empty:
            continue
        ponto = geom.representative_point()
        feats.append({'type': 'Feature', 'properties': {'c': f'b{r.b}', 'b': int(r.b), 'n': r.NM_BAIRRO, 'm': r.CD_MUN, 'cx': round(ponto.x, 4), 'cy': round(ponto.y, 4)},
                      'geometry': json.loads(shapely.to_geojson(geom))})
    alvo = ROOT / 'docs' / 'dados' / 'bairros_rn.geojson'
    alvo.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'bairros_rn.geojson: {len(feats)} feições, {alvo.stat().st_size / 1e3:.0f} kB')
    for ano, g in loc.groupby('ano'):
        print(f'  {ano}: locais em bairro do IBGE {int((g.bairro >= 0).sum())} de {len(g)} ({(g.bairro >= 0).mean() * 100:.1f}%), eleitores em bairro {g[g.bairro >= 0].aptos.sum() / g.aptos.sum() * 100:.1f}%')


if __name__ == '__main__':
    main()
