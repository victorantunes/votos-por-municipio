"""Organiza os dados do TSE em tabelas simples (uma linha por disputa, candidatura ou município).

Entradas
  dados/tse/csv/*.csv        RN de 2020, 2022, 2024 e 2026 e Presidente de 2022 (scripts/coletar_tse.py)
  dados/agg_2026/agg_*.csv   boletins de urna de 2026, Presidente, por município (scripts/coletar_bu_2026.py)
  dados/correspondencia_tse_ibge.csv
Saídas
  dados/br/contexto.csv, dados/br/lula.csv                       Lula no Brasil (2022 1º e 2º turnos, 2026 1º turno)
  (os candidatos do PT de cada estado ficam em scripts/preparar_uf.py)

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
(D / 'br').mkdir(exist_ok=True)

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


# ============================================================ disputas dos candidatos do PT (todos os estados)
CARGOS = {  # (ano, DS_CARGO do TSE, turno) -> (id da disputa, cargo, tipo); o id sem sufixo é o 1º turno, e "t2" o 2º
    (2020, 'Prefeito', '1'): ('pref20', 'Prefeito', 'maj'), (2020, 'Prefeito', '2'): ('pref20t2', 'Prefeito', 'maj'), (2020, 'Vereador', '1'): ('ver20', 'Vereador', 'prop'),
    (2022, 'Governador', '1'): ('gov22', 'Governador', 'maj'), (2022, 'Governador', '2'): ('gov22t2', 'Governador', 'maj'), (2022, 'Senador', '1'): ('sen22', 'Senador', 'maj'),
    (2022, 'Deputado Federal', '1'): ('df22', 'Deputado Federal', 'prop'), (2022, 'Deputado Estadual', '1'): ('de22', 'Deputado Estadual', 'prop'),
    (2022, 'Deputado Distrital', '1'): ('dd22', 'Deputado Distrital', 'prop'),
    (2022, 'Presidente', '1'): ('pres22t1', 'Presidente', 'maj'), (2022, 'Presidente', '2'): ('pres22t2', 'Presidente', 'maj'),
    (2024, 'Prefeito', '1'): ('pref24', 'Prefeito', 'maj'), (2024, 'Prefeito', '2'): ('pref24t2', 'Prefeito', 'maj'), (2024, 'Vereador', '1'): ('ver24', 'Vereador', 'prop'),
    (2026, 'Governador', '1'): ('gov26', 'Governador', 'maj'), (2026, 'Senador', '1'): ('sen26', 'Senador', 'maj'),
    (2026, 'Deputado Federal', '1'): ('df26', 'Deputado Federal', 'prop'), (2026, 'Deputado Estadual', '1'): ('de26', 'Deputado Estadual', 'prop'),
    (2026, 'Deputado Distrital', '1'): ('dd26', 'Deputado Distrital', 'prop')}
ORDEM_DISP = ['ver20', 'pref20', 'pref20t2', 'de22', 'df22', 'dd22', 'sen22', 'gov22', 'gov22t2', 'pres22t1', 'pres22t2', 'ver24', 'pref24', 'pref24t2',
              'de26', 'df26', 'dd26', 'sen26', 'gov26', 'pres26t1']
SITUACAO = {'ELEITO': 'Eleito', 'ELEITO POR QP': 'Eleito', 'ELEITO POR MÉDIA': 'Eleito', 'SUPLENTE': 'Suplente', 'NÃO ELEITO': 'Não eleito',
            '2º TURNO': '2º turno'}


def titulo(txt):
    part = {'De', 'Da', 'Do', 'Das', 'Dos', 'E'}
    p = str(txt).strip().title().split(' ')
    return ' '.join(w.lower() if (i > 0 and w in part) else w for i, w in enumerate(p))


# o recorte por estado está em scripts/preparar_uf.py


if __name__ == '__main__':
    brasil()
