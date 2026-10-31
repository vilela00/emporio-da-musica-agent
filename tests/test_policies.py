from emporio.policies import TOPICS, get_policy, sections


def test_all_ten_sections_parsed():
    assert list(sections()) == [str(n) for n in range(1, 11)]


def test_every_topic_resolves_with_notes():
    for topic in TOPICS:
        text = get_policy(topic)
        assert text.startswith("Manual de políticas") and "Notas de interpretação" in text


def test_payment_section_carries_the_tiers():
    text = get_policy("pagamento")
    assert "parcela mínima de R$ 80,00" in text and "acima de R$ 2.000,00" in text


def test_unknown_topic():
    assert "Tópico desconhecido" in get_policy("receitas")
