"""Check that the curated policies (data/processed/policies.md) cover the PDF content.

pypdf extracts the manual one word per line and loses the table structure, so the
Markdown version was curated by hand. This script is the safety net: it compares
every number (deadlines, amounts, percentages) and the relevant words of the PDF
with the Markdown and lists anything missing.

Usage: uv run python scripts/validate_policies.py
"""

import re
import sys
from pathlib import Path

from pypdf import PdfReader

from emporio_agent.config import PROCESSED_DIR, RAW_DIR
from emporio_agent.data_store import normalize

PDF = RAW_DIR / "politicas_da_loja.pdf"
MD = PROCESSED_DIR / "policies.md"

# PDF words that do not need to be in the Markdown (page headers and footers).
IGNORED = {"pagina", "manual", "versao", "documento", "interno", "restrito", "ultima", "atualizacao"}


def extract_pdf(path: Path) -> str:
    pages = [page.extract_text() or "" for page in PdfReader(path).pages]
    return normalize(" ".join(pages))


def main() -> int:
    pdf = extract_pdf(PDF)
    md = normalize(MD.read_text(encoding="utf-8"))

    numbers = set(re.findall(r"\d+(?:[.,]\d+)*", pdf))
    # Numbers like "7.2" are section ids, not content.
    missing_numbers = sorted(n for n in numbers if n not in md and not re.fullmatch(r"\d+\.\d", n))

    words = set(re.findall(r"[a-z]{6,}", pdf)) - IGNORED
    missing_words = sorted(w for w in words if w not in md)

    coverage = 1 - len(missing_words) / max(len(words), 1)
    print(f"PDF numbers missing from the Markdown: {missing_numbers or 'none'}")
    print(f"Vocabulary coverage: {coverage:.1%} ({len(words)} words)")
    if missing_words:
        print(f"Missing words (review, usually paraphrases): {', '.join(missing_words)}")
    return 1 if missing_numbers else 0


if __name__ == "__main__":
    sys.exit(main())
