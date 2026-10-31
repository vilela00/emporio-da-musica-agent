from decimal import Decimal

from emporio.agent.guard import retry_note, ungrounded_amounts


def test_amounts_from_tools_or_customer_pass():
    evidence = ["Preço: R$ 2.199,00 (no PIX: R$ 2.089,05)", "tenho uns R$ 3000 pra gastar"]
    answer = "Sai por *R$ 2.199,00*, ou R$ 2.089,05 no PIX. Cabe nos seus R$ 3.000!"
    assert ungrounded_amounts(answer, evidence) == set()


def test_made_up_installment_is_caught():
    evidence = ["Crédito sem juros: até 12x de R$ 183,25"]
    answer = "Dá pra fazer em 6x de R$ 366,50 ou 12x de R$ 183,25."
    assert ungrounded_amounts(answer, evidence) == {Decimal("366.50")}
    assert "R$ 366,50" in retry_note({Decimal("366.50")})
