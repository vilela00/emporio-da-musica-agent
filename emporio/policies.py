"""The store manual, retrieved by numbered section: the manual's own structure is the index."""

from __future__ import annotations

import re
from functools import lru_cache

from emporio.catalog import ROOT

MANUAL = ROOT / "data" / "derived" / "politicas_da_loja.md"

TOPICS: dict[str, tuple[str, ...]] = {
    "contato_e_loja": ("1",),
    "horario": ("2",),
    "pagamento": ("3",),
    "trocas_e_devolucoes": ("4",),
    "frete_e_entregas": ("5",),
    "promocoes": ("6",),
    "atendimento_e_escopo": ("7", "10"),
    "garantia": ("8",),
    "privacidade": ("9",),
}

# How the store reads its own manual where it is ambiguous. Each note maps to an assumption
# documented in the README (A-nn).
NOTES: dict[str, tuple[str, ...]] = {
    "contato_e_loja": (
        "Telefone e WhatsApp: (67) 3341-4444, como na capa e nos dados da empresa (§1.2).",
        "E-mail: contato@emporiodamusica.com.br, como na capa. A grafia com acento da §1.2 é erro de digitação.",
    ),
    "horario": (
        "Feriados considerados: nacionais e o estadual de Mato Grosso do Sul (11/10). "
        "O contexto do atendimento já traz se a loja está aberta e quando a equipe volta.",
    ),
    "pagamento": (
        "Parcelamento segue a §3.1 (mínimo por faixa de parcelas); a 'parcela mínima de R$ 100,00' "
        "da tabela vale para 7x a 12x. Qualquer valor de parcela vem da ferramenta de orçamento.",
    ),
    "trocas_e_devolucoes": (
        "Prazos de um pedido específico vêm calculados pela ferramenta de pedidos.",
        "O sistema não registra a data real de entrega: a previsão de entrega é usada como data de "
        "recebimento, e isso deve ser dito ao cliente.",
        "Pedidos entregues pela loja contam como compra online para o direito de arrependimento (§4.1).",
        "Nenhum produto do sistema está marcado como 'venda final'.",
    ),
    "frete_e_entregas": (
        "Pedido de exatamente R$ 500,00 em Campo Grande tem frete grátis.",
        "Região metropolitana: só Campo Grande é considerada; para outras cidades o frete sai pelo CEP no fechamento.",
        "Valor de frete de um pedido vem da ferramenta de orçamento.",
    ),
    "promocoes": (
        "Promoção só vale se a ferramenta de produto mostrar como ativa; o nome da campanha não indica vigência.",
    ),
    "atendimento_e_escopo": (
        "Não há lista de lojas parceiras no sistema: não invente nomes; diga que a equipe pode indicar.",
        "Sopros e cordas orquestrais aparecem no manual, mas não há itens dessas categorias no sistema "
        "agora: ofereça verificar com a equipe, sem dizer que a loja não vende.",
        "Reclamação: registre com a ferramenta de encaminhamento; retorno em até 24 horas úteis, como diz a §7.3.",
    ),
    "garantia": ("Prazo de garantia legal de um pedido específico vem da ferramenta de pedidos.",),
    "privacidade": ("Pedido de exclusão de dados: registre um encaminhamento com o motivo 'dados_pessoais'.",),
}


@lru_cache(maxsize=1)
def sections() -> dict[str, str]:
    text = re.sub(r"<!--.*?-->", "", MANUAL.read_text(encoding="utf-8"), flags=re.S)
    parts = re.split(r"(?m)^## (\d+)\. ", text)
    return {number: f"## {number}. {body.strip()}" for number, body in zip(parts[1::2], parts[2::2], strict=True)}


def get_policy(topic: str) -> str:
    if topic not in TOPICS:
        return f"Tópico desconhecido: {topic}. Tópicos válidos: {', '.join(TOPICS)}."
    numbers = TOPICS[topic]
    body = "\n\n".join(sections()[n] for n in numbers)
    notes = "\n".join(f"- {note}" for note in NOTES.get(topic, ()))
    header = f"Manual de políticas da loja (versão 2.1), seção {' e '.join(numbers)}:"
    return f"{header}\n\n{body}\n\nNotas de interpretação:\n{notes}"
