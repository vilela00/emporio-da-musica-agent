# 05. A late order on Good Friday night

- Customer: Ana, customer #2, order #8 shipped and late, writing from `+55 67 99654-7821`
- Store clock: Good Friday 03/04/2026, 19:40 (holiday, store closed)
- Exercises: a late shipment found in the data, the complaint registered with a protocol (§7.3) and the next opening after a holiday
- Model: gemini-3.8-flash. Recorded on 2026-10-31 with `uv run python -m evals.conversations`.

Customer messages are scripted; Tom's replies are the agent's output, unedited. Tool calls are listed under each message and their raw outputs are in the collapsed blocks.

---

**Cliente:** Boa noite. Meu pedido não chegou até hoje e já passou muito da data.

> `get_my_orders()`
> `create_handoff(reason='reclamacao', summary='Pedido #8 (Kala KA-C Concert Mogno) com entrega prevista para 28/02/2026 está em atraso e a cliente reclama que ainda não recebeu.')`

<details><summary>tool outputs</summary>

```text
Cliente: Ana (Campo Grande)

Pedido #8, feito em 15/02/2026
Situação: enviado
Itens: 1x Kala KA-C Concert Mogno
Total do pedido: R$ 349,90 (cartão de débito)
Rastreio: BRJL5544332BR (site dos Correios ou da Jadlog)
Previsão de entrega: 28/02/2026 (ATRASADO: a previsão já passou)
Se o cliente reclamar do atraso: registre já com create_handoff (motivo reclamacao) e informe o protocolo que a ferramenta devolver.

Encaminhamento registrado: protocolo EM-20260403-001 (Reclamação). Retorno da equipe em até 24 horas úteis (manual §7.3). Diga esse prazo ao cliente, sem prometer o que a equipe vai fazer. Agora em Campo Grande: sexta-feira, 03/04/2026, 19:40. A loja está fechada (feriado: Sexta-feira da Paixão). A equipe volta no sábado, 04/04/2026, às 09:00.
```

</details>

**Tom:** Boa noite, Ana! Sou o Tom, assistente virtual da Empório da Música.

Sinto muito por esse atraso com o seu pedido #8 (Kala KA-C Concert Mogno). Já registrei a sua reclamação sob o protocolo *EM-20260403-001*.

Como hoje é feriado e a loja está fechada, nossa equipe retorna amanhã, sábado (04/04), a partir das 09:00, e entrará em contato com você em até 24 horas úteis para verificar a situação junto à transportadora.

Posso te ajudar com mais alguma dúvida por enquanto?

**Cliente:** Vocês abrem amanhã? Qual o endereço da loja?

> `get_store_policy(topic='horario')`
> `get_store_policy(topic='contato_e_loja')`

<details><summary>tool outputs</summary>

```text
Manual de políticas da loja (versão 2.1), seção 2:

## 2. Horário de Funcionamento

O atendimento presencial na loja segue os horários abaixo. O atendimento via WhatsApp segue o mesmo horário, com respostas automáticas fora do expediente.

| Dia | Horário |
|---|---|
| Segunda a Sexta-feira | 09:00 às 18:00 |
| Sábado | 09:00 às 13:00 |
| Domingo e Feriados | Fechado |

Em datas especiais (Black Friday, Aniversário da Loja, Natal), o horário pode ser estendido. Alterações serão comunicadas com antecedência nas redes sociais e no atendimento via WhatsApp.

Notas de interpretação:
- Feriados considerados: nacionais e o estadual de Mato Grosso do Sul (11/10). O contexto do atendimento já traz se a loja está aberta e quando a equipe volta.

Manual de políticas da loja (versão 2.1), seção 1:

## 1. Sobre a Empório da Música

A Empório da Música é uma loja especializada em instrumentos musicais, fundada em 2008 em Campo Grande, Mato Grosso do Sul. Com mais de 15 anos de atuação no mercado, somos referência regional na venda de instrumentos para músicos iniciantes, intermediários e profissionais.

Nosso catálogo abrange mais de 300 instrumentos de marcas nacionais e internacionais, incluindo guitarras, baixos, violões, baterias, teclados, instrumentos de sopro, cordas orquestrais e ukuleles. Trabalhamos exclusivamente com instrumentos musicais — não comercializamos acessórios como cordas, palhetas, cabos, cases, pedais ou amplificadores.

### 1.1 Missão

Democratizar o acesso a instrumentos musicais de qualidade na região Centro-Oeste, oferecendo atendimento especializado e preços competitivos, contribuindo para o desenvolvimento cultural e musical da comunidade.

### 1.2 Dados da Empresa

| Campo | Informação |
|---|---|
| Razão Social | Empório da Música Instrumentos Musicais Ltda. |
| Nome Fantasia | Empório da Música |
| CNPJ | 12.345.678/0001-90 |
| Endereço | Rua 14 de Maio, 3200 — Centro, Campo Grande - MS, 79202-333 |
| Telefone / WhatsApp | (67) 3341-4444 |
| E-mail | contato@empóriodamusica.com.br |
| Fundação | 2008 |

Notas de interpretação:
- Telefone e WhatsApp: (67) 3341-4444, como na capa e nos dados da empresa (§1.2).
- E-mail: contato@emporiodamusica.com.br, como na capa. A grafia com acento da §1.2 é erro de digitação.
```

</details>

**Tom:** Sim, Ana! Amanhã (sábado) funcionamos das 09:00 às 13:00.

Nosso endereço é:
• *Rua 14 de Maio, 3200 — Centro, Campo Grande - MS*

Precisa de mais alguma informação?

**Cliente:** Tá bom, obrigada.


**Tom:** Por nada, Ana! Qualquer outra dúvida, estou por aqui. Tenha uma ótima noite!
