# Traceability: store manual → implementation → evidence

I read the store manual the way I read a tender's terms of reference: every clause that changes what the agent may say becomes a requirement with a place where it is enforced and a test or scenario that proves it. Section numbers refer to `data/políticas_da_loja.pdf` (v2.1). Scenario ids refer to `evals/scenarios.py`.

| Manual | Requirement | Enforced in | Evidence |
|---|---|---|---|
| §1, §7.1 | Only instruments; accessories politely redirected; no invented partner stores | persona rules; `get_store_policy("atendimento_e_escopo")` notes | S10 |
| §1.2 | Address and contact | `get_store_policy("contato_e_loja")` + note on the conflicting phone and e-mail (A-09) | S03 |
| §2 | Mon–Fri 09–18, Sat 09–13, closed on Sundays and holidays | `hours.store_status`, appended to the prompt every turn | `test_hours.py` (7 tests), S17 |
| §3 | PIX: 5% off the list price | `pricing.PricedItem.pix_total` | `test_pricing.py::test_pix_discount_on_list_price`, S02 |
| §3.1 | Installments: up to 3x min. R$ 50, 4x–6x min. R$ 80, 7x–12x min. R$ 100 (wins over the table's "R$ 100", A-10) | `pricing.min_installment`, `max_installments` | `test_pricing.py::test_installment_tiers_follow_section_3_1`, `test_views.py::test_quote_refuses_installments_below_minimum`, S15 |
| §3.1 | Combined payment only above R$ 2,000 | `pricing.Quote.combined_payment_allowed` | `test_pricing.py::test_combined_payment_only_above_2000` |
| §4.1 | Regret: 7 days from receipt | `orders.deadlines` (receipt = estimated delivery, A-14) | `test_orders.py::test_return_and_warranty_deadlines`, S04, conversation 03 |
| §4.2 | Defect exchange: 30 days from purchase | `orders.deadlines` | same test, conversation 03 |
| §4.3, §4.4 | Preference exchange; items not eligible | manual text via `get_store_policy("trocas_e_devolucoes")` | persona rules (no dedicated test) |
| §5.1 | Campo Grande: free from R$ 500, otherwise R$ 35; 1–3 business days | `shipping.shipping_for` (R$ 500,00 exactly is free, A-11) | `test_shipping.py`, conversation 01 |
| §5.2 | Other cities: carriers, price by CEP, large items may need a special quote | `shipping.shipping_for`, `views.shipping_text` | `test_shipping.py::test_other_cities_and_large_items`, S18 |
| §5.3 | Tracking code format BR + 9 + BR | order view; grounding guard checks every code in a reply | `test_guard.py::test_invented_tracking_code_is_caught` |
| §6.2 | Promotions don't stack; PIX not on promotional prices | `catalog.Store.active_promotion`, `PricedItem.pix_total` | `test_pricing.py::test_promotion_price_and_no_pix_on_top`, `test_mixed_cart_applies_pix_only_to_regular_items` |
| §6.2 | Show original price and percentage with the promotional price | `views.price_text`, persona rule | S06 |
| §7.1 | Tone: informal but professional | persona prompt | conversations 01–05 |
| §7.1 | Never quote price, stock or deadlines without checking the system | tools + grounding guard (amounts, installment plans, protocol numbers, tracking codes) | `test_guard.py` (8 tests); the eval runner re-checks every reply |
| §7.1 | Out of hours: tell when the team is back | `hours.describe` in the prompt context | S16, S17, conversation 05 |
| §7.2 | Greet by name | `prompts.customer_line` (name from the phone number) | `test_prompts.py`, S20 |
| §7.3 | Out of stock: say so and offer similar available items | `search.alternatives`, `views.product_card` | `test_search.py`, `test_views.py::test_out_of_stock_card_offers_alternatives`, S07 |
| §7.3 | Discontinued: out of the catalog, offer equivalents | `Product.availability`, alternatives | S08 |
| §7.3 | Expired promotion: be transparent, give the current price | `views.product_card` lists past promotions as no longer valid | `test_views.py::test_product_card_prices_and_past_promotion`, S05, conversation 02 |
| §7.3 | Complaint: empathy, register, forward; reply within 24 business hours | `create_handoff` → `handoff.open_ticket` (orders attached by the system) | `test_handoff.py`, S16, conversation 05 |
| §8.1 | Legal warranty: 90 days from receipt | `orders.deadlines` | `test_orders.py`, S04, conversation 03 |
| §9 | Personal data only for the customer's own orders | identity from the channel; `orders.lookup_orders` scoping; same answer for wrong e-mail and missing order | `test_orders.py` (3 tests), S13, S14, S19, conversation 04 |
| §10 | When unsure how a policy applies, ask the manager | `create_handoff` with reason `duvida_de_politica` | persona rule |
