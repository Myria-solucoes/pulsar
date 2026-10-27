"""Leitura de um deck completo do modo DECOMP (U19 §4)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .binarios import Hidr, HistoricoVazoes, Posto, ler_hidr, ler_postos, ler_vazoes_dat
from .caso import DadosGerais, ListaDecomp, ler_arquivos, ler_caso, ler_gevazp_dat, ler_lista_decomp
from .dadger import Dadger, ler_dadger
from .prevs_modif import Modif, Previsao, ler_modif, ler_prevs
from .regras import Regras, ler_regras
from .texto import ErroLeitura, resolver

# P-DECK-01: nome fixo do arquivo de modificações (U19 §4.11).
NOME_MODIF = "MODIF.DAT"


@dataclass
class Deck:
    diretorio: Path
    caso: str | None = None
    arquivos: dict[str, str] | None = None
    gevazp: DadosGerais | None = None
    lista_decomp: ListaDecomp | None = None
    dadger: Dadger | None = None
    hidr: Hidr | None = None
    prevs: dict[int, Previsao] | None = None
    postos: dict[int, Posto] | None = None
    historico: HistoricoVazoes | None = None
    modif: list[Modif] | None = None
    regras: Regras | None = None
    # P-DECK-02 (ESCOLHA, lacuna L14): fonte preferida do nº de postos quando
    # o DADGER (& VAZOES reg. 3) e o GEVAZP.DAT (reg. 17) informam os dois.
    fonte_n_postos: str = "dadger"

    @property
    def n_postos(self) -> int:
        """Número de postos do histórico (P-DECK-02, P-DADG-09, P-DECK-05)."""
        v = self.dadger.vazoes if self.dadger else None
        do_dadger = v.numero_postos if v and v.numero_postos else None
        do_gevazp = self.gevazp.numero_postos if self.gevazp is not None else None
        ordem = (do_dadger, do_gevazp) if self.fonte_n_postos == "dadger" else (do_gevazp, do_dadger)
        for n in ordem:
            if n:
                return n
        # P-DECK-05 (ESCOLHA, lacuna L15): sem nenhuma das duas fontes, 320
        # (valor do GEVAZP.DAT reg. 17 = 0, U19 §3.3).
        return 320


def _arquivo(diretorio: Path, nome: str | None, obrigatorio: bool) -> Path | None:
    if not nome:
        if obrigatorio:
            raise ErroLeitura(f"{diretorio}: nome de arquivo ausente")
        return None
    p = resolver(diretorio, nome)
    if p is None and obrigatorio:
        raise ErroLeitura(f"{diretorio}: arquivo {nome} não encontrado")
    return p


def ler_deck(
    diretorio: Path,
    dadger: str | None = None,
    completo: bool = True,
    fonte_n_postos: str = "dadger",
    exigir_fim_modif: bool = True,
    lista_decomp: str | None = None,
) -> Deck:
    """Lê o deck a partir de CASO.DAT (U19 §4.1–4.4).

    P-DECK-04: sem ``dadger``, segue CASO.DAT -> ARQUIVOS.DAT reg. 10 -> lista
    do DECOMP, que é a execução cujas saídas estão no pacote.

    ``dadger`` força o nome do DADGER (decks com várias revisões). Com
    ``completo=False`` lê o que existir (coleções parciais com só DADGER,
    HIDR e REGRAS). ``lista_decomp`` troca a lista do ARQUIVOS.DAT reg. 10
    por outra do diretório (P-CLI-01: a lista de outra revisão, ``RV0``).
    """
    d = Path(diretorio)
    if fonte_n_postos not in ("dadger", "gevazp"):
        raise ValueError(fonte_n_postos)
    deck = Deck(diretorio=d, fonte_n_postos=fonte_n_postos)
    # P-DECK-06 (ESCOLHA, lacuna L15): nomes usados quando falta a lista de
    # arquivos (U19 §4.6 "Arquivo: HIDR.DAT"; §3.10 "regras.dat").
    nome_hidr = "HIDR.DAT"
    nome_regras = "REGRAS.DAT"

    caso = _arquivo(d, "CASO.DAT", completo)
    if caso is not None:
        deck.caso = ler_caso(caso)
        deck.arquivos = ler_arquivos(_arquivo(d, deck.caso, True))
        deck.gevazp = ler_gevazp_dat(_arquivo(d, deck.arquivos.get("dados_gerais"), True))
        nome_regras = deck.arquivos.get("regras", nome_regras)
        lista = _arquivo(d, lista_decomp or deck.arquivos.get("lista_decomp"), completo or bool(lista_decomp))
        if lista is not None:
            deck.lista_decomp = ler_lista_decomp(lista)
            dadger = dadger or deck.lista_decomp.dadger
            nome_hidr = deck.lista_decomp.hidr

    if dadger is None:
        # P-DECK-07 (ESCOLHA, lacuna L15): sem lista do DECOMP (coleção de
        # decks do ONS), o primeiro DADGER.* em ordem alfabética.
        cands = sorted(p.name for p in d.iterdir() if p.name.upper().startswith("DADGER."))
        if not cands:
            raise ErroLeitura(f"{d}: sem DADGER")
        dadger = cands[0]
    deck.dadger = ler_dadger(_arquivo(d, dadger, True))
    deck.hidr = ler_hidr(_arquivo(d, nome_hidr, True))

    v = deck.dadger.vazoes
    if v is not None:
        p = _arquivo(d, v.arquivo_prevs, completo)
        if p is not None:
            # P-PREVS-03: semanas no PREVS = não observadas + observadas
            # (DADGER & VAZOES reg. 7; REL "SEMANAS TOTAIS").
            n_sem = (v.semanas_nao_observadas or 0) + (v.semanas_observadas or 0)
            deck.prevs = ler_prevs(p, n_sem or None)
        p = _arquivo(d, v.arquivo_postos, completo)
        if p is not None:
            deck.postos = ler_postos(p, deck.n_postos)
        p = _arquivo(d, v.arquivo_historico, completo)
        if p is not None:
            if deck.gevazp is None or deck.gevazp.ano_inicial_historico is None:
                raise ErroLeitura(f"{d}: sem ano inicial do histórico para ler {p.name}")
            deck.historico = ler_vazoes_dat(p, deck.gevazp.ano_inicial_historico, deck.n_postos)

    p = _arquivo(d, NOME_MODIF, False)  # existência não obrigatória (U19 §4.11)
    if p is not None:
        deck.modif = ler_modif(p, exigir_fim=exigir_fim_modif)
    # P-DECK-03: REGRAS.DAT só é obrigatório se houver NPOSNW (U19 §3.10).
    p = _arquivo(d, nome_regras, completo and bool(deck.dadger.ac_config("NPOSNW")))
    if p is not None:
        deck.regras = ler_regras(p)
    return deck
