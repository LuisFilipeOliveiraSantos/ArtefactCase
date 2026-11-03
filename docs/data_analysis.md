# Analysis of the provided data

First pass over the CSVs and the policy manual, to guide data handling and the README assumptions.

## Overview

| Table | Rows | Notes |
|---|---|---|
| `products` | 65 | `status`: 62 `active`, 2 `discontinued`, 1 `coming_soon`. Mostly acoustic guitars (35) and ukuleles (15). `specs` is a JSON string. IDs out of order (145 appears before 131). |
| `categories` | 9 | Woodwinds, brass and orchestral strings have **no products** registered. |
| `promotions` | 25 | Only **4 active** (`is_active=1`): products 127, 121, 90 and 94. No validity dates, only the flag. |
| `orders` | 20 | Status: `delivered` (7), `shipped` (1), `confirmed` (4), `pending` (4), `cancelled` (4). Orders from Oct/2025 to Mar/2026. |
| `order_items` | 22 | Orders 15 and 20 have 2 items. |
| `customers` | 50 | Customers from Campo Grande, Dourados, Três Lagoas, Corumbá and Ponta Porã. |

## Issues found

### Products and catalog
- **Zero stock but `active`**: product 96 (Giannini GF-3D) is `active` with `stock_quantity = 0` → must be treated as out of stock, not available.
- **Discontinued with stock**: product 136 (Ibanez Bass 2X) is `discontinued` but has 13 units. Product 113 is `discontinued` with 0 units.
- **`coming_soon` with stock and already sold**: product 130 (Kala KA-ABP-CTG) is `coming_soon` with 2 units, yet it was already sold (2 units in order 3, from 2025-11-20, and 1 in order 14).
- **Unrealistic names** in guitars, basses, drums and keyboards (e.g. "Music Man Bass 1X Electric Bass", "Teclado Sintetizador Korg Synth 1 Pro").
- **Descriptions that contradict the product**: 135 "Music Man Bass 1X" is described as a Fender Jazz Bass; 136 "Ibanez Bass 2X" as a Precision; 137 "Yamaha Bass 3X" as a 5-string Ibanez (specs: 4 strings); 142 "Korg Synth 1 Pro" as a Roland with 88 keys (specs: 61); 143 "Nord Synth 2 Pro" as a Nord Stage piano (specs: synthesizer). Name and specs agree with each other, so they are treated as the truth.
- **Categories without products**: woodwinds, brass and orchestral strings (categories 6–8) have no products at all.
- The manual mentions "more than 300 instruments", but the CSV has 65.

### Promotions
- Products with **more than one promotion** (93, 96, 99), all inactive. If two were ever active for the same product, a rule is needed (the manual says promotions do not stack).
- Seasonal campaign names ("Black Friday", "Páscoa") but no dates → `is_active` is the only source of truth.

### Orders
- **`total_brl` differs from the sum of the items** in some orders:
  - order 3: 2 × product 130 (R$ 1,749) = R$ 3,498, but the total is R$ 3,450;
  - order 20: products 107 (R$ 799) + 84 (R$ 689) = R$ 1,488, but the total is R$ 1,400.
  Likely a discount or a price at the time of purchase. **Use `total_brl` as the amount charged**; do not recompute.
- There is no actual delivery date, only `estimated_delivery` → this affects the 7-day withdrawal right, which counts "from receipt".
- `confirmed` / `pending` / `cancelled` orders have no tracking code (consistent).
- Order 8 is `shipped` with an estimated delivery of 2026-02-28, already in the past → a delay to flag.

### Customers
- **Duplicated e-mail**: customers 11 (Bruno Carvalho Martins) and 43 (Bruno Martins) share `bruno.martins@jmail.com`.
- Similar names (e.g. 13 Diego Fernandes Castro × 47 Diego Castro, different e-mails).
- Not every customer has orders.

### Policy manual (PDF)
- **E-mail with an accent** in §1.2 (`contato@empóriodamusica.com.br`), without it on the cover (`contato@emporiodamusica.com.br`).
- **Two phone numbers**: (67) 3341-4444 (cover and §1.2, "Phone / WhatsApp") × (67) 3321-4500 (§7, "WhatsApp channel").
- Confusing installment rule: "up to 3x with no minimum installment (except below R$ 50.00)", while the table says "minimum installment R$ 100.00" for credit in general.
- Text extraction with `pypdf` returns one word per line and loses table structure → **handled**: a curated Markdown version (`data/processed/policies.md`, one section per topic) is validated against the PDF by `scripts/validate_policies.py` (all numbers present, ~92% word coverage; the rest are paraphrases).

## Open decisions

Candidates for the README **Assumptions** section:

1. **"Today's" date**: orders go up to Mar/2026. Use the real system date or a fixed reference date?
2. **Order receipt date**: use `estimated_delivery` as the receipt date for `delivered` orders?
3. **Customer identification (LGPD)**: require order number + e-mail/phone before showing order data?
4. **Availability**: only `status = active` and `stock_quantity > 0` count as "available"? How to present `coming_soon` and `discontinued`?
5. **Promotional prices**: show original price + discount % + final price (required by §6.2); the PIX 5% discount does not stack with promotions.
6. **Conflicting contacts**: which phone/e-mail to give the customer.
7. **Out of scope**: accessories are politely redirected (§7.1); topics unrelated to the store get a polite refusal.
8. **Holidays**: the manual says "closed on holidays" but does not list them.
