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


def test_scope_section_warns_about_the_other_whatsapp_number():
    text = get_policy("atendimento_e_escopo")
    assert "(67) 3321-4500" in text and "não informe esse número" in text and "(67) 3341-4444" in text
