# 🚀 Autonomous Business Platform

A production-ready AI-powered business automation platform with Ray-backed job queuing and FastAPI backend.

## Features

- 🎯 **Campaign Generator**: AI-powered marketing campaigns with parallel generation
- 🛍️ **Product Management**: Printify/Shopify integration
- 📊 **Analytics Dashboard**: Real-time metrics and insights
- 📧 **Email Marketing**: Automated campaigns and sequences
- 📱 **Social Media**: Multi-platform posting and scheduling
- 🎨 **Content Creation**: Images, videos, and copy generation
- 📅 **Calendar & Tasks**: AI-powered planning
- 🔧 **Custom Workflows**: Build automation workflows
- 📈 **Job Monitoring**: Advanced Ray-backed job queue with monitoring

## Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Start Platform

```bash
cd scripts
./start_platform.sh
```

This starts:
- FastAPI backend (port 8000)
- Streamlit frontend (port 8501)
- Ray cluster (port 8265)

### 3. Access Application

- **Web App**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs
- **Ray Dashboard**: http://localhost:8265

## Configuration

### Required API Keys

1. **AI Services**:
   - Replicate API (for AI models)
   - OpenAI API (optional)

2. **E-commerce**:
   - Printify API token
   - Shopify credentials

3. **Social Media**:
   - YouTube API credentials
   - Twitter/X API (optional)

### Environment Variables

See `.env.example` for all available configuration options.

## Architecture

- **Frontend**: Streamlit with 20+ specialized tabs
- **Backend**: FastAPI with async job processing
- **Job Queue**: Ray-backed distributed task queue
- **Storage**: SQLite (default) or PostgreSQL
- **AI Models**: Replicate, OpenAI, local models

## Performance

- ⚡ Parallel job execution (7x faster campaigns)
- 📊 Resource profiling (CPU/RAM allocation)
- 🔄 Automatic retry logic (exponential backoff)
- 📈 Real-time job monitoring

## Development

```bash
# Run tests
pytest

# Format code
black .

# Type checking
mypy .
```

## Deployment

### Docker

```bash
docker-compose up -d
```

### Manual

```bash
# Production mode
streamlit run autonomous_business_platform.py --server.port 8501
uvicorn backend.fastapi_backend:app --host 0.0.0.0 --port 8000
```

## Documentation

- [Docker Setup](docs/DOCKER.md)
- [API Reference](http://localhost:8000/docs)
- [Cleanup Guide](docs/CLEANUP_PLAN.md)

## License

MIT License - See LICENSE file for details
