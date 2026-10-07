"""Baixa os boletins de urna (BU) do 1º turno de 2026 e agrega os votos para Presidente por município.

Fonte: TSE, dados abertos, "Resultados - 2026 - Boletim de Urna" (primeiro turno, gerado em 05/10/2026).
Saída: dados/agg_2026/agg_<UF>.csv (um arquivo por UF) e dados/agg_2026/_resumo.csv.
"""
import csv
import io
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DADOS = ROOT / 'dados'
BU = DADOS / 'bu'
AGG = DADOS / 'agg_2026'
BU.mkdir(parents=True, exist_ok=True)
AGG.mkdir(parents=True, exist_ok=True)

URLS = [u.strip() for u in (DADOS / 'bu_urls.txt').read_text().splitlines() if u.strip()]
UA = {'User-Agent': 'Mozilla/5.0'}


def baixar(url):
    dest = BU / url.split('/')[-1]
    if dest.exists() and dest.stat().st_size > 0:
        try:
            zipfile.ZipFile(dest)
            return dest
        except Exception:
            dest.unlink()
    tmp = dest.with_suffix('.part')
    for tentativa in range(3):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, 'wb') as f:
                esperado = int(r.headers.get('Content-Length', 0))
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            if esperado and tmp.stat().st_size != esperado:
                raise IOError(f'download incompleto: {tmp.stat().st_size} de {esperado} bytes')
            tmp.replace(dest)
            return dest
        except Exception as e:
            print('erro baixando', url, e, flush=True)
            time.sleep(5)
    raise RuntimeError('falha ao baixar ' + url)


def processar(zip_path):
    uf = zip_path.name.split('_')[2]
    out = AGG / f'agg_{uf}.csv'
    t0 = time.time()
    z = zipfile.ZipFile(zip_path)
    nome_csv = [i.filename for i in z.infolist() if i.filename.lower().endswith('.csv')][0]
    votos = defaultdict(int)          # (mun, votavel) -> votos
    info_votavel = {}                 # votavel -> (tipo, nome, partido)
    info_mun = {}                     # mun -> (nome, uf)
    secoes = {}                       # (mun, zona, secao) -> (aptos, comparecimento)
    vistos = set()
    duplicadas = 0
    lidas = 0
    with z.open(nome_csv) as f:
        header = f.readline().decode('latin-1').strip().split(';')
        h = [c.strip('"') for c in header]
        ix = {c: i for i, c in enumerate(h)}
        for raw in f:
            if b'"Presidente"' not in raw:
                continue
            row = next(csv.reader([raw.decode('latin-1')], delimiter=';'))
            if row[ix['DS_CARGO_PERGUNTA']] != 'Presidente' or row[ix['NR_TURNO']] != '1':
                continue
            lidas += 1
            mun = row[ix['CD_MUNICIPIO']]
            zona, sec = row[ix['NR_ZONA']], row[ix['NR_SECAO']]
            votavel = row[ix['NR_VOTAVEL']]
            chave = (mun, zona, sec, votavel)
            if chave in vistos:
                duplicadas += 1
                continue
            vistos.add(chave)
            votos[(mun, votavel)] += int(row[ix['QT_VOTOS']])
            info_votavel[votavel] = (row[ix['DS_TIPO_VOTAVEL']], row[ix['NM_VOTAVEL']], row[ix['SG_PARTIDO']])
            info_mun[mun] = (row[ix['NM_MUNICIPIO']], row[ix['SG_UF']])
            secoes[(mun, zona, sec)] = (int(row[ix['QT_APTOS']]), int(row[ix['QT_COMPARECIMENTO']]))
    aptos = defaultdict(int)
    compar = defaultdict(int)
    nsec = defaultdict(int)
    for (mun, _, _), (a, c) in secoes.items():
        aptos[mun] += a
        compar[mun] += c
        nsec[mun] += 1
    with open(out, 'w', newline='', encoding='utf-8') as g:
        w = csv.writer(g)
        w.writerow(['SG_UF', 'CD_MUNICIPIO', 'NM_MUNICIPIO', 'NR_VOTAVEL', 'DS_TIPO_VOTAVEL', 'NM_VOTAVEL', 'SG_PARTIDO',
                    'QT_VOTOS', 'QT_SECOES', 'QT_APTOS', 'QT_COMPARECIMENTO'])
        for (mun, votavel), v in sorted(votos.items()):
            tipo, nome, partido = info_votavel[votavel]
            nm, sg = info_mun[mun]
            w.writerow([sg, mun, nm, votavel, tipo, nome, partido, v, nsec[mun], aptos[mun], compar[mun]])
    msg = f'{uf}: {lidas} linhas de presidente, {len(info_mun)} municipios, {duplicadas} duplicadas, {time.time()-t0:.0f}s'
    print(msg, flush=True)
    return uf, lidas, len(info_mun), duplicadas


def main():
    ordem = sorted(URLS, key=lambda u: u)
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(baixar, u) for u in ordem]
        resumo = []
        for fut in futs:
            p = fut.result()
            print('baixado', p.name, round(p.stat().st_size / 1e6), 'MB', flush=True)
            uf = p.name.split('_')[2]
            if (AGG / f'agg_{uf}.csv').exists():
                print(uf, 'ja agregado, pulando', flush=True)
                continue
            resumo.append(processar(p))
    with open(AGG / '_resumo.csv', 'w', newline='') as g:
        w = csv.writer(g)
        w.writerow(['uf', 'linhas_presidente', 'municipios', 'duplicadas'])
        w.writerows(resumo)
    print('FIM', flush=True)


if __name__ == '__main__':
    main()
