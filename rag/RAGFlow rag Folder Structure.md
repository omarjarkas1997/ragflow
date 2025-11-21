# RAGFlow `/rag/` Folder Structure

## Core Directories

### `/app/` - Document Type Parsers (14 files)
**Purpose:** Specialized parsers for different document types

- `naive.py` (33KB) - Default parser, handles PDF/DOCX/Excel with multiple strategies (DeepDOC/PlainText/MinerU/TCADP)
- `book.py` - Long documents with TOC, hierarchical chunking
- `table.py` - Excel/CSV with complex headers, merged cells
- `paper.py` - Academic papers (abstract extraction, citation handling)
- `qa.py` - Q&A pairs extraction from docs
- `resume.py` - Structured data extraction (dates, companies, skills)
- `manual.py` - Technical manuals with hierarchical sections
- `laws.py` - Legal documents, regulation text
- `presentation.py` - PPT/PDF slides
- `email.py` - EML/MSG parsing
- `audio.py`, `picture.py` - Media files
- `one.py` - Single-chunk per document
- `tag.py` - Auto-tagging content

**Key for finance:** `table.py` (financial statements), `naive.py` (flexible base)

---

### `/flow/` - Pipeline Components
**Purpose:** Modular processing pipeline (like LangChain but custom)

```
flow/
├── base.py - Component base classes
├── pipeline.py - Orchestration engine
├── parser/ - Document parsing step
├── splitter/ - Chunking step
├── tokenizer/ - Embedding step
├── extractor/ - LLM-based extraction
└── hierarchical_merger/ - Smart chunk merging
```

**Pattern:** File → Parser → Splitter → Tokenizer → Store

Each has `schema.py` (input validation) + main logic file

---

### `/nlp/` - NLP Core (7 files)
**Purpose:** Search, tokenization, query processing

- `search.py` (27KB) - **Most important**
  - `Dealer` class: hybrid search (BM25 + vector)
  - Reranking logic
  - Citation insertion
  
- `rag_tokenizer.py` (19KB) - Custom tokenizer
  - Handles Chinese/English mixed text
  - NER integration, synonym expansion
  
- `query.py` - Query enhancement (stop words, synonyms, field boosting)
- `term_weight.py` - TF-IDF-like weighting
- `synonym.py` - Synonym lookup
- `surname.py` - Chinese name recognition
- `__init__.py` (27KB) - Utility functions (chunking strategies, bullet detection)

---

### `/llm/` - Model Integrations (7 files)
**Purpose:** Abstraction layer for various LLM providers

- `chat_model.py` (78KB) - 30+ chat models (OpenAI, Anthropic, Ollama, etc.)
- `embedding_model.py` (35KB) - Embedding APIs
- `cv_model.py` (38KB) - Vision models (OCR, image-to-text)
- `rerank_model.py` - Reranking models (Cohere, Jina)
- `sequence2txt_model.py` - Speech-to-text
- `tts_model.py` - Text-to-speech

---

### `/prompts/` - Prompt Templates (33 files)
**Purpose:** Reusable prompts for RAG tasks

Key ones:
- `generator.py` (31KB) - Main RAG answer generation
- `citation_prompt.md` - Citation formatting
- `toc_*.md` - Table of contents extraction
- `question_prompt.md` - Query refinement
- `keyword_prompt.md` - Keyword extraction
- `summary4memory.md` - Conversation summarization

---

### `/utils/` - Infrastructure Connectors (15 files)
**Purpose:** Storage, databases, caching

- `es_conn.py`, `opensearch_conn.py` - Elasticsearch/OpenSearch
- `infinity_conn.py` - Infinity vector DB
- `minio_conn.py`, `s3_conn.py`, `oss_conn.py` - Object storage
- `redis_conn.py` - Caching/state
- `doc_store_conn.py` - Abstraction for vector DBs
- `file_utils.py` - File operations

---

### `/svr/` - Background Services (4 files)
**Purpose:** Async processing, data sync

- `task_executor.py` (47KB) - Main async task runner
- `sync_data_source.py` - Data source syncing (S3, databases)
- `discord_svr.py` - Discord bot integration
- `cache_file_svr.py` - File caching

---

### `/res/` - Data Resources (4 files)
**Purpose:** NLP dictionaries and models

- `huqie.txt` (8MB) - Chinese word frequency dictionary
- `huqie.txt.trie` (55MB) - Trie index for fast lookup
- `ner.json` (235KB) - Named entity recognition data
- `synonym.json` (268KB) - Synonym mappings

---

### Root Files

- `raptor.py` (9KB) - RAPTOR implementation (recursive summarization)
- `benchmark.py` (14KB) - Testing on MS-MARCO, TriviaQA, MIRACL
- `settings.py` - Configuration
- `__init__.py` - Package initialization

---

## For Finance RAG - Priority Order

1. **Copy directly:** `/app/table.py`, `/nlp/search.py`
2. **Study patterns:** `/app/naive.py`, `/nlp/__init__.py` (chunking)
3. **Adapt concepts:** `/prompts/citation_prompt.md`, `/flow/parser/`
4. **Skip:** `/svr/`, most of `/utils/`, `/flow/pipeline.py`

The modular design in `/flow/` is interesting but you'll get more flexibility with LangChain's equivalent.