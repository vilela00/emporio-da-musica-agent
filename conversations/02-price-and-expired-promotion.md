# 02. Price of a named model and a promotion that is over

- Customer: unregistered number, writing from `+55 67 98888-1234`
- Store clock: Monday 23/03/2026, 10:30 (store open)
- Exercises: price lookup, honesty about an inactive promotion (manual §7.3) and installment rules (§3.1)
- Model: gemini-3.8-flash. Recorded on 2026-10-31 with `uv run python -m evals.conversations`.

Customer messages are scripted; Tom's replies are the agent's output, unedited. Tool calls are listed under each message and their raw outputs are in the collapsed blocks.

---

**Cliente:** Quanto custa o Takamine GD20?

> `search_products(query='Takamine GD20')`
> `get_product_details(product_id=95)`

<details><summary>tool outputs</summary>

```text
Filtros: palavras "Takamine GD20" | só disponíveis
1 produto(s); mostrando 1:
- #95 Takamine GD20 Dreadnought Natural | Violões | R$ 2.199,00 (no PIX: R$ 2.089,05) | disponível

#95 Takamine GD20 Dreadnought Natural (Violões)
Situação: disponível, em estoque (5)
Preço: R$ 2.199,00 (no PIX: R$ 2.089,05)
Crédito sem juros: até 12x de R$ 183,25; débito; boleto (compensação em até 3 dias úteis)
Características: tampo Cedro Sólido; fundo e laterais Sapele; braço Mogno; cordas de aço; escala 650mm; sem captação; cor Natural
Descrição: Violão dreadnought Takamine com tampo sólido em cedro. Excelente para fingerstyle com timbre quente e definido.
Promoções encerradas, que não valem mais: Oferta Especial (12%)
```

</details>

**Tom:** Olá! Sou o Tom, assistente virtual da Empório da Música.

O violão *Takamine GD20 Dreadnought Natural* está disponível por *R$ 2.199,00*, ou em até 12x de *R$ 183,25* sem juros no cartão. No PIX à vista, ele sai por *R$ 2.089,05*.

Precisa de mais alguma informação sobre ele ou sobre as condições de entrega?

**Cliente:** Vi no Instagram que ele tava com 12% de desconto. Ainda vale?


**Tom:** Essa promoção de 12% já foi encerrada e não está mais valendo. 

O valor atual dele é *R$ 2.199,00* em até 12x sem juros, ou com o desconto de 5% no PIX, ficando por *R$ 2.089,05*.

Gostaria de ver as opções de frete ou tem mais alguma dúvida sobre o modelo?

**Cliente:** E se eu parcelar em 12x, como fica?


**Tom:** Em 12x no cartão de crédito sem juros, ele fica em parcelas de *R$ 183,25*, totalizando *R$ 2.199,00*.

Posso te ajudar a calcular o frete ou tirar mais alguma dúvida?
