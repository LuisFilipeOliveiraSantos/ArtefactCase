# Technical Case — AI Engineer (Artefact)

English summary of the case brief (originally in Portuguese) and of the recruiter's email, written as a checklist.

## Selection process context

- Role: **AI Engineer – Full-Stack para Aplicações com IA Generativa** (São Paulo office, fully remote).
- Stages: **written case (this repo)** → fit interview → technical interview 1 → technical interview 2 → chat with partners.
- Guidance from the email: the case assesses logical reasoning and **should be solved in the simplest way possible**.

## Submission rules

- [ ] **Deadline:** end of the 2nd business day after 2026-10-31 (Saturday) → **2026-11-03, 23:59**.
      (If the Nov 2 holiday, Finados, is not counted, it would be 2026-11-04. Plan for Nov 3; confirm with the recruiter if needed.)
- [ ] **All responses in English.**
- [ ] Submit a **PDF** through the Google Form (logged in with a Gmail account), containing the public repository link.
- [ ] PDF file name: `Luis Filipe Oliveira Santos - AI Engineer – Full-Stack para Aplicações com IA Generativa.pdf`
- [ ] **Do not change anything in the repository after the deadline.**

## Mission

Prototype a **text-message customer service agent** for Empório da Música that helps the staff with recurring
questions: opening hours, order status, product price and availability, etc.

**Only mandatory technical constraint:** Python as the main language.

Evaluation focus: **logic, clarity and initiative** — *how* the problem is solved and *why* each decision was
made matter more than a perfect solution.

## Provided materials

| File (in this repo) | Content |
|---|---|
| `data/raw/products.csv` | 65 products: price, category, stock, status, specs as JSON |
| `data/raw/categories.csv` | 9 categories |
| `data/raw/promotions.csv` | 25 promotions with an `is_active` flag |
| `data/raw/orders.csv` | 20 orders: status, total, payment, tracking, estimated delivery |
| `data/raw/order_items.csv` | items of each order |
| `data/raw/customers.csv` | 50 customers: name, phone, e-mail, city |
| `data/raw/politicas_da_loja.pdf` | store policy manual (8 pages, Portuguese) |

> Using every file is not mandatory: use whatever gives the best customer experience.

## Agent requirements

- [ ] Adopt a **persona** aligned with the store's identity and tone ("informal but professional", manual §7.1)
- [ ] Receive and answer messages based on the provided context
- [ ] Know **when to query data** (availability, prices, order status)
- [ ] Know **when to query policies** (exchanges, opening hours, payment methods)
- [ ] Properly handle **out-of-scope** questions (e.g. accessories, topics unrelated to the store)

## Decisions to be justified in the README

- [ ] Framework / approach (RAG, function calling, ReAct, SQL agent, hybrid…)
- [ ] Model and provider (paid or free, local or API)
- [ ] Interface (CLI, notebook, API or simple UI)
- [ ] Conversation history persistence (if it makes sense)
- [ ] Data handling

## Deliverables

1. **Public Git repository** on GitHub
   - [ ] Commit history showing real progress (**no single squashed / force-pushed commit**)
   - [ ] Each commit leaves the project in a working state
2. **README.md**
   - [ ] Full instructions to run (environment, model provider, commands)
   - [ ] Rationale for technical decisions (framework, LLM, retrieval, prompt)
   - [ ] Known limitations and what would be done with more time
   - [ ] Use of coding assistants: which tool and how it was used in the workflow
   - [ ] Assumptions made where the brief is ambiguous
3. **Interaction examples** in `examples/`
   - [ ] Between **3 and 5** conversations (`.md`, `.txt` or image) covering varied scenarios
   - [ ] At least one **non-trivial** one (live data lookup or policy application)

### Scenarios suggested in the brief

| Question (customer, in Portuguese) | Type |
|---|---|
| "Quais opções de violões disponíveis custando até R$1000?" — acoustic guitars available up to R$1000 | catalog (data) |
| "Qual o endereço da loja?" — store address | general info (policy) |
| "Quanto custa o Takamine GD20?" — price of a product | price (data) |
| "Me arrependi da minha compra, posso devolver meu pedido?" — can I return my order? | return policy + order data |
