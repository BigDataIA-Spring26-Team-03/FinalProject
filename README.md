# TariffIQ: A Conversational US Import Tariff Intelligence Platform

**Course:** DAMG 7245 - Big Data and Intelligent Analytics (Team 3)  
**Institution:** Northeastern University, College of Engineering — Spring 2026

---

## Attestation

> WE ATTEST THAT WE HAVEN'T USED ANY OTHER STUDENTS' WORK IN OUR ASSIGNMENT AND ABIDE BY THE POLICIES LISTED IN THE STUDENT HANDBOOK.

- Ayush Fulsundar
- Ishaan Samel
- Vaishnavi Srinivas

---

| Resource | Link |
|---|---|
| 📹 Demo Video | [YouTube](https://youtu.be/6i6KgKRNOPs) |
| 📋 Proposal Document | [Google Docs](https://docs.google.com/document/d/17Li9KOo8oT_stR5Ub6cVK2EzPJdUgTTmyNiLRfbTfdI/edit?usp=sharing) |
| 🧪 CodeLabs | [Codelab Preview](https://codelabs-preview.appspot.com/?file_id=1yQYEhEw4kgdSCLw9ahbBzbuS6SimOu1LME1asgVXb98#0) |
| 🏗️ Architecture Diagram | [View Diagram](#architecture) |

## Table of Contents

- [Background](#background)
- [Objective](#objective)
- [Scope](#scope)
- [Problem Statement](#problem-statement)
- [System Design](#system-design)
- [Data Sources](#data-sources)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Data Processing & Transformation](#data-processing--transformation)
- [LLM Integration Strategy](#llm-integration-strategy)
- [Guardrails and Human-in-the-Loop](#guardrails-and-human-in-the-loop)
- [Evaluations & Testing](#evaluations--testing)
- [Milestones & Timeline](#milestones--timeline)
- [Team Roles & Responsibilities](#team-roles--responsibilities)
- [Risks & Mitigation](#risks--mitigation)
- [Expected Outcomes & Metrics](#expected-outcomes--metrics)
- [Token & Cost Report](#token--cost-report)
- [Conclusion](#conclusion)
- [References](#references)

---

## Background

US import tariffs have never been more volatile. Between 2018 and 2026, the government imposed Section 301 tariffs on over $370 billion of Chinese goods, Section 232 tariffs on steel and aluminum, IEEPA across-the-board tariffs, and country-specific reciprocal rates under 2025 executive orders. Keeping up with these changes manually is no longer realistic for most businesses.

The information needed to answer a basic sourcing question exists across three government systems: duty rates in the USITC Harmonized Tariff Schedule, legal context in the Federal Register, and trade flow data from the Census Bureau. None of these systems connect to each other. Getting a complete answer requires visiting all three, knowing where to look, and synthesizing the results yourself. Most procurement teams do not have time for that, and smaller businesses often cannot do it at all.

Our preliminary data validation confirmed this gap is consequential. US imports of Chinese machinery under Chapter 84 dropped from $7.01 billion per month in June 2024 to $2.89 billion in June 2025, a 62% decline directly traceable to IEEPA tariff escalations documented in Federal Register notices from the same period.

TariffIQ connects all three sources through a conversational multi-agent interface that any procurement professional can query in plain English, with no trade law background required.

---

## Objective

The goal is to build a conversational multi-agent RAG system that lets procurement professionals query US import tariff information in plain English and get accurate, cited answers in seconds.

**Big Data Engineering Component** — Ingest the complete USITC HTS schedule of 35,733 product codes including Chapter 99 special tariff codes, Federal Register tariff notices from 2018 to present, and Census Bureau monthly trade flow data for all US trading partners. Orchestrated through Apache Airflow and persisted in Snowflake.

**Significant LLM Use** — A LangGraph six-agent sequential pipeline where specialist agents handle query understanding, product classification, rate retrieval, policy context via RAG, trade flow analysis, and answer synthesis. Claude powers LLM-dependent agents via LiteLLM.

**Cloud-Native Architecture** — Snowflake as the single source of truth. ChromaDB as an ephemeral vector index rebuilt from Snowflake on startup. All services containerized via Docker Compose and deployed on GCP. FastAPI exposes all components as a tool registry callable by LangGraph agents.

**User-Facing Application** — A Streamlit chat interface where analysts ask questions in plain English and receive cited answers traceable to specific HTS codes, Federal Register document numbers, or Census data points.

---

## Scope

### In-Scope

- Complete USITC HTS ingestion including Chapter 99 special tariff program codes
- Federal Register tariff notices from 2018 to present, full text ingested, HTS codes extracted via spaCy EntityRuler, chunks embedded into ChromaDB
- Census Bureau HS6 import volumes queried live at query time, no bulk storage
- Six-agent LangGraph pipeline: Query, Classification, Rate, Policy, Trade, Synthesis
- Two HITL triggers: classification confidence below 80%, citation failure on synthesized answer
- Two ChromaDB collections with hybrid BM25 + dense + RRF retrieval
- Streamlit interface with inline citations and downloadable sourcing brief

### Out-of-Scope

- Tariffs other countries impose on US exports
- Anti-dumping and countervailing duties
- CBP binding classification rulings
- Tariff rate quotas
- Export controls and ITAR
- Legal advice or binding classification rulings

---

## Stakeholders / End Users

- **Procurement managers** seeking conversational tariff intelligence to compare duty rates across sourcing countries and make faster, data-driven buying decisions
- **Trade compliance officers** needing accurate, cited tariff information with legal policy context to ensure import regulatory compliance
- **Supply chain analysts** wanting to understand real-world trade flow shifts caused by tariff escalations and identify alternative sourcing markets
- **Small and mid-sized importers** looking for a free alternative to expensive paid trade intelligence platforms to assess their tariff exposure across product categories

---

## Problem Statement

### Current Challenges

**Data Fragmentation** — A complete tariff answer requires three databases that were never designed to work together. The USITC HTS has duty rates but no legal context. The Federal Register has legal context but no rates. The Census Bureau has trade volumes but neither. A procurement manager comparing sourcing options for steel pipes must manually query all three, find the relevant documents, and synthesize the answer themselves.

**Manual Workflows That Do Not Scale** — A procurement team reviewing 20 product categories across 5 sourcing countries faces 100 individual research tasks every time tariff policy shifts. With policy changing at the current pace, most teams cannot keep up.

**No Connection Between Policy and Trade Impact** — Knowing a tariff rate is 25% is useful. Knowing that imports from that country dropped 60% after that rate was imposed is actionable. The Census Bureau data answers the second question and connects it to the specific Federal Register action that caused the shift.

**LLM Hallucination Risk** — General purpose LLMs cannot reliably answer tariff questions. Duty rates, HTS codes, and effective dates change frequently and carry real financial consequences if wrong. A system that lets an LLM generate rates from memory rather than verified government records is not usable for business decisions.

### Opportunities

TariffIQ addresses these challenges by providing:

- **Unified Data Pipelines:** Automated ingestion from all three sources into a single Snowflake platform, eliminating the manual multi-system research workflow.
- **LLM-Assisted Product Classification:** A three-layer pipeline that translates plain English product descriptions into precise HTS codes using alias lookup, Census Schedule B API, and ChromaDB semantic search.
- **Real-Time Policy Monitoring:** Federal Register ingestion that detects new tariff notices, extracts affected HTS chapters via spaCy EntityRuler, and re-indexes relevant policy context automatically.
- **Cited, Grounded Answers:** Every factual claim is backed by a specific primary source record, eliminating hallucination risk for tariff-specific facts while keeping the interface conversational.

---

## Data Sources

| Source | Type | Purpose |
|--------|------|---------|
| USITC Harmonized Tariff | Government REST API | Product classification, base MFN duty rates, FTA preferential rates, and footnote cross-references to additional tariff programs |
| Federal Register (USTR Notices) | Government REST API | Legal text behind every tariff action — Section 301, Section 232, IEEPA, and reciprocal tariffs — with effective dates and HTS code references |
| Census Bureau Trade Data | Government REST API | Actual US import volumes by product and country of origin to track real-world trade flow shifts caused by tariff escalations |

Sample Federal Register Document: https://www.federalregister.gov/documents/2025/12/29/2025-23912/notice-of-action-chinas-acts-policies-and-practices-related-to-targeting-of-the-semiconductor

---

## Technology Stack

| Layer | Technology | Description |
|-------|-----------|-------------|
| Cloud | Google Cloud Platform | Native integration across all services, and a fully managed infrastructure that eliminates local machine dependency |
| Data Warehouse | Snowflake | Used for storing and querying both HTS product classifications |
| Pipeline Orchestration | Apache Airflow | Three independent DAGs with separate failure domains. Mature retry and SLA monitoring |
| Backend API | FastAPI | Async performance, automatic OpenAPI schema generation, tool registry for LangGraph agents |
| Vector Store | ChromaDB | Two collections for policy and reference RAG |
| LLM | LiteLLM with Claude and OpenAI | Multi provider LLM routing framework that enables automatic fallback from Claude to OpenAI if a provider is unavailable |
| Caching | Redis | Semantic cache before every LLM call |
| Frontend | Streamlit | Conversational chat with citation display and sourcing brief download |
| Containerization | Docker Compose | All services in a single compose file |

---

## Architecture

### Design Decisions

Before committing to the final design, two distinct architectures were evaluated and prototyped.

**Option A: Text-to-SQL with LLM Synthesis**

Store all HTS codes and rates in a relational database. LLM converts natural language product descriptions directly into SQL queries. SQL returns the rate. LLM synthesizes the answer with Federal Register RAG context added.

The SQL-for-rates instinct is correct and carried forward into the final design. But text-to-SQL fails at the classification step for this specific domain. HTS legal descriptions use highly specialized terminology that does not map to plain English. The word "laptop" does not appear anywhere in the HTS schedule. The correct code 8471.30 is described as "portable automatic data processing machines, weighing not more than 10 kg." A text-to-SQL approach that tries to match "laptop" directly against HTS descriptions fails before it reaches the rate lookup. Lacks the columnar time-series query capability needed for Census trade flow trend analysis across millions of monthly records. **Rejected.**

**Option B: Single LLM Agent with Tool Calls**

One agent makes sequential tool calls for classification, rate lookup, policy retrieval, and synthesis.

A single agent has no clean enforcement boundary between LLM reasoning and SQL fact. There is no reliable way to prevent the agent from generating a rate from memory instead of from a verified SQL result. For tariff data, that boundary is non-negotiable. **Rejected.**

**Final Design: Six-Agent Sequential Pipeline**

| Decision | Chosen | Rejected | Reason |
|----------|--------|----------|--------|
| Database | Snowflake | PostgreSQL | Columnar storage, VARIANT columns |
| Vector store | ChromaDB | Pinecone | Free, local, no external dependency |
| Entity extraction | spaCy EntityRuler | Regex | Named entity labels, handles all HTS format variants |
| Orchestration | Airflow | Prefect / cron | Mature retry and SLA support |

---

## Data Processing & Transformation

### Batch vs. Stream Processing

All three sources use scheduled batch processing via Airflow DAGs.

### Data Formats

- **Raw:** JSON (USITC API, Federal Register API, Census API), HTML (Federal Register document bodies)
- **Storage:** Snowflake TEXT, VARIANT (raw JSON), NUMBER, DATE — ChromaDB for vector index

### Storage Schemas

**HTS_CODES:** `hts_id`, `hts_code`, `stat_suffix`, `chapter`, `section_number`, `level`, `description`, `general_rate`, `special_rate`, `other_rate`, `units`, `indent_level`, `is_header_row`, `footnotes`, `raw_json`, `loaded_at`

**FEDERAL_REGISTER_NOTICES:** `document_number`, `title`, `publication_date`, `document_type`, `agency_names`, `abstract`, `full_text`, `html_url`, `body_html_url`, `char_count`, `chunk_count`, `raw_json`, `ingested_at`

**NOTICE_HTS_CODES:** `document_number`, `hts_code`, `hts_chapter`, `context_snippet`

**CENSUS_TRADE_DATA:** `hs_code`, `hs_chapter`, `comm_lvl`, `commodity_desc`, `country_code`, `country_name`, `year`, `month`, `period`, `import_value_usd`, `import_quantity`, `loaded_at`

---

## LLM Integration Strategy

### Prompt Design

**Query Agent system prompt:**
```
You are a query parser for a US tariff platform. Extract the product and country and correct any spelling. Return only JSON: {"product": "...", "country": "..."}
```

**Policy Agent system prompt:**
```
You are a US trade policy analyst. Answer the user's question using only the Federal Register excerpts provided. Cite the exact document number in parentheses for every factual claim. If the context is insufficient, say so explicitly. Do not use knowledge of tariff rates or policy outside the provided documents.
```

**Synthesis Agent system prompt:**
```
You are a trade sourcing analyst. Generate a sourcing brief in the required JSON schema from the structured inputs provided. Every rate claim must reference a Snowflake record ID. Every policy claim must reference a Federal Register document number. Do not generate tariff rates, dates, or policy facts from memory.
```

### RAG Pipeline

The Policy Agent uses three steps before every LLM call:

1. **HyDE:** A hypothetical Federal Register sentence is generated and embedded as the query vector, improving recall for products with unusual HTS terminology.
2. **Pre-filtered retrieval:** ChromaDB query is filtered to the confirmed HTS chapter from Agent 2.
3. **BM25 + Dense + RRF:** Keyword matching combined with semantic retrieval, fused via Reciprocal Rank Fusion into a final top-k result set.

---

## Guardrails and Human-in-the-Loop

- **Input validation:** Query Agent checks for a recognizable product reference before the pipeline runs. Prompt injection patterns are rejected before the LLM call.
- **Citation enforcement:** Synthesis Agent output is validated against a `CitedTariffResponse` Pydantic model. Every rate claim needs a Snowflake record ID. Every policy claim needs a Federal Register document number. Both are confirmed to exist in Snowflake before the response is accepted. Failures go to HITL, not to the user.
- **Hallucination prevention:** Rate data comes from SQL with record IDs, not from LLM generation. The Pydantic validator enforces this at the schema level regardless of what the LLM outputs.
- **HITL Trigger 1:** Classification confidence below 0.80 after all three layers. Human confirms or corrects via Streamlit queue. Confirmed codes written back to `product_aliases`.
- **HITL Trigger 2:** Citation validation failure on synthesized answer. Failure written to `hitl_records` for human review.

---

## Evaluations & Testing

### LLM Evaluation Framework

**Rubric-Based Evaluation:**

- **HTS Accuracy (1–5):** Does the response return the correct subheading-level HTS code?
- **Rate Accuracy (1–5):** Is the effective duty rate correct including Federal Registry adders?
- **Citation Grounding (1–5):** Does the response cite a real, retrievable Federal Register document number?
- **Completeness (1–5):** Does the response address all parts of the query (product, rate, policy, trade volume)?

**Automated Graders:**

- Use Claude as judge to score agent outputs against the rubric
- Compare against a golden set of 30 manually labeled queries covering all three agent types (classification, policy, trade)
- Any response returning a hallucinated document number or incorrect rate fails automatically regardless of overall score

**Golden Set Examples:**

- `"What is the tariff on solar panels from China?"` → HTS 8541.40, 50% Section 301
- `"Has the Section 301 rate on steel changed since 2018?"` → FR doc 2018-XXXXX, 25%
- `"How much furniture did the US import from Vietnam in 2024?"` → Census HS Chapter 94, $X billion

### Unit Tests (pytest)

- **ETL:** Test HTS level detection from code string, `IS_HEADER_ROW` flagging for empty `htsno`, BeautifulSoup HTML stripping, idempotent Snowflake inserts, HTS regex extraction with no false positives
- **API:** Test Census 204 returns None without raising, Federal Register pagination follows `next_page_url` until null, USITC `exportList` returns list of dicts with expected fields
- **LLM Wrappers:** Mock LLM responses, test prompt construction per agent type, test confidence score is between 0.0 and 1.0, test citation extractor regex finds FR document numbers in response text

### Integration Tests

- **End-to-end workflow:** Input product query → verify HTS code returned → verify policy document cited → verify trade volume fetched from Census live API
- **Three-source join:** Run demo query against test Snowflake schema (`TARIFFIQ_TEST`) and verify result contains non-null values for `GENERAL_RATE`, `POLICY_DOC`, and `IMPORT_VALUE_USD`
- **Guardrails:** Trigger HITL gate with a low-confidence classification (below 80%) and verify query is routed to review queue rather than returned to user
- **RAG retrieval:** Send a known query and verify returned chunks contain a document number that exists in `FEDERAL_REGISTER_NOTICES`

### Metrics

- **Accuracy:** HTS classification accuracy, effective rate accuracy (±0.5% tolerance), citation grounding rate, hallucination rate (target: 0%)
- **Cost:** LLM tokens per query logged via LiteLLM, estimated USD cost per query, Redis semantic cache hit rate
- **Throughput:** Queries per minute under load, DAG run duration per source, embedding batch processing time per 100 chunks

---

## Milestones & Timeline

**Project Duration:** April 4, 2026 — April 24, 2026 (3 weeks)

| Milestone | Description | Key Deliverables |
|-----------|-------------|-----------------|
| M1: Data Infrastructure | Data ingestion & storage setup for all three sources | USITC HTS → Snowflake, Federal Register → Snowflake, Census, Airflow DAGs scaffolded |
| M2: Big Data Processing | Chunking, embedding, and vector index construction | HTS-anchored chunking, ChromaDB collections, Great Expectations validation suite |
| M3: LLM Agent Development | LangGraph multi-agent pipeline implementation | 6 agents (Query, Classification, Rate, Policy, Trade, Synthesis), LiteLLM routing, Redis semantic cache |
| M4: Guardrails & Safety | Input/output validation and HITL gates | Input scope classifier, hallucination detection, confidence scoring, HITL escalation queue, Pydantic citation enforcement |
| M5: Backend APIs | FastAPI endpoints and MCP server | REST API (POST /query, GET /hts/:code), MCP server with 8 typed tools, Snowflake + Census query wrappers |
| M6: Frontend Application | Streamlit conversational interface | Chat UI, HTS code explorer, Sourcing Brief panel, Sourcing Risk Score (SRS) display |
| M7: Cloud Deployment | Containerization and CI/CD pipeline | Docker Compose, GitHub Actions CI/CD, Prometheus + Grafana (3 alert rules), structlog |
| M8: Testing & Evaluation | Unit tests, integration tests, LLM eval | pytest suite (80% coverage), 25-query golden set, Claude-as-judge grader |
| M9: Final Polish | Documentation, demo prep, submission | README, architecture diagrams, 5-query demo script, proposal finalized |

| Milestone | Week 1 (Apr 4–10) | Week 2 (Apr 11–17) | Week 3 (Apr 18–25) |
|-----------|-------------------|---------------------|---------------------|
| M1: Data Infrastructure | ██████ | | |
| M2: Big Data Processing | ███ | ███ | |
| M3: LLM Agent Development | | ██████ | |
| M4: Guardrails & Safety | | ████ | ██ |
| M5: Backend APIs | | ███ | ███ |
| M6: Frontend Application | | | ██████ |
| M7: Cloud Deployment | | | ██████ |
| M8: Testing & Evaluation | | ██ | ████ |
| M9: Final Polish | | | ███ |

**Week 1 (Apr 4–10) — Data Foundation:** All three data sources connected and queryable. Snowflake tables populated. Airflow DAGs scaffolded. ChromaDB collections built and validated. Project unblocked for agent development.

**Week 2 (Apr 11–17) — Intelligence Layer:** LangGraph agent pipeline operational end-to-end. LiteLLM routing, Redis cache, guardrails, and HITL escalation in place. FastAPI backend serving initial endpoints. Evaluation framework started.

**Week 3 (Apr 18–25) — Integration & Delivery:** Streamlit frontend connected to backend. Docker Compose deployment working. CI/CD pipeline active. Full test suite passing. Golden set evaluation complete. Demo script ready. Proposal submitted.

---

## Team Roles & Responsibilities

| Role | Owner |
|------|-------|
| ETL Lead | Ishaan |
| Cloud Architect | Ayush |
| LLM Engineer | Ayush |
| QA/Test Engineer | Vaishnavi |
| Documentation Lead | Vaishnavi |
| Frontend Lead | Ishaan |

---

## Risks & Mitigation

### Potential Risks

| Risk | Impact | Likelihood | Severity |
|------|--------|-----------|----------|
| 1. LLM Hallucination | Incorrect duty rates or fake document citations | High | Critical |
| 2. High LLM API Costs | Budget overrun | Medium | High |
| 3. HTS Classification Failure | Wrong product code, wrong rate returned | Medium | Critical |
| 4. Census API Returns No Data (HS8) | Trade volume unavailable for specific codes | High | Medium |
| 5. Data Inconsistency Across Sources | Mismatched HTS codes between Source 1 and Source 2 | Medium | Medium |
| 6. ChromaDB Cold Start Latency | Slow startup on fresh deployment | Low | Medium |
| 7. Latency Issues | Query takes >8 seconds end-to-end | Medium | Medium |

### Mitigation Strategies

**1. LLM Hallucination:**
- Enforce structured output with Pydantic schemas on Synthesis Agent
- Output guardrail validates every cited document number against `FEDERAL_REGISTER_NOTICES` before response is returned
- Hallucinated citations trigger automatic HITL escalation — never reach the user
- Rate Agent uses pure SQL for duty rate lookups

**2. High LLM API Costs:**
- Redis semantic cache before every LLM call — target 40–60% hit rate
- LiteLLM token logging per query with Grafana spend threshold alert
- GPT-4o used only as fallback on Claude rate limit, not as primary

**3. HTS Classification Failure:**
- Three-layer classification: keyword match → synonym expansion → fuzzy fallback
- Confidence score below 80% triggers HITL escalation before response is returned
- Golden set evaluation identifies systematic misclassification patterns for prompt tuning

**4. Census API Returns No Data:**
- HS8 excluded by design — confirmed broken during validation, HS6 is the maximum granularity
- HTTP 204 handled gracefully — returns None, logs warning, continues pipeline without crashing
- Trade Agent reports "data suppressed" rather than zero to avoid misleading users

**5. Data Inconsistency Across Sources:**
- HTS codes extracted from Federal Register are validated against `HTS_CODES` table via `match_to_source1()`
- Unmatched codes flagged in `NOTICE_HTS_CODES` rather than silently dropped
- Great Expectations suite enforces null checks, range validation, and duplicate detection on every DAG run

**6. Latency Issues:**
- Federal Register HTML fetches parallelized with thread pool of size 8
- Redis cache absorbs repeated queries — no LLM call on cache hit
- Policy Agent and Trade Agent run in parallel within LangGraph pipeline

---

## Expected Outcomes & Metrics

### KPIs

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| HTS Classification Accuracy | 80%+ correct subheading-level code | Golden set of 30 labeled queries, automated grader |
| Rate Accuracy | 90%+ correct effective duty rate | Compare against manually verified rates |
| Hallucination Rate | <5% of responses flagged | Output guardrail + document number validator |
| End-to-End Latency | P95 under 8 seconds | End-to-end timestamp logging via structlog |
| Cost per Query | <$0.10 in LLM tokens | LiteLLM token logging + Grafana spend dashboard |
| Redis Cache Hit Rate | 40–60% of LLM calls served from cache | Redis hit/miss counters logged per request |

### Expected Benefits

**Technical Benefits**

- **Unified multi-source knowledge base.** TariffIQ AI is the first system to combine USITC product classifications, Federal Register policy documents, and Census Bureau trade statistics into a single queryable knowledge base. Each source answers a different dimension of a tariff query — what the product is, what the policy says, and how much trade is actually flowing — and no existing tool combines all three.
- **RAG over structured government data.** The HTS-anchored chunking strategy ensures that every embedded chunk contains the specific policy language surrounding a tariff code, not arbitrary text windows. This produces higher retrieval precision than naive chunking and demonstrates a generalizable pattern for RAG over regulatory corpora.
- **Production-grade agent pipeline.** The six-agent LangGraph architecture with LiteLLM routing, Redis semantic caching, Pydantic citation enforcement, and HITL escalation represents a complete, observable, cost-controlled agentic system — not a prototype. The Redis cache alone is projected to reduce LLM spend by 40–60% at steady-state query volume.

**Business Benefits**

- **Immediate value for importers and trade professionals.** A customs broker, procurement manager, or trade compliance officer can ask "what is the effective tariff on Vietnamese furniture?" and receive a cited, accurate answer in under 8 seconds — a task that currently requires cross-referencing three separate government websites manually, taking 20–30 minutes per query.
- **Timeliness in a high-volatility tariff environment.** With over 40 new USTR tariff notices published in 2025 alone and IEEPA actions still being issued in early 2026, tariff information goes stale within weeks. TariffIQ's daily Federal Register ingestion ensures the knowledge base reflects the most current policy without manual update.
- **Sourcing Risk Score as a decision tool.** The SRS output gives procurement teams a single actionable number summarizing exposure — combining base rate, Section 301 adder, trade volume trend, and policy volatility — that can be compared across suppliers and countries. This is the kind of output that feeds directly into sourcing decisions, not just research.
- **Scalable to additional trade programs.** Future versions can expand coverage further by integrating CBP's anti-dumping and countervailing duty (ADD/CVD) order database, which would add a fourth source covering product-specific penalty duties that sit on top of the standard Section 301 and Section 232 rates.

---

## Token & Cost Report

### Token Measurement Strategy

**Instrumentation:** Route all LLM calls through LiteLLM, capturing per-call: `input_tokens`, `output_tokens`, `cost_usd`, `latency_ms`, `cache_hit`, agent name, model, query ID, and timestamp. Log via structlog, aggregated in Grafana for per-query and daily spend dashboards.

> Rate Agent and Trade Agent never call LLM — zero token cost by design.

### Prompt Optimization Techniques

**1. Compression:**
- System prompts kept under 300 tokens per agent — declarative, no verbose explanations
- Retrieved context capped at top-5 chunks (~1,000 tokens) via re-ranker before passing to Synthesis Agent
- Structured JSON output enforced via Pydantic — eliminates conversational padding in responses

**2. Caching:**
- Redis semantic cache checks query similarity (cosine > 0.92) before every LLM call
- Cache TTL set to 24 hours — refreshed after daily Federal Register DAG run
- Expected cache hit rate: 40–60% → driven by query clustering around high-interest products (semiconductors, steel, EVs)

**3. Batching:**
- Embeddings generated in batches of 64 using Sentence Transformers — 40% faster than single-record embedding
- Federal Register DAG fetches only net-new documents — no redundant re-embedding on days with no new publications

**4. Token Budget Guardrails:**
- Hard limit: top-5 chunks passed to Synthesis Agent regardless of corpus size
- Grafana alert fires if daily LLM spend exceeds $5
- Rate lookups always served from Snowflake SQL — LLM never asked to recall numeric duty rates

### Estimated Project Cost

| Item | Cost |
|------|------|
| Claude Sonnet API (dev + testing) | ~$15–25 |
| Snowflake, Redis, ChromaDB | $0 (free tier / local) |
| Census, Federal Register, USITC APIs | $0 (public) |
| **Total** | **~$15–25** |

> Target: under $0.10 per query. Redis caching at 50% hit rate effectively doubles query capacity within the same budget.

---

## Conclusion

US tariff policy has never been more volatile — with over 40 USTR notices published in 2025 alone and IEEPA actions still being issued in 2026, the information a trade professional needs to answer "what is the effective tariff on this product from this country?" is spread across three separate government systems and takes 20–30 minutes to piece together manually.

TariffIQ AI solves this. By combining USITC HTS data, Federal Register policy documents, and Census Bureau trade statistics into a single conversational RAG system, it delivers cited, accurate tariff intelligence in under 8 seconds — grounded in real government data and traceable to its source documents.

For DAMG 7245, TariffIQ delivers on every course objective: a production-grade big data pipeline across three live government APIs, a six-agent LangGraph system with observable cost controls, HTS-anchored vector retrieval, and a full evaluation framework with automated golden set grading. The result is a working, deployable system that addresses a real problem with real data.

---

## References

### APIs & Datasets

- United States International Trade Commission. Harmonized Tariff Schedule REST API — exportList endpoint. https://hts.usitc.gov/reststop/exportList
- United States International Trade Commission. HTS System User Guide. https://www.usitc.gov/documents/hts/hts_external_user_guide.pdf
- Office of the Federal Register. Federal Register API v1 — USTR Tariff Notices. https://www.federalregister.gov/api/v1/documents.json?conditions[agencies][]=trade-representative-office-of-united-states
- Office of the Federal Register. Federal Register — 2025 USTR Document Index. https://www.federalregister.gov/index/2025/trade-representative-office-of-united-states
- United States Census Bureau. International Trade Timeseries — Imports by HS Code. https://api.census.gov/data/timeseries/intltrade/imports/hs
- Office of the United States Trade Representative. Section 301 Tariff Actions and Exclusion Process. https://ustr.gov/trade-topics/enforcement/section-301-investigations/tariff-actions
- Office of the United States Trade Representative. Federal Register Notices. https://ustr.gov/federal-register-notices
