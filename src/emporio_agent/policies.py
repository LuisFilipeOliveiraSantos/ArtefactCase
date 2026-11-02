"""Retrieval over the store policy manual.

The manual is ~3k tokens split into ~20 short sections. At this size, embeddings and a
vector store would be infrastructure with no gain: a lexical ranking (simplified BM25,
accent-free, with a small synonym list) over the sections finds the right one and is
fully deterministic and testable.

The manual and the customers' questions are in Portuguese, so the stopwords and
synonyms below are Portuguese too.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from emporio_agent.config import POLICIES_MD
from emporio_agent.data_store import normalize

STOPWORDS = set(
    "a o e de da do das dos em no na nos nas um uma para por com sem que se ao aos as os "
    "ou eu meu minha voce vcs qual quais como quando onde posso pode tem ter ser sao "
    "esta isso essa esse mais muito ja nao sim loja".split()
)

# Bridges the customers' vocabulary to the manual's vocabulary.
SYNONYMS = {
    "devolver": ["devolucao", "arrependimento", "reembolso"],
    "devolucao": ["arrependimento", "reembolso"],
    "arrependi": ["arrependimento", "devolucao"],
    "trocar": ["troca", "trocas"],
    "quebrado": ["defeito", "avaria"],
    "estragado": ["defeito", "avaria"],
    "horario": ["funcionamento", "sabado", "domingo"],
    "abre": ["horario", "funcionamento"],
    "fecha": ["horario", "funcionamento"],
    "endereco": ["rua", "cep"],
    "fica": ["endereco"],
    "telefone": ["whatsapp", "contato"],
    "contato": ["telefone", "whatsapp", "mail"],
    "pagar": ["pagamento", "pix", "cartao", "boleto"],
    "parcelar": ["parcelamento", "parcela", "credito"],
    "parcelas": ["parcelamento", "parcela"],
    "frete": ["entrega", "entregas", "envio"],
    "entregam": ["entrega", "frete"],
    "chega": ["entrega", "prazo"],
    "demora": ["prazo"],
    "cidade": ["cidades", "correios", "transportadora"],
    "interior": ["cidades", "correios"],
    "rastrear": ["rastreamento", "codigo"],
    "esgotado": ["estoque", "indisponivel", "alternativas"],
    "acabou": ["estoque", "indisponivel"],
    "desconto": ["promocao", "promocoes", "descontos"],
    "acessorios": ["cordas", "palhetas", "cabos", "cases", "pedais", "amplificadores"],
    "dados": ["lgpd", "privacidade"],
    "reclamacao": ["empatia"],
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", normalize(text))
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


@dataclass(frozen=True)
class Section:
    title: str
    content: str
    tokens: tuple[str, ...]


class PolicyIndex:
    def __init__(self, path: Path = POLICIES_MD):
        text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
        self.sections = []
        for block in re.split(r"^## ", text, flags=re.M)[1:]:
            title, _, body = block.partition("\n")
            # The title counts twice: it is the best summary of what the section is about.
            tokens = tokenize(title) * 2 + tokenize(body)
            self.sections.append(Section(title.strip(), body.strip(), tuple(tokens)))

        self._tf = [Counter(s.tokens) for s in self.sections]
        self._avg_len = sum(len(s.tokens) for s in self.sections) / len(self.sections)
        df = Counter(t for tf in self._tf for t in tf)
        n = len(self.sections)
        self._idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def _expand(self, query: str) -> list[str]:
        terms = tokenize(query)
        return terms + [s for t in terms for s in SYNONYMS.get(t, [])]

    def search(self, query: str, k: int = 3) -> list[tuple[Section, float]]:
        """Return the k best sections for the query, best first, with their BM25 scores."""
        terms = self._expand(query)
        k1, b = 1.5, 0.75
        scored = []
        for section, tf in zip(self.sections, self._tf):
            length_norm = 1 - b + b * len(section.tokens) / self._avg_len
            score = sum(
                self._idf[t] * tf[t] * (k1 + 1) / (tf[t] + k1 * length_norm)
                for t in terms
                if t in tf
            )
            if score > 0:
                scored.append((section, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def titles(self) -> list[str]:
        return [s.title for s in self.sections]


@lru_cache(maxsize=1)
def get_policy_index() -> PolicyIndex:
    return PolicyIndex()
