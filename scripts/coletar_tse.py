"""Baixa do TSE os resultados de 2020, 2022, 2024 e 2026 e extrai os arquivos usados na análise.

Fonte: TSE, dados abertos (https://cdn.tse.jus.br/estatistica/sead/odsele/).
Entradas baixadas (dados/tse/brutos/, ignoradas pelo git):
  votacao_candidato_munzona_<ano>.zip   votos de cada candidato por município e zona
  detalhe_votacao_munzona_<ano>.zip     aptos, comparecimento, abstenções, brancos, nulos e válidos por município e zona
  consulta_cand_<ano>.zip               cadastro dos candidatos (partido, cargo, situação, título de eleitor usado só para ligar os anos)
  votacao_secao_<ano>_RN.zip            votos de cada candidato em cada seção eleitoral (só RN)
  eleitorado_local_votacao_<ano>.zip    locais de votação, com bairro, coordenadas e eleitores por seção (Brasil; fica só o RN)
  BR_bairros_CD2022.zip                 bairros do Censo 2022 (IBGE), em dados/malha_ibge/
Saídas extraídas (dados/tse/csv/, ignoradas pelo git):
  RN de 2020, 2022, 2024 e 2026, e o arquivo BR (Presidente) de 2022.
"""
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent.parent
BRUTOS = ROOT / 'dados' / 'tse' / 'brutos'
CSV = ROOT / 'dados' / 'tse' / 'csv'
BASE = 'https://cdn.tse.jus.br/estatistica/sead/odsele'
UA = {'User-Agent': 'Mozilla/5.0'}

# (pasta no TSE, prefixo do arquivo, ano, arquivos que serão extraídos do zip)
PACOTES = [
    ('votacao_candidato_munzona', 'votacao_candidato_munzona', 2022, ['RN', 'BR']),
    ('votacao_candidato_munzona', 'votacao_candidato_munzona', 2020, ['RN']),
    ('detalhe_votacao_munzona', 'detalhe_votacao_munzona', 2022, ['RN', 'BR']),
    ('detalhe_votacao_munzona', 'detalhe_votacao_munzona', 2020, ['RN']),
    ('consulta_cand', 'consulta_cand', 2022, ['RN']),
    ('consulta_cand', 'consulta_cand', 2020, ['RN']),
    ('votacao_candidato_munzona', 'votacao_candidato_munzona', 2026, ['RN']),
    ('detalhe_votacao_munzona', 'detalhe_votacao_munzona', 2026, ['RN']),
    ('consulta_cand', 'consulta_cand', 2026, ['RN']),
    ('votacao_candidato_munzona', 'votacao_candidato_munzona', 2024, ['RN']),
    ('detalhe_votacao_munzona', 'detalhe_votacao_munzona', 2024, ['RN']),
    ('consulta_cand', 'consulta_cand', 2024, ['RN']),
]


def baixar(pasta, prefixo, ano, url=None, dest=None):
    dest = dest or BRUTOS / f'{prefixo}_{ano}.zip'
    if dest.exists():
        try:
            zipfile.ZipFile(dest).testzip()
            return dest
        except Exception:
            dest.unlink()
    url = url or f'{BASE}/{pasta}/{prefixo}_{ano}.zip'
    tmp = dest.with_suffix('.part')
    print('baixando', url, flush=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r, open(tmp, 'wb') as f:
        esperado = int(r.headers.get('Content-Length', 0))
        while True:
            bloco = r.read(1 << 20)
            if not bloco:
                break
            f.write(bloco)
    if esperado and tmp.stat().st_size != esperado:
        raise IOError(f'download incompleto: {tmp.stat().st_size} de {esperado} bytes')
    tmp.replace(dest)
    return dest


ANOS_SECAO = (2020, 2022, 2024, 2026)
UFS_SECAO = ['RN', 'DF']  # estados com detalhe por local de votação (cada estado a mais exige baixar e processar os votos por seção)
IBGE_BAIRROS = ('https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_de_setores_censitarios__divisoes_intramunicipais/'
                'censo_2022/bairros/shp/BR/BR_bairros_CD2022.zip')


def granular(ufs=None):
    """Votos por seção, locais de votação e bairros do IBGE, para os estados da lista."""
    ufs = ufs or UFS_SECAO
    for ano in ANOS_SECAO:
        for uf in ufs:
            nome = f'votacao_secao_{ano}_{uf}.csv'
            if not (CSV / nome).exists():
                try:
                    z = zipfile.ZipFile(baixar(None, 'votacao_secao', ano, url=f'{BASE}/votacao_secao/votacao_secao_{ano}_{uf}.zip', dest=BRUTOS / f'votacao_secao_{ano}_{uf}.zip'))
                except urllib.error.HTTPError as e:
                    if e.code != 404:
                        raise
                    print(f'{uf} {ano}: não há arquivo de seções (sem eleição desse tipo no estado)', flush=True)
                    continue
                print('extraindo', nome, flush=True)
                z.extract(nome, CSV)
        faltam = [uf for uf in ufs if (CSV / f'votacao_secao_{ano}_{uf}.csv').exists() and not (CSV / f'eleitorado_local_votacao_{ano}_{uf}.csv').exists()]
        if faltam:
            z = zipfile.ZipFile(baixar(None, 'eleitorado_local_votacao', ano, url=f'{BASE}/eleitorado_locais_votacao/eleitorado_local_votacao_{ano}.zip'))
            if f'eleitorado_local_votacao_{ano}_{faltam[0]}.csv' in z.namelist():  # a partir de 2026 o zip traz um arquivo por UF
                for uf in faltam:
                    z.extract(f'eleitorado_local_votacao_{ano}_{uf}.csv', CSV)
            else:
                nac = f'eleitorado_local_votacao_{ano}.csv'
                print('extraindo e filtrando', nac, flush=True)
                z.extract(nac, CSV)
                dados = pd.concat([c[c.SG_UF.isin(faltam)] for c in pd.read_csv(CSV / nac, sep=';', encoding='latin-1', dtype=str, chunksize=200000)])
                for uf in faltam:
                    dados[dados.SG_UF == uf].to_csv(CSV / f'eleitorado_local_votacao_{ano}_{uf}.csv', sep=';', index=False, encoding='latin-1')
                (CSV / nac).unlink()
    # Presidente de 2022 por seção: os arquivos dos estados não trazem o cargo, então filtramos o arquivo nacional (BR) em blocos
    pres = CSV / 'votacao_secao_2022_presidente.csv'
    if not pres.exists() or not set(ufs) <= set(pd.read_csv(pres, sep=';', dtype=str, usecols=['SG_UF']).SG_UF.unique()):
        z = zipfile.ZipFile(baixar(None, 'votacao_secao', 2022, url=f'{BASE}/votacao_secao/votacao_secao_2022_BR.zip', dest=BRUTOS / 'votacao_secao_2022_BR.zip'))
        membro = next(n for n in z.namelist() if n.endswith('_BR.csv'))
        print('filtrando', membro, flush=True)
        cols = ['SG_UF', 'NR_TURNO', 'CD_MUNICIPIO', 'NR_ZONA', 'NR_SECAO', 'DS_CARGO', 'NR_VOTAVEL', 'SQ_CANDIDATO', 'QT_VOTOS']
        with z.open(membro) as f:
            partes = [c[c.SG_UF.isin(ufs) & (c.DS_CARGO.str.upper() == 'PRESIDENTE')] for c in pd.read_csv(f, sep=';', encoding='latin-1', dtype=str, usecols=cols, chunksize=400000)]
        pd.concat(partes).to_csv(pres, sep=';', index=False, encoding='latin-1')
    shp = ROOT / 'dados' / 'malha_ibge' / 'BR_bairros_CD2022.shp'
    if not shp.exists():
        shp.parent.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(baixar(None, 'BR_bairros_CD2022', 0, url=IBGE_BAIRROS, dest=BRUTOS / 'BR_bairros_CD2022.zip')).extractall(shp.parent)


def main():
    BRUTOS.mkdir(parents=True, exist_ok=True)
    CSV.mkdir(parents=True, exist_ok=True)
    for pasta, prefixo, ano, ufs in PACOTES:
        z = zipfile.ZipFile(baixar(pasta, prefixo, ano))
        for uf in ufs:
            nome = f'{prefixo}_{ano}_{uf}.csv'
            if (CSV / nome).exists():
                continue
            print('extraindo', nome, flush=True)
            z.extract(nome, CSV)
    granular()


if __name__ == '__main__':
    main()
