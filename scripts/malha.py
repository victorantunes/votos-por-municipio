"""Gera a malha simplificada dos municípios (e das UFs) para o modo "polígonos" do mapa.

Entrada : malha municipal 2022 do IBGE (BR_Municipios_2022.shp)
Saída   : docs/dados/municipios.geojson e docs/dados/ufs.geojson

A simplificação preserva as fronteiras compartilhadas entre vizinhos (shapely.coverage_simplify),
então não surgem frestas nem sobreposições entre municípios.
"""
import json
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import pandas as pd
import shapely

warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent.parent
CANDIDATOS = [ROOT / 'dados' / 'malha_ibge' / 'BR_Municipios_2022.shp',
              Path('F:/workspace/mbx/tcc/data/external/municipios_2022/BR_Municipios_2022.shp')]
SHP = next(p for p in CANDIDATOS if p.exists())
TOL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.01    # graus (cerca de 1,1 km)
CASAS = 3                                                     # 0,001 grau, cerca de 110 m

res = pd.read_csv(ROOT / 'docs' / 'dados' / 'resultado_municipios.csv', dtype={'CD_IBGE': str})
codigos = set(res.CD_IBGE)
gdf = gpd.read_file(SHP, columns=['CD_MUN', 'SIGLA_UF', 'geometry'])
gdf['CD_MUN'] = gdf['CD_MUN'].astype(str)
gdf = gdf[gdf.CD_MUN.isin(codigos)].reset_index(drop=True)
print('municípios na malha:', len(gdf), 'de', len(codigos))

simp = shapely.coverage_simplify(gdf.geometry.values, tolerance=TOL)
gdf['geometry'] = simp
print('geometrias válidas após simplificar:', int(shapely.is_valid(simp).sum()), 'de', len(simp))


def arred(coords):
    out = []
    for x, y in coords:
        p = (round(x, CASAS), round(y, CASAS))
        if not out or out[-1] != p:
            out.append(p)
    return out


def anel(coords):
    pts = arred(coords)
    return [list(p) for p in pts] if len(pts) >= 4 else None


def geojson(geom):
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    saida = []
    for pol in polys:
        rings = [anel(pol.exterior.coords)] + [anel(r.coords) for r in pol.interiors]
        rings = [r for r in rings if r]
        if rings and rings[0]:
            saida.append(rings)
    if not saida:
        return None
    return {'type': 'Polygon', 'coordinates': saida[0]} if len(saida) == 1 else {'type': 'MultiPolygon', 'coordinates': saida}


feats = []
for cod, g in zip(gdf.CD_MUN, gdf.geometry):
    gj = geojson(g)
    if gj:
        feats.append({'type': 'Feature', 'properties': {'c': cod}, 'geometry': gj})
out = ROOT / 'docs' / 'dados' / 'municipios.geojson'
out.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('municipios.geojson:', len(feats), 'feições,', round(out.stat().st_size / 1e6, 2), 'MB')

ufs = []
for uf, g in gdf.groupby('SIGLA_UF'):
    u = shapely.union_all(g.geometry.values)
    gj = geojson(u)
    if gj:
        ufs.append({'type': 'Feature', 'properties': {'u': uf}, 'geometry': gj})
out2 = ROOT / 'docs' / 'dados' / 'ufs.geojson'
out2.write_text(json.dumps({'type': 'FeatureCollection', 'features': ufs}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('ufs.geojson:', len(ufs), 'feições,', round(out2.stat().st_size / 1e6, 2), 'MB')

# ---- Rio Grande do Norte com mais detalhe (recorte "PT no RN"), para o mapa aproximado no estado
TOL_RN = 0.002                                               # cerca de 220 m
rn = gdf[gdf.SIGLA_UF == 'RN'].copy()
bruto = gpd.read_file(SHP, columns=['CD_MUN', 'SIGLA_UF', 'geometry'])
bruto['CD_MUN'] = bruto['CD_MUN'].astype(str)
bruto = bruto[bruto.CD_MUN.isin(set(rn.CD_MUN))].reset_index(drop=True)
bruto['geometry'] = shapely.coverage_simplify(bruto.geometry.values, tolerance=TOL_RN)
feats_rn = [{'type': 'Feature', 'properties': {'c': cod}, 'geometry': geojson(g)} for cod, g in zip(bruto.CD_MUN, bruto.geometry)]
out3 = ROOT / 'docs' / 'dados' / 'municipios_rn.geojson'
out3.write_text(json.dumps({'type': 'FeatureCollection', 'features': feats_rn}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('municipios_rn.geojson:', len(feats_rn), 'feições,', round(out3.stat().st_size / 1e6, 2), 'MB')
uf_rn = {'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'u': 'RN'}, 'geometry': geojson(shapely.union_all(bruto.geometry.values))}]}
out4 = ROOT / 'docs' / 'dados' / 'uf_rn.geojson'
out4.write_text(json.dumps(uf_rn, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('uf_rn.geojson:', round(out4.stat().st_size / 1e6, 3), 'MB')
