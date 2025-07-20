# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Response Rule

All claude response must be in KOREAN

## Project Overview

This is a Regulatory Intelligence Platform for the Financial Services Commission (FSC) - a Proof of Concept system designed to collect, analyze, and structure FSC decision data. The system enables natural language querying for complex regulatory trend analysis and case studies.

## System Architecture

The system is designed as a two-phase architecture:

### Phase 1: One-time Data Pipeline
- **FSC Crawler Script** (`app/services/fsc_crawler.py`): Downloads FSC decision documents in ZIP format
- **PDF Processor Service** (`app/services/pdf_processor.py`): Orchestrates hybrid PDF processing workflow
- **Rule-based Extractor** (`app/services/rule_based_extractor.py`): Extracts structured data using Korean legal document patterns (95%+ accuracy)
- **Gemini Service** (`app/services/gemini_service.py`): AI enhancement for complex violation summaries and categorization
- **SQLite/PostgreSQL Database**: Stores final validated structured data with composite keys

### Phase 2: Query & Analysis System
- **Web UI** (Next.js): User interface for search and visualization
- **Backend API** (FastAPI): Handles business logic and API endpoints
- **NL2SQL Engine** (LangChain + Gemini): Converts natural language queries to SQL

## Database Schema

The system uses a PostgreSQL database with four main tables:

- **Decisions**: Core FSC decision documents with metadata
- **Actions**: Regulatory actions/sanctions linked to decisions
- **Laws**: Legal framework references
- **Action_Law_Map**: Many-to-many relationship between actions and laws

## Technology Stack

### Backend
- **Python** with FastAPI, SQLAlchemy, Pydantic
- **SQLite/PostgreSQL** for data storage with composite key architecture
- **Google Gemini 1.5 Pro API** for AI processing (with rate limiting)
- **PyPDF2** for PDF text extraction
- **LangChain** with langchain-google-genai for NL2SQL

### Frontend
- **Next.js** (React) with TailwindCSS (planned)
- **JavaScript** for client-side logic

### Data Processing
- **Rule-based Extractor**: Regex patterns for Korean legal documents
- **Python** libraries: requests, BeautifulSoup4 for web scraping
- **File system** storage for raw ZIP and processed PDF files

## Key File Structure (Actual)

```
./
├── app/
│   ├── api/v1/endpoints/     # API endpoints
│   ├── core/                 # Core settings and database
│   ├── models/              # Database models (SQLAlchemy)
│   └── services/            # Business logic
│       ├── fsc_crawler.py   # FSC website crawler
│       ├── pdf_processor.py # PDF processing orchestrator
│       ├── rule_based_extractor.py # Pattern-based extraction
│       └── gemini_service.py # AI enhancement service
├── data/
│   ├── raw_zip/             # Downloaded ZIP files (2021-2025)
│   └── processed_pdf/       # Extracted PDF files by year
├── prompts/                 # AI prompts
├── scripts/                 # Utility scripts
├── process_*.py             # Various batch processing scripts
└── verify_db_data*.py       # Data validation scripts
```

## Development Workflow

### Data Pipeline Development (Completed)
1. ✅ FSC crawler implementation - Downloads 2021-2025 decision documents (2,000+ files)
2. ✅ Hybrid PDF processing pipeline - Rule-based (95%+ accuracy) + Gemini API for complex cases
3. ✅ SQLite database with composite key schema (decision_year + decision_id)
4. ✅ Data validation and batch processing with session management

### Query System Development (In Progress)
1. ✅ FastAPI backend with SQLAlchemy ORM - Basic structure implemented
2. 🚧 NL2SQL engine using LangChain - Planned
3. 🚧 Next.js frontend with search interface - In development
4. 📋 Data visualization components - Planned

## Key Components

### PDF Processing Pipeline (Hybrid Approach)
- **Rule-based Extraction** (Primary): Regex patterns for Korean legal document standards
  - 95%+ accuracy for standard fields (decision number, dates, amounts, entity names)
  - Handles complex multi-action cases and table formats
- **AI Enhancement** (Secondary): Gemini API for complex cases
  - 2-step pipeline for documents that fail rule-based extraction
  - Complex violation summaries and categorization
- **Batch Processing**: Session management for SQLite transactions
- **Data Validation**: Comparison with original PDF text

### Natural Language Query System
- Process user queries in Korean
- Generate appropriate SQL queries for complex regulatory analysis
- Return structured results for visualization

## API Endpoints (Planned)

- `/api/search/nl2sql` - Natural language to SQL conversion endpoint
- Additional CRUD endpoints for managing decision data

## Database Categories

### Decision Categories
- **category_1**: 제재 (Sanctions), 인허가 (Licensing), 정책 (Policy)
- **category_2**: 기관 (Institutions), 임직원 (Executives), 전문가 (Professionals), etc.

### Industry Sectors
- 은행 (Banking), 보험 (Insurance), 금융투자 (Financial Investment), 회계/감사 (Accounting/Auditing)

### Action Types
- 과태료 (Fines), 직무정지 (Suspension), 인가 (Authorization), etc.

## Development Notes

This is a PoC system focused on:
- One-time data loading from FSC decision documents
- **Hybrid extraction approach**: Rule-based (primary) + AI-powered (secondary)
- Complex NL2SQL capabilities for regulatory analysis
- Korean language support for natural language queries

### Current Status (2025년 7월)
- **Data Collection**: 2,000+ FSC decision PDFs (2021-2025) downloaded
- **Data Processing**: 58/83 files processed for 2025 (69.9% completion)
- **Extraction Accuracy**: 95%+ with rule-based patterns
- **Database**: 58 decisions, 59 actions, 30 laws successfully stored
- **API Limitation**: Daily quota reached (250 requests for Gemini free tier)

### Known Issues
- **Securities PDFs**: 15 files (64-72, 80, 91-93호) cause JSON parsing errors
- **API Rate Limits**: Free tier 50 requests/day requires batch strategy
- **React Warning**: antd v5 compatibility with React 19 (non-critical)
- **SQL Dialect**: Some generated SQL uses MySQL syntax on SQLite

## Recent V2 System Updates
- Migrated from V1 to V2 schema with surrogate keys
- Implemented Gemini Structured Output for reliable extraction
- Completed full web interface with Next.js + Ant Design
- Processed 68 out of 83 (81.9%) 2025 FSC decisions
- Integrated law information display in search results