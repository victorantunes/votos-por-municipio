"""Extrai um ponto representativo (dentro do polígono) de cada município a partir da malha municipal 2022 do IBGE."""
import warnings
from pathlib import Path

import geopandas as gpd

warnings.filterwarnings('ignore')
ROOT = Path(__file__).resolve().parent.parent
# Baixe a malha em https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip
# e extraia em dados/malha_ibge/. O resultado (dados/centroides_ibge.csv) já está no repositório.
SHP = ROOT / 'dados' / 'malha_ibge' / 'BR_Municipios_2022.shp'
gdf = gpd.read_file(SHP, columns=['CD_MUN', 'NM_MUN', 'SIGLA_UF', 'AREA_KM2', 'geometry'])
pts = gdf.geometry.representative_point()
out = gdf.drop(columns='geometry').copy()
out['lat'] = pts.y.round(5)
out['lon'] = pts.x.round(5)
out['CD_MUN'] = out['CD_MUN'].astype(str)
out.to_csv(ROOT / 'dados' / 'centroides_ibge.csv', index=False, encoding='utf-8')
print(out.shape)
print(out.head(3).to_string())
