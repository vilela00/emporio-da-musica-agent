from emporio.agent.guard import installment_mentions, retry_note, ungrounded


def test_amounts_from_tools_or_customer_pass():
    evidence = ["Preço: R$ 2.199,00 (no PIX: R$ 2.089,05)", "tenho uns R$ 3000 pra gastar"]
    answer = "Sai por *R$ 2.199,00*, ou R$ 2.089,05 no PIX. Cabe nos seus R$ 3.000!"
    assert ungrounded(answer, evidence) == []


def test_made_up_installment_value_is_caught():
    evidence = ["Crédito sem juros: até 12x de R$ 183,25"]
    answer = "Dá pra fazer em 6x de R$ 366,50 ou 12x de R$ 183,25."
    assert ungrounded(answer, evidence) == ["R$ 366,50", "6x"]


def test_made_up_installment_count_is_caught():
    # Evaluation run 3: the card said 12x and the reply said "em até 10x sem juros".
    evidence = ["Crédito sem juros: até 12x de R$ 183,25; débito; boleto"]
    assert ungrounded("R$ 183,25 em até 10x sem juros", evidence) == ["10x"]


def test_customer_question_grounds_the_plan_being_refused():
    evidence = ["Dá pra parcelar o Kala KA-C em 6x?", "Crédito sem juros: até 4x de R$ 87,48"]
    assert ungrounded("Em 6x não dá; o máximo é 4x de R$ 87,48.", evidence) == []


def test_mentions_and_note():
    assert installment_mentions("12x, 6 x ou 10 vezes; 7 dias") == {12, 6, 10}
    assert "10x" in retry_note(["10x"])


def test_invented_protocol_is_caught():
    # Full evaluation run: the lite model wrote "O protocolo é o #2026040301" without opening a ticket.
    evidence = ["Pedido #8 ... Rastreio: BRJL5544332BR (site dos Correios ou da Jadlog)"]
    answer = "Seu rastreio é BRJL5544332BR. Já abri um chamado: o protocolo é o #2026040301."
    assert ungrounded(answer, evidence) == ["código 2026040301"]


def test_protocol_from_the_tool_passes():
    evidence = ["Encaminhamento registrado: protocolo EM-20260403-001 (Reclamação)."]
    assert ungrounded("Registrei sua reclamação, protocolo *EM-20260403-001*.", evidence) == []


def test_invented_tracking_code_is_caught():
    assert ungrounded("Rastreio: BRXX1234567BR", ["Pedido sem rastreio"]) == ["código BRXX1234567BR"]
