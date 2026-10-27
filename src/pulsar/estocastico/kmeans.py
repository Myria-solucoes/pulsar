"""K-means de Hartigan e Wong: port do algoritmo AS 136 (02 §8; lacuna L12).

Fonte: ``fontes/algoritmos/as136.f`` (StatLib, Applied Statistics 28(1):
100–108, 1979), referência [17] do R3383. As três rotinas (KMNS, OPTRA e
QTRAN) seguem o Fortran instrução a instrução: mesmas etapas, mesmos
testes de conjunto vivo (LIVE, NCP, ITRAN), mesmas atualizações incrementais
dos centros, mesmos desempates e o mesmo recálculo final dos centros como
médias. Proveniência: P-KM-01..06 em PROVENIENCIA.md.

Adaptação de execução (P-KM-03): entre duas transferências os centros não
mudam e a decisão de cada ponto depende só do próprio ponto, então os pontos
são avaliados em lotes e o lote é cortado no primeiro ponto que transfere
(ou em que ``INDX``/``ICOUN`` chega a M). As saídas antecipadas dos laços
(``IF (DC .GE. RR) GO TO 60``) não mudam o resultado, porque somas parciais
de quadrados são não decrescentes também em ponto flutuante.

Aritmética (P-KM-01): ``distancia="sequencial"`` soma Σ_J (a_J - c_J)² em
sequência de J = 1..N no tipo dos dados (com float32, o REAL do as136.f);
``distancia="blas"`` (padrão) calcula ‖a‖² + ‖c‖² - 2 a·c em float64 pelo
produto de matrizes, cerca de 6 vezes mais rápido no tamanho real (P-KM-01), e só difere da soma
sequencial nos últimos bits (decisões mudam apenas em empates numéricos).

Índices internos começam em 0; os contadores comparados com LIVE e NCP
(passo ``I`` e ``ISTEP``) seguem a numeração do Fortran, a partir de 1.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# P-KM-02: "BIG to be a very large positive number" (as136.f, DATA BIG /1.E30/).
BIG = 1.0e30
# P-KM-04 (ESCOLHA, lacuna L12): número máximo de iterações (argumento ITER
# do KMNS, que o AS 136 deixa para quem chama).
ITERACOES = 50


class ErroKmeans(ValueError):
    pass


@dataclass(frozen=True)
class ResultadoKmeans:
    centros: np.ndarray  # [K, N], médias finais dos grupos (rótulo 150 do KMNS)
    grupo: np.ndarray  # [M], IC1 (0..K-1)
    contagens: np.ndarray  # [K], NC
    wss: np.ndarray  # [K]
    iteracoes: int  # passagens pelo laço 140 (OPTRA + QTRAN)
    ifault: int  # 0 ou 2 (iterações esgotadas; centros finais ainda são médias)


def _dist_seq(a: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Σ_J (a_J - c_J)² somado em sequência de J (laços 10, 20, 30, 40 e 50
    do Fortran). ``a`` [B, N] e ``c`` [B, N] (pares) ou ``c`` [K, N] com
    ``a`` [B, 1, N] (todos os centros)."""
    d = np.zeros(np.broadcast_shapes(a.shape, c.shape)[:-1], dtype=a.dtype)
    for j in range(a.shape[-1]):
        x = a[..., j] - c[..., j]
        d = d + x * x
    return d


class _Estado:
    def __init__(self, a: np.ndarray, c: np.ndarray, distancia: str):
        self.a = a
        self.blas = distancia == "blas"
        self.a2 = np.einsum("ij,ij->i", a, a) if self.blas else None
        self.m, self.n = a.shape
        self.k = c.shape[0]
        self.c = c
        t = a.dtype.type
        self.um = t(1.0)
        self.big = t(BIG)
        self.ic1 = np.zeros(self.m, dtype=np.int64)
        self.ic2 = np.zeros(self.m, dtype=np.int64)
        self.nc = np.zeros(self.k, dtype=np.int64)
        self.an1 = np.zeros(self.k, dtype=a.dtype)
        self.an2 = np.zeros(self.k, dtype=a.dtype)
        self.ncp = np.zeros(self.k, dtype=np.int64)
        self.itran = np.zeros(self.k, dtype=np.int64)
        self.live = np.zeros(self.k, dtype=np.int64)
        self.d = np.zeros(self.m, dtype=a.dtype)
        self.indx = 0

    # ------------------------------------------------------------------
    def _todas(self, i0: int, i1: int) -> np.ndarray:
        """Distâncias [B, K] dos pontos i0..i1-1 a todos os centros."""
        return self._colunas(i0, i1, slice(None))

    def _pares(self, i0: int, i1: int, ls) -> np.ndarray:
        """Distâncias [B] dos pontos i0..i1-1 aos centros ``ls`` (um por ponto)."""
        if not self.blas:
            return _dist_seq(self.a[i0:i1], self.c[ls])
        x = self.a[i0:i1] - self.c[ls]
        return np.einsum("ij,ij->i", x, x)

    def inicial(self):
        """Laços 50–120 do KMNS: dois centros mais próximos de cada ponto,
        centros = médias, AN1, AN2, ITRAN e NCP iniciais."""
        a, c = self.a, self.c
        for i0 in range(0, self.m, 1024):
            dist = self._todas(i0, min(self.m, i0 + 1024))
            # IC1 = menor distância com o menor índice nos empates; IC2 = idem
            # entre os demais (equivale às comparações estritas do laço 50).
            o = np.argsort(dist, axis=1, kind="stable")
            self.ic1[i0:i0 + 1024] = o[:, 0]
            self.ic2[i0:i0 + 1024] = o[:, 1]
        self._medias()
        if (self.nc == 0).any():
            raise ErroKmeans("IFAULT = 1: grupo vazio depois da alocação inicial")
        aa = self.nc.astype(a.dtype)
        self.an2 = aa / (aa + self.um)
        self.an1 = np.where(aa > self.um, aa / np.where(aa > self.um, aa - self.um, self.um), self.big).astype(a.dtype)
        self.itran[:] = 1
        self.ncp[:] = -1

    def _medias(self):
        """Laços 70–110 (e 160–180): soma dos pontos de cada grupo na ordem
        I = 1..M e divisão pela contagem."""
        a = self.a
        self.nc = np.bincount(self.ic1, minlength=self.k)
        c = np.zeros((self.k, self.n), dtype=a.dtype)
        for i in range(self.m):  # soma sequencial em I, como no Fortran
            c[self.ic1[i]] += a[i]
        with np.errstate(invalid="ignore", divide="ignore"):
            self.c = c / self.nc.astype(a.dtype)[:, None]

    # ------------------------------------------------------------------
    def _transfere(self, i: int, l1: int, l2: int):
        """Atualização dos centros, NC, AN1 e AN2 (laços 80 do OPTRA e 50 do
        QTRAN)."""
        c, a, um = self.c, self.a, self.um
        al1 = a.dtype.type(self.nc[l1])
        alw = al1 - um
        al2 = a.dtype.type(self.nc[l2])
        alt = al2 + um
        c[l1] = (c[l1] * al1 - a[i]) / alw
        c[l2] = (c[l2] * al2 + a[i]) / alt
        self.nc[l1] -= 1
        self.nc[l2] += 1
        self.an2[l1] = alw / al1
        self.an1[l1] = self.big
        if alw > um:
            self.an1[l1] = alw / (alw - um)
        self.an1[l2] = alt / al2
        self.an2[l2] = alt / (alt + um)
        self.ic1[i] = l2
        self.ic2[i] = l1

    # ------------------------------------------------------------------
    def _varredura(self, dist, ll, r2, cand):
        """Laço 60 do OPTRA para um lote: (L2, R2) de cada ponto.

        Fortran: R2 começa em D(I,LL)·AN2(LL) e, para L crescente entre os
        candidatos, passa a DC·AN2(L) quando DC < R2/AN2(L). No modo
        "sequencial" a varredura é refeita assim, com R2 corrente; no modo
        "blas" usa-se o equivalente em aritmética exata: o menor DC·AN2(L)
        entre os candidatos, com empate para o menor L, só substitui LL se
        for estritamente menor (P-KM-03)."""
        if self.blas:
            v = np.where(cand, dist * self.an2[None, :], np.inf)
            j = np.argmin(v, axis=1)
            vmin = v[np.arange(len(j)), j]
            melhor = vmin < r2
            return np.where(melhor, j, ll), np.where(melhor, vmin, r2)
        l2 = ll.copy()
        r2 = r2.copy()
        for b in range(len(ll)):
            cs = np.flatnonzero(cand[b])
            if not len(cs):
                continue
            db = dist[b, cs]
            an2 = self.an2[cs]
            r = r2[b]
            p = 0
            while p < len(cs):
                hit = np.flatnonzero(db[p:] < r / an2[p:])
                if not len(hit):
                    break
                q = p + int(hit[0])
                r = db[q] * an2[q]
                l2[b] = cs[q]
                p = q + 1
            r2[b] = r
        return l2, r2

    @staticmethod
    def _corte(transf, contador: int, m: int):
        """Posição do primeiro ponto do lote que transfere e da primeira em
        que o contador (INDX ou ICOUN, +1 por ponto e 0 na transferência)
        chega a M sem transferência antes; None quando não há."""
        t = np.flatnonzero(transf)
        t = int(t[0]) if len(t) else None
        h = m - contador - 1
        h = h if 0 <= h < len(transf) and (t is None or h < t) else None
        return t, h

    def _colunas(self, i0: int, i1: int, ls) -> np.ndarray:
        """Distâncias [B, len(ls)] dos pontos i0..i1-1 aos centros ``ls``."""
        a = self.a[i0:i1]
        c = self.c[ls]
        if not self.blas:
            return _dist_seq(a[:, None, :], c[None, :, :])
        c2 = np.einsum("ij,ij->i", c, c)
        return np.maximum(self.a2[i0:i1, None] + c2[None, :] - 2.0 * (a @ c.T), 0.0)

    def optra(self):
        """AS 136.1, etapa de transferência ótima.

        As distâncias de um bloco de pontos a todos os centros são guardadas;
        numa transferência só os centros L1 e L2 mudam, e só essas duas
        colunas são recalculadas para os pontos seguintes do bloco."""
        m = self.m
        self.live[self.itran == 1] = m + 1
        i0 = 0
        while i0 < m:
            bloco = np.arange(i0, min(m, i0 + 1024))
            dist = self._todas(i0, int(bloco[-1]) + 1)  # [B, K]
            pos = 0
            lote = 16
            while pos < len(bloco):
                idx = bloco[pos:pos + lote]
                dsub = dist[pos:pos + lote]
                ar = np.arange(len(idx))
                l1 = self.ic1[idx]
                ll = self.ic2[idx]
                ok_nc = self.nc[l1] != 1  # NC(L1) = 1: sem transferência
                # D(I) recalculado quando NCP(L1) != 0
                dnovo = np.where(self.ncp[l1] != 0, dsub[ar, l1] * self.an1[l1], self.d[idx])
                r2 = dsub[ar, ll] * self.an2[ll]
                passo = idx + 1  # I do Fortran
                cand = ~((passo >= self.live[l1])[:, None] & (passo[:, None] >= self.live[None, :]))
                cand[ar, l1] = False
                cand[ar, ll] = False
                cand[~ok_nc] = False
                l2, r2 = self._varredura(dsub, ll, r2, cand)
                transf = ok_nc & (r2 < dnovo)  # rótulo 70
                t, h = self._corte(transf, self.indx, m)
                ate = len(idx) if t is None else t
                if h is not None:
                    ate = h + 1
                sel = ar[:ate][ok_nc[:ate]]
                self.d[idx[sel]] = dnovo[sel]
                self.ic2[idx[sel]] = l2[sel]
                self.indx += ate
                if h is not None:
                    return  # INDX = M
                if t is None:
                    pos += len(idx)
                    lote = min(2 * lote, 1024)
                    continue
                i = int(idx[t])
                L1, L2 = int(l1[t]), int(l2[t])
                self.d[i] = dnovo[t]
                self.indx = 0
                self.live[L1] = m + i + 1
                self.live[L2] = m + i + 1
                self.ncp[L1] = i + 1
                self.ncp[L2] = i + 1
                self._transfere(i, L1, L2)
                pos += t + 1
                if pos < len(bloco):
                    dist[pos:, [L1, L2]] = self._colunas(i0 + pos, int(bloco[-1]) + 1, [L1, L2])
                lote = 16
            i0 = int(bloco[-1]) + 1
        self.itran[:] = 0
        self.live -= m

    # ------------------------------------------------------------------
    def qtran(self):
        """AS 136.2, etapa de transferência rápida."""
        m = self.m
        icoun = 0
        istep = 0
        lote = 64
        i0 = 0
        while True:
            idx = np.arange(i0, min(m, i0 + lote))
            l1 = self.ic1[idx]
            l2 = self.ic2[idx]
            passos = istep + np.arange(1, len(idx) + 1)
            ok_nc = self.nc[l1] != 1
            rec = passos <= self.ncp[l1]
            i1 = int(idx[-1]) + 1
            dnovo = np.where(rec, self._pares(i0, i1, l1) * self.an1[l1], self.d[idx])
            testa = ~((passos >= self.ncp[l1]) & (passos >= self.ncp[l2]))
            r2 = dnovo / self.an2[l2]
            transf = ok_nc & testa & (self._pares(i0, i1, l2) < r2)
            t, h = self._corte(transf, icoun, m)
            ate = len(idx) if t is None else t
            if h is not None:
                ate = h + 1
            sel = np.flatnonzero(ok_nc[:ate])
            self.d[idx[sel]] = dnovo[sel]
            icoun += ate
            istep += ate
            if h is not None:
                return  # ICOUN = M
            if t is not None:
                i = int(idx[t])
                L1, L2 = int(l1[t]), int(l2[t])
                istep += 1
                icoun = 0
                self.d[i] = dnovo[t]
                self.indx = 0
                self.itran[L1] = 1
                self.itran[L2] = 1
                self.ncp[L1] = istep + m
                self.ncp[L2] = istep + m
                self._transfere(i, L1, L2)
                i0 = i + 1
                lote = 64
            else:
                i0 += len(idx)
                lote = min(2 * lote, 4096)
            if i0 >= m:
                i0 = 0  # GO TO 10
            lote = min(lote, m - i0)


DISTANCIAS = ("blas", "sequencial")


def kmns(a: np.ndarray, centros_iniciais: np.ndarray, iteracoes: int = ITERACOES,
         distancia: str = "blas") -> ResultadoKmeans:
    """KMNS do AS 136. ``a`` [M, N] e ``centros_iniciais`` [K, N]; os
    centros são convertidos para o tipo de ``a`` (P-KM-01: float32 é o REAL
    do as136.f; o padrão do Pulsar é float64 com ``distancia="blas"``).

    IFAULT 3 (K ≤ 1 ou K ≥ M) e 1 (grupo vazio) levantam ``ErroKmeans``;
    IFAULT 2 (iterações esgotadas) é devolvido em ``ifault``, com os centros
    finais recalculados como médias, como no Fortran (P-KM-04)."""
    a = np.ascontiguousarray(a)
    c = np.array(centros_iniciais, dtype=a.dtype, copy=True)
    m, n = a.shape
    k = c.shape[0]
    if c.shape[1] != n:
        raise ErroKmeans("centros com dimensão diferente dos pontos")
    if k <= 1 or k >= m:
        raise ErroKmeans(f"IFAULT = 3: K = {k} fora de 2..M-1 (M = {m})")
    if distancia not in DISTANCIAS:
        raise ValueError(distancia)
    e = _Estado(a, c, distancia)
    e.inicial()
    ifault = 2
    it = 0
    for it in range(1, iteracoes + 1):
        e.optra()
        if e.indx == m:
            ifault = 0
            break
        e.qtran()
        if k == 2:
            ifault = 0
            break
        e.ncp[:] = 0
    # rótulo 150: centros finais = médias, WSS
    e._medias()
    wss = np.zeros(k, dtype=a.dtype)
    for j in range(n):
        x = a[:, j] - e.c[e.ic1, j]
        np.add.at(wss, e.ic1, x * x)
    return ResultadoKmeans(e.c, e.ic1.copy(), e.nc.copy(), wss, it, ifault)
