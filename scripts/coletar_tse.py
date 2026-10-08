"""Baixa do TSE os resultados de 2020, 2022, 2024 e 2026 e extrai os arquivos usados na análise.

Fonte: TSE, dados abertos (https://cdn.tse.jus.br/estatistica/sead/odsele/).
Entradas baixadas (dados/tse/brutos/, ignoradas pelo git):
  votacao_candidato_munzona_<ano>.zip   votos de cada candidato por município e zona
  detalhe_votacao_munzona_<ano>.zip     aptos, comparecimento, abstenções, brancos, nulos e válidos por município e zona
  consulta_cand_<ano>.zip               cadastro dos candidatos (partido, cargo, situação, CPF usado só para ligar 2020 e 2022)
Saídas extraídas (dados/tse/csv/, ignoradas pelo git):
  RN de 2020, 2022, 2024 e 2026, e o arquivo BR (Presidente) de 2022.
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

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


def baixar(pasta, prefixo, ano):
    dest = BRUTOS / f'{prefixo}_{ano}.zip'
    if dest.exists():
        try:
            zipfile.ZipFile(dest).testzip()
            return dest
        except Exception:
            dest.unlink()
    url = f'{BASE}/{pasta}/{prefixo}_{ano}.zip'
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


if __name__ == '__main__':
    main()
