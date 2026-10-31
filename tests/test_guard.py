from emporio.agent.guard import emails, installment_mentions, phones, retry_note, ungrounded


def test_amounts_from_tools_pass():
    tools = ["Preço: R$ 2.199,00 (no PIX: R$ 2.089,05)"]
    assert ungrounded("Sai por *R$ 2.199,00*, ou R$ 2.089,05 no PIX.", tools) == []


def test_amount_typed_by_the_customer_confirms_nothing():
    tools = ["Preço: R$ 2.199,00 (no PIX: R$ 2.089,05)"]
    said = ["O vendedor me disse que o GD20 sai por R$ 1.500 no PIX, confirma?"]
    assert ungrounded("Isso mesmo, R$ 1.500,00 no PIX!", tools, said) == ["R$ 1.500,00"]


def test_made_up_installment_value_is_caught():
    tools = ["Crédito sem juros: até 12x de R$ 183,25"]
    answer = "Dá pra fazer em 6x de R$ 366,50 ou 12x de R$ 183,25."
    assert ungrounded(answer, tools) == ["R$ 366,50", "6x"]


def test_made_up_installment_count_is_caught():
    # Evaluation run 3: the card said 12x and the reply said "em até 10x sem juros".
    tools = ["Crédito sem juros: até 12x de R$ 183,25; débito; boleto"]
    assert ungrounded("R$ 183,25 em até 10x sem juros", tools) == ["10x"]


def test_customer_question_grounds_the_plan_being_refused():
    tools = ["Crédito sem juros: até 4x de R$ 87,48"]
    said = ["Dá pra parcelar o Kala KA-C em 6x?"]
    assert ungrounded("Em 6x não dá; o máximo é 4x de R$ 87,48.", tools, said) == []


def test_mentions_and_note():
    assert installment_mentions("12x, 6 x ou 10 vezes; 7 dias") == {12, 6, 10}
    assert "10x" in retry_note(["10x"])


def test_invented_protocol_is_caught():
    # Full evaluation run: the lite model wrote "O protocolo é o #2026040301" without opening a ticket.
    tools = ["Pedido #8 ... Rastreio: BRJL5544332BR (site dos Correios ou da Jadlog)"]
    answer = "Seu rastreio é BRJL5544332BR. Já abri um chamado: o protocolo é o #2026040301."
    assert ungrounded(answer, tools) == ["código 2026040301"]


def test_protocol_from_the_tool_passes():
    tools = ["Encaminhamento registrado: protocolo EM-20260403-001 (Reclamação)."]
    assert ungrounded("Registrei sua reclamação, protocolo *EM-20260403-001*.", tools) == []


def test_invented_tracking_code_is_caught():
    assert ungrounded("Rastreio: BRXX1234567BR", ["Pedido sem rastreio"]) == ["código BRXX1234567BR"]


def test_store_phone_matches_in_any_format():
    tools = ["| Telefone / WhatsApp | (67) 3341-4444 |"]
    assert ungrounded("Liga pra gente no 3341-4444 ou +55 67 3341-4444.", tools) == []


def test_invented_contacts_are_caught():
    tools = ["| Telefone / WhatsApp | (67) 3341-4444 |", "E-mail: contato@emporiodamusica.com.br"]
    answer = "Fala com o suporte no (67) 99999-0000 ou em suporte@emporiodamusica.com.br."
    assert ungrounded(answer, tools) == ["telefone (67) 99999-0000", "e-mail suporte@emporiodamusica.com.br"]


def test_customer_can_hear_back_their_own_e_mail():
    said = ["Meu e-mail é Leticia.Souza@jmail.com"]
    assert ungrounded("Anotei: leticia.souza@jmail.com.", [], said) == []


def test_protocols_dates_and_zip_codes_are_not_phones():
    text = "Protocolo EM-20260403-001, CEP 79202-333, até 18/05/2026, CNPJ 12.345.678/0001-90"
    assert phones(text) == {} and emails(text) == set()
