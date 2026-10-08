"""Organiza os candidatos do PT de todos os estados em tabelas simples, uma pasta por UF (dados/uf/<UF>/).

Entradas (dados/tse/brutos/, baixadas por scripts/coletar_tse.py)
  consulta_cand_<ano>.zip               cadastro nacional dos candidatos (arquivo BRASIL)
  votacao_candidato_munzona_<ano>.zip   votos por candidato, município e zona (arquivo BRASIL, lido em blocos)
  detalhe_votacao_munzona_<ano>.zip     aptos, comparecimento, brancos, nulos e válidos (um arquivo por UF, e BR para Presidente)
  dados/agg_2026/agg_<UF>.csv           Presidente de 2026 por município (boletins de urna)
Saídas, por UF
  candidaturas.csv  pessoas.csv  votos.csv  contexto.csv  disputas.csv

Quem entra: toda pessoa que foi candidata pelo PT, em qualquer estado, em 2020, 2022, 2024 ou 2026, com todas as candidaturas dela que tiveram
votos próprios (inclusive por outros partidos e em outros estados). A pessoa é ligada pelo título de eleitor, que não é publicado, e recebe um
identificador nacional (gid). Uma candidatura pertence ao estado em que teve votos; o Presidente tem candidatura em todos os estados.
"""
import hashlib
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preparar import CARGOS, ORDEM_DISP, SITUACAO, ctx_2026, contexto, inteiro, titulo  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parent.parent
D = ROOT / 'dados'
BRUTOS = D / 'tse' / 'brutos'
PARTIDO = 'PT'  # o recorte é de um partido; para outro partido basta trocar a sigla (o Presidente de 2026 abaixo é específico do PT)
ANOS = (2020, 2022, 2024, 2026)
UFS = ['AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT', 'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO']
UF_NOME = {'AC': 'Acre', 'AL': 'Alagoas', 'AM': 'Amazonas', 'AP': 'Amapá', 'BA': 'Bahia', 'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo',
           'GO': 'Goiás', 'MA': 'Maranhão', 'MG': 'Minas Gerais', 'MS': 'Mato Grosso do Sul', 'MT': 'Mato Grosso', 'PA': 'Pará', 'PB': 'Paraíba',
           'PE': 'Pernambuco', 'PI': 'Piauí', 'PR': 'Paraná', 'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RO': 'Rondônia', 'RR': 'Roraima',
           'RS': 'Rio Grande do Sul', 'SC': 'Santa Catarina', 'SE': 'Sergipe', 'SP': 'São Paulo', 'TO': 'Tocantins'}
PROPRIO = {'Presidente', 'Governador', 'Senador', 'Deputado Federal', 'Deputado Estadual', 'Deputado Distrital', 'Prefeito', 'Vereador'}
MUNICIPAIS = {'Prefeito', 'Vereador'}
FUNDIR = {73709: 98930}  # Boa Esperança do Norte (MT) foi desmembrada de Sorriso depois de 2022; os votos dos dois são somados, como no recorte do Brasil


def membro(zipfile_, sufixo):
    z = zipfile.ZipFile(zipfile_)
    return z, next(n for n in z.namelist() if n.endswith(sufixo))


def cadastro():
    cols = ['SQ_CANDIDATO', 'NM_CANDIDATO', 'NM_URNA_CANDIDATO', 'NR_CANDIDATO', 'SG_PARTIDO', 'DS_SIT_TOT_TURNO', 'NM_UE', 'SG_UE', 'SG_UF', 'DS_CARGO',
            'NR_TITULO_ELEITORAL_CANDIDATO']
    partes = []
    for ano in ANOS:
        z, n = membro(BRUTOS / f'consulta_cand_{ano}.zip', '_BRASIL.csv')
        with z.open(n) as f:
            c = pd.read_csv(f, sep=';', encoding='latin-1', dtype=str, usecols=cols)
        c['ano'] = ano
        partes.append(c)
    c = pd.concat(partes, ignore_index=True)
    c['cargo'] = c.DS_CARGO.str.title()
    # o TSE esconde o CPF a partir de 2024: as pessoas são ligadas pelo título de eleitor (que coincide com o CPF onde os dois existem)
    c['chave'] = c.NR_TITULO_ELEITORAL_CANDIDATO.where(c.NR_TITULO_ELEITORAL_CANDIDATO.str.len() == 12, 'sq' + c.SQ_CANDIDATO)
    return c.drop_duplicates('SQ_CANDIDATO')


def votos_nacionais(sq_relevantes):
    """Lê o arquivo nacional de votos por município em blocos. Devolve os votos das candidaturas relevantes e o total de todos os candidatos
    (usado só para a posição de cada um na disputa)."""
    cols = ['SG_UF', 'NR_TURNO', 'SG_UE', 'CD_MUNICIPIO', 'DS_CARGO', 'SQ_CANDIDATO', 'QT_VOTOS_NOMINAIS', 'QT_VOTOS_NOMINAIS_VALIDOS']
    chave_disp = {(a, c, t): v[0] for (a, c, t), v in CARGOS.items()}
    rel, tot = [], []
    for ano in ANOS:
        z, n = membro(BRUTOS / f'votacao_candidato_munzona_{ano}.zip', '_BRASIL.csv')
        with z.open(n) as f:
            for ch in pd.read_csv(f, sep=';', encoding='latin-1', dtype=str, usecols=cols, chunksize=600000):
                cargo = ch.DS_CARGO.str.title()
                disp = pd.Series([chave_disp.get((ano, c, t)) for c, t in zip(cargo, ch.NR_TURNO)], index=ch.index)
                ch = ch[disp.notna()]
                if not len(ch):
                    continue
                ch = ch.assign(disp=disp[disp.notna()], cargo=cargo[disp.notna()], v=inteiro(ch.QT_VOTOS_NOMINAIS_VALIDOS), vb=inteiro(ch.QT_VOTOS_NOMINAIS))
                ch['circ'] = np.where(ch.cargo.isin(MUNICIPAIS), ch.SG_UE, ch.SG_UF)
                tot.append(ch.groupby(['disp', 'circ', 'SQ_CANDIDATO']).v.sum().reset_index())
                r = ch[ch.SQ_CANDIDATO.isin(sq_relevantes)]
                rel.append(r.groupby(['disp', 'SG_UF', 'SQ_CANDIDATO', 'CD_MUNICIPIO']).agg(v=('v', 'sum'), vb=('vb', 'sum')).reset_index())
        print(ano, 'votos lidos', flush=True)
    rel = pd.concat(rel, ignore_index=True).groupby(['disp', 'SG_UF', 'SQ_CANDIDATO', 'CD_MUNICIPIO'], as_index=False).sum()
    tot = pd.concat(tot, ignore_index=True).groupby(['disp', 'circ', 'SQ_CANDIDATO'], as_index=False).v.sum()
    tot['rk'] = tot.groupby(['disp', 'circ']).v.rank(method='min', ascending=False).astype(int)
    tot['nc'] = tot.groupby(['disp', 'circ']).v.transform('size')
    return rel, tot[['disp', 'SQ_CANDIDATO', 'rk', 'nc']]


def detalhes():
    """Abre os arquivos de detalhe (aptos, comparecimento, brancos, nulos) de cada ano."""
    return {ano: zipfile.ZipFile(BRUTOS / f'detalhe_votacao_munzona_{ano}.zip') for ano in ANOS}


def ler_detalhe(z, uf, ano):
    nome = f'detalhe_votacao_munzona_{ano}_{uf}.csv'
    if nome not in z.namelist():
        return pd.DataFrame()
    with z.open(nome) as f:
        return pd.read_csv(f, sep=';', encoding='latin-1', dtype=str)


def main():
    cons = cadastro()
    pt_sq = cons[(cons.SG_PARTIDO == PARTIDO) & cons.cargo.isin(PROPRIO)]
    chaves_largas = set(pt_sq.chave)
    sq_rel = set(cons[cons.chave.isin(chaves_largas) & cons.cargo.isin(PROPRIO)].SQ_CANDIDATO)
    print(f'cadastro: {len(cons):,} candidaturas; {len(chaves_largas):,} pessoas do PT; {len(sq_rel):,} candidaturas relevantes', flush=True)
    rel, rank = votos_nacionais(sq_rel)
    rel = rel.merge(cons[['SQ_CANDIDATO', 'chave', 'SG_PARTIDO']], on='SQ_CANDIDATO')
    # pessoas do PT com votos próprios (como no recorte do RN: quem teve uma candidatura do PT com votos)
    chaves_pt = set(rel[rel.SG_PARTIDO == PARTIDO].chave)
    rel = rel[rel.chave.isin(chaves_pt)]
    ordem = sorted(chaves_pt, key=lambda c: hashlib.sha1(c.encode()).hexdigest())  # a ordem embaralhada só serve para os identificadores não revelarem nada
    gid = {c: n for n, c in enumerate(ordem, 1)}
    print(f'{len(chaves_pt):,} pessoas com votos; {rel.SQ_CANDIDATO.nunique():,} candidaturas', flush=True)
    lula_chave = cons[(cons.cargo == 'Presidente') & (cons.NR_CANDIDATO == '13')].chave.iloc[0]
    det = detalhes()
    brd = ler_detalhe(det[2022], 'BR', 2022)
    resumo = []
    for uf in UFS:
        saida = D / 'uf' / uf
        saida.mkdir(parents=True, exist_ok=True)
        r = rel[rel.SG_UF == uf].copy()
        r['cd_tse'] = inteiro(r.CD_MUNICIPIO)
        por = r.groupby(['disp', 'SQ_CANDIDATO']).agg(tot=('v', 'sum'), tot_bruto=('vb', 'sum')).reset_index()
        nmun = r[r.v > 0].groupby(['disp', 'SQ_CANDIDATO']).cd_tse.nunique().rename('nmun')
        por = por.merge(nmun, on=['disp', 'SQ_CANDIDATO'], how='left').fillna({'nmun': 0})
        por = por.merge(cons[['SQ_CANDIDATO', 'chave', 'NM_CANDIDATO', 'NM_URNA_CANDIDATO', 'NR_CANDIDATO', 'SG_PARTIDO', 'DS_SIT_TOT_TURNO', 'NM_UE', 'cargo']], on='SQ_CANDIDATO')
        por = por.merge(rank, on=['disp', 'SQ_CANDIDATO'], how='left')
        por['pessoa'] = 'g' + por.chave.map(gid).astype(str)
        por['situacao'] = por.DS_SIT_TOT_TURNO.map(lambda s: SITUACAO.get(s, titulo(s)))
        por['nome_urna'] = por.NM_URNA_CANDIDATO.map(titulo)
        por['nome'] = por.NM_CANDIDATO.map(titulo)
        por['anulados'] = por.tot_bruto - por.tot
        por['ue'] = np.where(por.cargo.isin(MUNICIPAIS), por.NM_UE.map(titulo), UF_NOME[uf])
        por['externo'] = por.cargo == 'Presidente'
        por['cid'] = [f'c{n:04d}' for n in range(1, len(por) + 1)]
        votos = r.merge(por[['SQ_CANDIDATO', 'disp', 'cid']], on=['SQ_CANDIDATO', 'disp']).groupby(['cid', 'cd_tse']).v.sum().reset_index().rename(columns={'v': 'votos'})

        # contexto das disputas do estado (participação)
        ctx = []
        for (ano, cargo, turno), (disp, _, _) in CARGOS.items():
            if disp not in set(por.disp) or cargo == 'Presidente':
                continue
            d = ler_detalhe(det[ano], uf, ano)
            if not len(d):
                continue
            d = d[(d.DS_CARGO.str.title() == cargo) & (d.NR_TURNO == turno)]
            if len(d):
                ctx.append(contexto(d, disp))
        for turno in ('1', '2'):  # Presidente de 2022: detalhe nacional
            disp = f'pres22t{turno}'
            if disp in set(por.disp):
                ctx.append(contexto(brd[(brd.DS_CARGO.str.title() == 'Presidente') & (brd.SG_UF == uf) & (brd.NR_TURNO == turno)], disp))
        # Presidente de 2026: boletins de urna, já agregados por município
        extra = None
        if (D / 'agg_2026' / f'agg_{uf}.csv').exists():
            t26 = ctx_2026(uf)
            c26 = t26.reset_index().rename(columns={'CD_MUNICIPIO': 'cd_tse'}).assign(disp='pres26t1')
            ctx.append(c26.assign(votos=c26.votos_dados)[['disp', 'cd_tse', 'aptos', 'comparec', 'votos', 'abst', 'brancos', 'nulos', 'validos']])
            agg26 = pd.read_csv(D / 'agg_2026' / f'agg_{uf}.csv')
            nom = agg26[agg26.DS_TIPO_VOTAVEL == 'Nominal'].groupby('NR_VOTAVEL').QT_VOTOS.sum().sort_values(ascending=False)
            extra = (t26.votos.rename_axis('cd_tse'), int(list(nom.index).index(13) + 1), len(nom))
        ctx = pd.concat(ctx, ignore_index=True) if ctx else pd.DataFrame(columns=['disp', 'cd_tse'])

        if extra is not None:
            serie, rk, nc = extra
            nova = {'cid': f'c{len(por) + 1:04d}', 'pessoa': 'g' + str(gid[lula_chave]), 'disp': 'pres26t1', 'nome_urna': 'Lula', 'nome': 'Luiz Inácio Lula da Silva', 'NR_CANDIDATO': '13',
                    'SG_PARTIDO': 'PT', 'situacao': '', 'tot': int(serie.sum()), 'nmun': int((serie > 0).sum()), 'rk': rk, 'nc': nc, 'anulados': 0, 'ue': UF_NOME[uf],
                    'externo': True, 'SQ_CANDIDATO': ''}
            por = pd.concat([por, pd.DataFrame([nova])], ignore_index=True)
            votos = pd.concat([votos, serie.rename('votos').reset_index().assign(cid=nova['cid'])[['cid', 'cd_tse', 'votos']]], ignore_index=True)

        votos['cd_tse'] = votos.cd_tse.replace(FUNDIR)
        votos = votos.groupby(['cid', 'cd_tse'], as_index=False).votos.sum()
        num = [c for c in ctx.columns if c not in ('disp', 'cd_tse')]
        ctx['cd_tse'] = ctx.cd_tse.replace(FUNDIR)
        ctx = ctx.groupby(['disp', 'cd_tse'], as_index=False)[num].sum() if len(ctx) else ctx
        por['ano'] = 2000 + por.disp.str.extract(r'(\d\d)')[0].astype(int)
        pess = por.sort_values(['ano', 'cid']).groupby('pessoa').agg(nome=('nome', 'last'), nome_urna=('nome_urna', 'last'), externo=('externo', 'max')).reset_index()
        por = por.rename(columns={'NR_CANDIDATO': 'numero', 'SG_PARTIDO': 'partido', 'SQ_CANDIDATO': 'sq'})
        por['situacao'] = por.situacao.fillna('')
        for c in ('tot', 'nmun', 'rk', 'nc', 'anulados'):
            por[c] = por[c].fillna(0).astype(int)
        por['sq'] = por.sq.fillna('')
        cols = ['cid', 'pessoa', 'disp', 'nome_urna', 'nome', 'numero', 'partido', 'situacao', 'tot', 'nmun', 'rk', 'nc', 'anulados', 'ue', 'sq']
        por[cols].to_csv(saida / 'candidaturas.csv', index=False)
        pess[['pessoa', 'nome', 'nome_urna', 'externo']].to_csv(saida / 'pessoas.csv', index=False)
        votos.sort_values(['cid', 'cd_tse']).to_csv(saida / 'votos.csv', index=False)
        ctx.to_csv(saida / 'contexto.csv', index=False)
        usadas = [d for d in ORDEM_DISP if d in set(por.disp)]
        pd.DataFrame({'id': usadas}).to_csv(saida / 'disputas.csv', index=False)
        resumo.append({'uf': uf, 'pessoas': len(pess), 'candidaturas': len(por), 'linhas_votos': len(votos), 'disputas': len(usadas)})
        print(f'{uf}: {len(pess):,} pessoas, {len(por):,} candidaturas, {len(votos):,} linhas de votos, {len(usadas)} disputas', flush=True)
    pd.DataFrame(resumo).to_csv(D / 'uf' / '_resumo.csv', index=False)


if __name__ == '__main__':
    main()
