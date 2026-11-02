import pytest

from emporio_agent.policies import get_policy_index, tokenize


@pytest.fixture(scope="module")
def index():
    return get_policy_index()


def top_title(index, query: str) -> str:
    results = index.search(query, k=1)
    assert results, f"no section found for: {query}"
    return results[0][0].title


def test_tokenize_removes_accents_and_stopwords():
    assert tokenize("Qual o endereço da loja?") == ["endereco"]


def test_manual_is_split_into_sections(index):
    assert len(index.sections) == 19
    assert all(s.content for s in index.sections)


def test_editorial_comment_is_not_indexed(index):
    assert all("Editorial fixes" not in s.content for s in index.sections)


# Customer questions (in Portuguese, as they will arrive) -> expected manual section.
@pytest.mark.parametrize(
    "query, expected_prefix",
    [
        ("Qual o endereço da loja?", "1.2"),
        ("Que horas vocês abrem no sábado?", "2."),
        ("Posso parcelar em 12x?", "3.1"),
        ("Me arrependi da minha compra, posso devolver meu pedido?", "4."),
        ("Meu violão chegou com defeito", "4.2"),
        ("Quanto tempo demora a entrega pra outra cidade?", "5.2"),
        ("Como rastrear meu pedido?", "5.3"),
        ("Dá pra juntar desconto do pix com promoção?", "6.2"),
        ("O produto está esgotado, o que fazer?", "7.3"),
        ("Qual a garantia?", "8."),
        ("Vocês vendem cordas de violão?", "1."),
    ],
)
def test_question_retrieves_expected_section(index, query, expected_prefix):
    assert top_title(index, query).startswith(expected_prefix)


def test_unrelated_query_returns_nothing(index):
    assert index.search("capital da França") == []


def test_results_are_sorted_and_limited(index):
    results = index.search("frete entrega prazo", k=3)
    assert len(results) == 3
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)
