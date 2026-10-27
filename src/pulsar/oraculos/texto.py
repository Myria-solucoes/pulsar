"""Leitores dos espelhos em texto publicados no pacote GEVAZP.

GEVAZP.REL, VAZDCP.REL, PROBVAZ.REL e VAZOES*.CSV mostram, com poucas casas,
os mesmos números dos binários. Servem de oráculo para os leitores binários
(03-oraculos-e-testes.md §3, "casar valores com o texto impresso").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

_NUM = r"-?\d*\.\d+(?:E[+-]\d+)?"
_TITULOS_CORR = {
    "hist_principais": "CORRELACAO ESPACIAL HISTORICA MENSAL/ANUAL ENTRE OS SUBSISTEMAS (POSTOS PRINCIPAIS",
    "sint_principais": "CORRELACAO ESPACIAL SINTETICA MENSAL/ANUAL ENTRE OS SUBSISTEMAS (POSTOS PRINCIPAIS",
    "hist_todos": "CORRELACAO ESPACIAL HISTORICA MENSAL/ANUAL ENTRE OS SUBSISTEMAS (TODOS POSTOS",
    "sint_todos": "CORRELACAO ESPACIAL SINTETICA MENSAL/ANUAL ENTRE OS SUBSISTEMAS (TODOS POSTOS",
}


def _linhas(caminho) -> list[str]:
    with open(caminho, encoding="latin-1") as f:
        return f.read().splitlines()


def _floats(s: str) -> list[float]:
    return [float(x) for x in re.findall(_NUM, s)]


# --------------------------------------------------------------------------
# Configuração


@dataclass(frozen=True)
class UsinaRel:
    nint: int
    num: int
    nome: str
    posto: int
    jusante: int
    ano_inicial: int
    ano_final: int
    status: str
    posto_artificial: int  # coluna PART (0 = não tem)
    bacia: str

    @property
    def coluna_ena(self) -> int:
        """Coluna usada nos blocos 'considerando artificiais' do VAZOES.RVx."""
        return self.posto_artificial or self.posto


def ler_configuracao(rel) -> list[UsinaRel]:
    """Tabela 'CONFIGURACAO DAS USINAS HIDRELETRICAS' do GEVAZP.REL."""
    out, dentro = [], False
    rx = re.compile(r"\s+(\d+)\s+(\d+)\s+(.{12})\s+(\d+)\s+(\d+)\s+(\d{4})\s+(\d{4})\s+(.*)$")
    for linha in _linhas(rel):
        if "CONFIGURACAO DAS USINAS HIDRELETRICAS" in linha:
            dentro = True
            continue
        if dentro and "TOTAL DE USINAS" in linha:
            break
        m = rx.match(linha) if dentro else None
        if not m:
            continue
        t = m[8].split()
        status = "" if t[0].lstrip("-").isdigit() else t.pop(0)
        # AJ TVj TVt PL DEFL PART FATOR BACIA
        out.append(
            UsinaRel(int(m[1]), int(m[2]), m[3].strip(), int(m[4]), int(m[5]),
                     int(m[6]), int(m[7]), status, int(t[5]), t[7])
        )
    return out


# --------------------------------------------------------------------------
# Previsões semanais e tendência


@dataclass(frozen=True)
class PrevisaoRel:
    nint: int
    posto: int
    nome: str
    total: tuple[int, ...]  # S1..S6
    incremental: tuple[int, ...]
    incremental_ena: tuple[int, ...]


def ler_previsoes(rel) -> list[PrevisaoRel]:
    """Tabela 'PREVISOES SEMANAIS TOTAIS / INCREMENTAIS / PARA ENA'."""
    out, dentro = [], False
    rx = re.compile(r"\s+(\d+)\s+(\d+)\s+(.{17})(.{8})((?:\s+-?\d+){18})\s*$")
    for linha in _linhas(rel):
        if "PREVISOES SEMANAIS TOTAIS" in linha:
            dentro = True
            continue
        if dentro and linha.startswith(" CEPEL") and out:
            break
        m = rx.match(linha) if dentro else None
        if m:
            v = tuple(int(x) for x in m[5].split())
            out.append(PrevisaoRel(int(m[1]), int(m[2]), m[3].strip(), v[:6], v[6:12], v[12:]))
    return out


TABELAS_TENDENCIA = {
    "fornecidas": "VAZOES FORNECIDAS PARA A TENDENCIA HIDROLOGICA",
    "fornecidas_principais": "VAZOES FORNECIDAS PARA A TENDENCIA HIDROLOGICA PARA POSTOS PRINCIPAIS",
    "incrementais_principais": "VAZOES INCREMENTAIS PARA A TENDENCIA HIDROLOGICA PARA POSTOS PRINCIPAIS",
    "incrementais_incrementais": "VAZOES INCREMENTAIS PARA A TENDENCIA HIDROLOGICA PARA POSTOS INCREMENTAIS",
}


def ler_tendencia(rel) -> dict[str, dict[int, tuple[str, np.ndarray]]]:
    """As quatro tabelas de tendência: {tabela: {posto: (nome, jan..dez)}}."""
    titulos = sorted(TABELAS_TENDENCIA.items(), key=lambda kv: -len(kv[1]))
    out = {k: {} for k in TABELAS_TENDENCIA}
    atual = None
    rx = re.compile(r"\s+(\d+) (.{12})((?:\s+" + _NUM + r"){12})\s*$")
    for linha in _linhas(rel):
        s = linha.strip()
        achou = next((k for k, t in titulos if s == t), None)
        if achou:
            atual = achou
            continue
        if atual and linha.startswith(" CEPEL"):
            atual = None
        m = rx.match(linha) if atual else None
        if m:
            out[atual][int(m[1])] = (m[2].strip(), np.array(_floats(m[3])))
    return out


# --------------------------------------------------------------------------
# Seções por série incremental


@dataclass
class SerieRel:
    nome: str
    historico: dict[int, np.ndarray] = field(default_factory=dict)
    serie_anual: dict[int, np.ndarray] = field(default_factory=dict)  # "MEDIA ULTIMOS 12 MESES"
    media: np.ndarray | None = None
    desvio: np.ndarray | None = None
    media_anual: np.ndarray | None = None  # média da série "média últimos 12 meses"
    desvio_anual: np.ndarray | None = None
    fac: np.ndarray | None = None  # [defasagem-1, mes-1]
    fac_componente_anual: np.ndarray | None = None  # tabela de ordem 0..11
    facp: np.ndarray | None = None
    ordens: list[int] | None = None
    coeficientes: list[list[float]] | None = None
    psi: list[float] | None = None


def ler_series_incrementais(rel) -> dict[str, SerieRel]:
    """Seções 'SERIE DE VAZOES INCREMENTAIS DO POSTO <nome>' do GEVAZP.REL."""
    series: dict[str, SerieRel] = {}
    s: SerieRel | None = None
    estado = None
    tabela: list[tuple[int, list[float]]] = []
    rx_ano = re.compile(r"\s+(\d{4})((?:\s+" + _NUM + r"){12})\s*$")
    rx_12 = re.compile(r"((?:\s+" + _NUM + r"){12})\s*$")
    rx_ordem = re.compile(r"\s+(\d+)((?:\s+" + _NUM + r"){12})\s*$")
    rx_ar = re.compile(r"\s+(\d+)\s+(\d+)((?:\s+" + _NUM + r")*)\s*$")

    def fecha_tabela():
        nonlocal tabela
        if s is not None and tabela:
            if estado == "fac":
                ini = [k for k, (o, _) in enumerate(tabela) if o == 0]
                corte = ini[0] if ini else len(tabela)
                s.fac = np.array([v for _, v in tabela[:corte]])
                if ini:
                    s.fac_componente_anual = np.array([v for _, v in tabela[corte:]])
            elif estado == "facp":
                s.facp = np.array([v for _, v in tabela])
        tabela = []

    for linha in _linhas(rel):
        if "SERIE  DE  VAZOES  INCREMENTAIS  DO  POSTO" in linha:
            fecha_tabela()
            nome = linha.split("POSTO", 1)[1].strip()
            s = series.setdefault(nome, SerieRel(nome))
            estado = "historico"
            continue
        if s is None:
            continue
        txt = linha.strip()
        if txt.startswith("SERIE  DE  MEDIA ULTIMOS 12 MESES"):
            estado = "anual"
            continue
        if txt == "MEDIA AMOSTRAL":
            estado = "media" if estado in ("historico", "media", "desvio") else "media_anual"
            continue
        if txt == "DESVIO PADRAO AMOSTRAL":
            estado = "desvio" if estado == "media" else "desvio_anual"
            continue
        if txt == "CORRELOGRAMA DA SERIE":
            estado = "fac"
            continue
        if txt == "CORRELOGRAMA PARCIAL DA SERIE":
            fecha_tabela()
            estado = "facp"
            continue
        if txt == "MODELO AUTOREGRESSIVO PARA CADA PERIODO":
            fecha_tabela()
            estado = "ar"
            s.ordens, s.coeficientes = [], []
            continue
        if txt.startswith("MES") and "COEFICIENTES DA PARTE A12" in txt:
            estado = "psi"
            s.psi = []
            continue
        if txt == "SERIE DE RUIDOS":
            estado = None
            continue
        if estado in ("historico", "anual"):
            m = rx_ano.match(linha)
            if m:
                destino = s.historico if estado == "historico" else s.serie_anual
                destino[int(m[1])] = np.array(_floats(m[2]))
        elif estado in ("media", "desvio", "media_anual", "desvio_anual"):
            m = rx_12.match(linha)
            if m and not rx_ano.match(linha):
                setattr(s, estado, np.array(_floats(m[1])))
        elif estado in ("fac", "facp"):
            m = rx_ordem.match(linha)
            if m:
                tabela.append((int(m[1]), _floats(m[2])))
        elif estado == "ar":
            m = rx_ar.match(linha)
            if m:
                s.ordens.append(int(m[2]))
                s.coeficientes.append(_floats(m[3]))
        elif estado == "psi":
            m = rx_ar.match(linha)
            if m:
                s.psi.append(_floats(m[3])[0])
    fecha_tabela()
    return series


# --------------------------------------------------------------------------
# Resíduos por série incremental


@dataclass
class ResiduosRel:
    nome: str
    serie: dict[int, np.ndarray] = field(default_factory=dict)  # ano -> 12 valores
    media: np.ndarray | None = None
    desvio: np.ndarray | None = None
    assimetria: np.ndarray | None = None
    fac: np.ndarray | None = None  # [defasagem-1, mes-1]


_TITULOS_RUIDO = {
    "MEDIA DA SERIE DE RUIDOS": "media",
    "DESVIO PADRAO DA SERIE DE RUIDOS": "desvio",
    "ASSIMETRIA DA SERIE DE RUIDOS": "assimetria",
}


def ler_residuos(rel) -> dict[str, ResiduosRel]:
    """Seções 'SERIE DE RUIDOS', média, desvio, assimetria e correlograma
    dos ruídos de cada série incremental do GEVAZP.REL (3 algarismos nos
    valores e momentos, 5 casas no correlograma)."""
    out: dict[str, ResiduosRel] = {}
    nome = estado = None
    fac: list[list[float]] = []
    rx_ano = re.compile(r"\s+(\d{4})((?:\s+" + _NUM + r"){12})\s*$")
    rx_ordem = re.compile(r"\s+(\d+)((?:\s+" + _NUM + r"){12})\s*$")
    for linha in _linhas(rel):
        if "SERIE  DE  VAZOES  INCREMENTAIS  DO  POSTO" in linha:
            nome, estado = linha.split("POSTO", 1)[1].strip(), None
            continue
        txt = linha.strip()
        if nome is None:
            continue
        if txt == "SERIE DE RUIDOS":
            estado = "serie"
            out[nome] = ResiduosRel(nome)
            continue
        if txt in _TITULOS_RUIDO:
            estado = _TITULOS_RUIDO[txt]
            continue
        if txt == "CORRELOGRAMA DA SERIE DE RUIDOS":
            estado, fac = "fac", []
            continue
        if estado is None or nome not in out:
            continue
        r = out[nome]
        if estado == "serie":
            m = rx_ano.match(linha)
            if m:
                r.serie[int(m[1])] = np.array(_floats(m[2]))
        elif estado in ("media", "desvio", "assimetria"):
            v = _floats(linha)
            if len(v) == 12 and "JAN" not in linha:
                setattr(r, estado, np.array(v))
                estado = None
        elif estado == "fac":
            m = rx_ordem.match(linha)
            if m:
                fac.append(_floats(m[2]))
                r.fac = np.array(fac)
            elif linha.startswith(" CEPEL"):
                estado = None
    return out


# --------------------------------------------------------------------------
# Correlações espaciais


def ler_correlacoes(rel, tabela: str) -> dict[tuple[str, str], np.ndarray]:
    """Tabela de correlação espacial: {(nome_i, nome_j): 12 meses + anual}.

    tabela: 'hist_principais', 'sint_principais', 'hist_todos' ou 'sint_todos'.
    """
    alvo = _TITULOS_CORR[tabela]
    out, atual = {}, None
    rx = re.compile(r"^ (.{12})->(.{12})(.*)$")
    for linha in _linhas(rel):
        if "CORRELACAO ESPACIAL" in linha:
            atual = next((k for k, t in _TITULOS_CORR.items() if t in linha), None)
            continue
        if atual != tabela:
            continue
        m = rx.match(linha)
        if m:
            v = _floats(m[3])
            if len(v) == 13:
                out[(m[1].strip(), m[2].strip())] = np.array(v)
    if not out:
        raise ValueError(f"{rel}: tabela '{alvo}' não encontrada")
    return out


# --------------------------------------------------------------------------
# Estatísticas históricas x geradas (1 casa decimal)


def ler_estatisticas_geradas(rel, secao: str = "PROCESSO  PAR(P)") -> dict[str, dict[str, np.ndarray]]:
    """Páginas 'PROCESSO  PAR(P)' ou 'RESULTADOS PARA VAZOES TOTALIZADAS':
    {sistema: {'media_hist','media_ger','desvio_hist','desvio_ger'}}."""
    out, atual, dentro, pares = {}, None, False, []
    for linha in _linhas(rel):
        txt = linha.strip()
        if txt == secao:
            dentro, atual, pares = True, None, []
            continue
        if not dentro:
            continue
        if txt.startswith("SISTEMA") and ":" in txt:
            atual = linha.split(":", 1)[1].strip()
            continue
        if atual and (txt.startswith("HIST") or txt.startswith("GER")):
            v = np.array(_floats(txt))
            if len(v) == 12:
                pares.append(v)
            if len(pares) == 4:
                out[atual] = dict(zip(("media_hist", "media_ger", "desvio_hist", "desvio_ger"), pares))
                dentro = False
    return out


# --------------------------------------------------------------------------
# VAZDCP.REL, PROBVAZ.REL e CSV


@dataclass(frozen=True)
class RegistroVazdcp:
    numero: int
    titulo: str
    valores: list[float]


def ler_vazdcp(caminho) -> list[RegistroVazdcp]:
    """Espelho em texto do VAZOES.RVx: um item por 'REGISTRO No.'."""
    linhas = _linhas(caminho)
    out, k = [], 0
    while k < len(linhas):
        m = re.match(r"REGISTRO No\.:\s+(\d+)", linhas[k])
        if not m:
            k += 1
            continue
        num, k = int(m[1]), k + 1
        titulo = linhas[k]
        if num <= 3:
            out.append(RegistroVazdcp(num, titulo, []))
            k += 1
            continue
        # cabeçalho de colunas (1 2 3 ...) e uma linha de valores
        valores = [float(x) for x in linhas[k + 2].split()]
        out.append(RegistroVazdcp(num, titulo.strip(), valores))
        k += 3
    return out


def ler_probvaz_rel(caminho) -> np.ndarray:
    """PROBVAZ.REL: [cenario, mes-1] com 4 casas."""
    linhas = []
    for linha in _linhas(caminho):
        t = [x.strip() for x in linha.split(",")]
        if len(t) >= 13 and t[0].isdigit():
            linhas.append([float(x) for x in t[1:13]])
    return np.array(linhas)


def ler_csv_series(caminho) -> tuple[list[tuple[int, str]], np.ndarray]:
    """VAZOES{I,T,IA,TA}.CSV -> ([(posto, nome)] na ordem NINT, [usina, cenario, mes-1])."""
    blocos: dict[tuple[int, str], list[list[float]]] = {}
    ordem = []
    for linha in _linhas(caminho):
        t = [x.strip() for x in linha.split(",")]
        if len(t) < 16 or not t[0].isdigit():
            continue
        chave = (int(t[1]), t[2])
        if chave not in blocos:
            blocos[chave] = []
            ordem.append(chave)
        blocos[chave].append([float(x) for x in t[4:16]])
    return ordem, np.array([blocos[k] for k in ordem])
