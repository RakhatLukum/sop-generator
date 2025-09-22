# SOP Generator Deployment Guide

## Streamlit Cloud Deployment

### 1. App Configuration
- **Main file path**: `sop_generator/app.py`
- **Python version**: 3.8+

### 2. Required Environment Variables
Set these in your Streamlit Cloud app settings:

```
API_KEY=your-api-key-here
OPENAI_BASE_URL=https://llm.govplan.kz/v1
```

### 3. Dependencies
The app will automatically install dependencies from `requirements.txt`.

### 4. Optional Features
Some features require additional system dependencies:
- **PDF OCR processing**: Requires `poppler-utils`, `tesseract-ocr`
- **Advanced visualizations**: Requires `plotly`
- **PDF generation**: Requires `reportlab`

If these dependencies are missing, the app will gracefully fall back to basic functionality.

### 5. Troubleshooting

#### Mock Client Error
If you see "Using mock client" messages, it means:
- Missing `API_KEY` environment variable
- Missing `OPENAI_BASE_URL` environment variable
- AutoGen packages not properly installed

#### Import Errors
The app has fallback mechanisms for missing dependencies. Check the logs for specific missing packages.

## Local Development

For local development, copy `.env.example` to `.env` and set your API credentials:

```bash
cp .env.example .env
# Edit .env with your credentials
```

Run locally:
```bash
streamlit run sop_generator/app.py
```
