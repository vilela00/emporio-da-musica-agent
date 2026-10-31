from emporio.agent.whatsapp import whatsapp_text


def test_markdown_becomes_whatsapp():
    text = "## Opções\n- **Yamaha C40**: R$ 599,90\n* Tagima\nPedido **#8** enviado."
    assert whatsapp_text(text) == "Opções\n• *Yamaha C40*: R$ 599,90\n• Tagima\nPedido *#8* enviado."


def test_single_asterisk_bold_is_kept():
    assert whatsapp_text("Sai por *R$ 2.199,00*.") == "Sai por *R$ 2.199,00*."
