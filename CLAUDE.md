# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Response Rule

All claude response must be in KOREAN

## Project Overview

This is a Regulatory Intelligence Platform for the Financial Services Commission (FSC) - a Proof of Concept system designed to collect, analyze, and structure FSC decision data. The system enables natural language querying for complex regulatory trend analysis and case studies.

## System Architecture

The system is designed as a two-phase architecture:

### Phase 1: One-time Data Pipeline
- **FSC Crawler Script** (`crawler.py`): Downloads FSC decision documents in ZIP format
- **Main Processing Script** (`process.py`): Orchestrates PDF processing workflow
- **Gemini Extractor AI**: Analyzes PDFs and extracts structured JSON data
- **Gemini Validator AI**: Validates extracted data for logical/contextual accuracy
- **PostgreSQL Database**: Stores final validated structured data

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
- **PostgreSQL 15+** for data storage
- **Google Gemini 1.5 Pro API** for AI processing
- **LangChain** with langchain-google-genai for NL2SQL

### Frontend
- **Next.js** (React) with TailwindCSS
- **JavaScript** for client-side logic

### Data Processing
- **Python** libraries: requests, BeautifulSoup4 for web scraping
- **File system** storage for raw ZIP and processed PDF files

## Key File Structure (Planned)

Based on the architecture document, the expected file structure will be:

```
./
├── data/
│   ├── raw_zip/          # Downloaded ZIP files
│   └── processed_pdf/    # Extracted PDF files
├── crawler.py            # FSC website crawler
├── process.py           # Main PDF processing script
├── prompt_extractor.txt  # AI prompt for data extraction
├── prompt_validator.txt  # AI prompt for data validation
└── backend/             # FastAPI application
    └── frontend/        # Next.js web interface
```

## Development Workflow

### Data Pipeline Development
1. Implement FSC crawler to download decision documents
2. Create PDF processing pipeline with Gemini API integration
3. Set up PostgreSQL database with the defined schema
4. Implement data validation and insertion logic

### Query System Development
1. Develop FastAPI backend with SQLAlchemy ORM
2. Implement NL2SQL engine using LangChain
3. Create Next.js frontend with search interface
4. Add data visualization components

## Key Components

### PDF Processing Pipeline
- Extract text from FSC decision PDFs
- Use Gemini API to structure data according to database schema
- Validate extracted data with AI verification
- Insert validated data into PostgreSQL with transactions

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
- AI-powered data extraction and validation
- Complex NL2SQL capabilities for regulatory analysis
- Korean language support for natural language queries

The system emphasizes data accuracy through AI validation and supports complex regulatory trend analysis through sophisticated query capabilities.