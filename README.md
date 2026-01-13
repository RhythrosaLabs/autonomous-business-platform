# 🚀 Autonomous Business Platform

> AI-powered business automation platform with Ray-backed parallel processing, FastAPI backend, and Streamlit frontend

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io/)
[![Ray](https://img.shields.io/badge/Ray-2.8+-orange.svg)](https://ray.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Features

- 🎯 **Campaign Generator**: AI-powered marketing campaigns with 7x faster parallel generation
- 🛍️ **Product Management**: Full Printify/Shopify integration with automated mockup generation
- 📊 **Analytics Dashboard**: Real-time metrics and insights with parallel data fetching
- 📧 **Email Marketing**: Automated campaigns and sequences
- 📱 **Social Media**: Multi-platform posting (YouTube, Twitter/X) and scheduling
- 🎨 **Content Creation**: AI-powered images, videos, and copy generation
- 📅 **Calendar & Tasks**: AI-powered planning and scheduling
- 🔧 **Custom Workflows**: Build automation workflows with visual editor
- 📈 **Job Monitoring**: Advanced Ray-backed job queue with real-time monitoring
- 🎮 **Playground**: Interactive AI model testing with code and HTML/CSS editors

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Streamlit Frontend                   │
│                   (Port 8501)                        │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              FastAPI Backend                         │
│                (Port 8000)                          │
│  • REST API endpoints                               │
│  • WebSocket support                                │
│  • Job management                                   │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│           Ray Distributed Cluster                    │
│              (Port 8265 - Dashboard)                │
│  • Parallel job execution                           │
│  • Resource profiling                               │
│  • Automatic retry logic                            │
└─────────────────────────────────────────────────────┘
```

## 📦 Quick Start

### Prerequisites

- Python 3.11+
- 8GB RAM minimum
- macOS, Linux, or Windows (WSL2)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/RhythrosaLabs/autonomous-business-platform.git
cd autonomous-business-platform
```

2. **Create virtual environment**
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys
nano .env
```

5. **Start the platform**
```bash
cd scripts
./start_platform.sh
```

The platform will start:
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Ray Dashboard**: http://localhost:8265

## 🔑 Required API Keys

### AI Services
- **Replicate API**: Get from [replicate.com](https://replicate.com)
- **OpenAI API** (optional): Get from [platform.openai.com](https://platform.openai.com)

### E-commerce
- **Printify API**: Get from [printify.com/app/account/api](https://printify.com/app/account/api)
- **Shopify**: Get from your Shopify admin panel

### Social Media
- **YouTube API**: Set up via [Google Cloud Console](https://console.cloud.google.com)
- **Twitter/X API** (optional): Get from [developer.twitter.com](https://developer.twitter.com)

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

1. **Build and start services**
```bash
docker compose up -d
```

2. **View logs**
```bash
docker compose logs -f
```

3. **Stop services**
```bash
docker compose down
```

### Manual Docker Build

```bash
# Build image
docker build -t autonomous-business-platform .

# Run backend
docker run -d \
  -p 8000:8000 \
  -p 8265:8265 \
  --env-file .env \
  --name abp-backend \
  autonomous-business-platform \
  python -m uvicorn fastapi_backend:app --host 0.0.0.0 --port 8000

# Run frontend
docker run -d \
  -p 8501:8501 \
  --env-file .env \
  --name abp-frontend \
  autonomous-business-platform
```

## 🌐 Cloud Deployment

### Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/RhythrosaLabs/autonomous-business-platform)

### Deploy to Render

1. Fork this repository
2. Create new Web Service on [Render](https://render.com)
3. Connect your forked repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `streamlit run autonomous_business_platform.py --server.port $PORT`
6. Add environment variables from `.env.example`

### Deploy to Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Launch app
fly launch

# Deploy
fly deploy
```

## 📊 Performance

- **Campaign Generation**: ~7x faster with parallel execution (70s → 10s)
- **Analytics Fetching**: ~2-5x faster with concurrent API calls
- **Resource Profiling**: Automatic CPU/RAM allocation per job type
- **Retry Logic**: Exponential backoff for network failures (3 attempts)

## 🛠️ Development

### Project Structure

```
autonomous-business-platform/
├── app/
│   ├── tabs/              # 34 Streamlit tab modules
│   ├── services/          # Core business logic
│   └── utils/             # Helper utilities
├── backend/
│   └── fastapi_backend.py # FastAPI server
├── scripts/
│   └── start_platform.sh  # Startup script
├── modules/               # Shared modules
├── brand/                 # Brand templates
├── autonomous_business_platform.py  # Main Streamlit app
├── requirements.txt       # Python dependencies
└── docker-compose.yml     # Docker configuration
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
```

### Type Checking

```bash
mypy .
```

## 📚 Documentation

- **API Documentation**: http://localhost:8000/docs (when running)
- **Ray Dashboard**: http://localhost:8265 (when running)
- **Cleanup Guide**: [docs/CLEANUP_PLAN.md](docs/CLEANUP_PLAN.md)
- **Docker Guide**: [docs/DOCKER.md](docs/DOCKER.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [Ray](https://ray.io/) for distributed computing
- Backend by [FastAPI](https://fastapi.tiangolo.com/)
- AI models via [Replicate](https://replicate.com/)

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/RhythrosaLabs/autonomous-business-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/RhythrosaLabs/autonomous-business-platform/discussions)

## 🚀 Roadmap

- [ ] Add Kubernetes deployment configs
- [ ] Implement user authentication
- [ ] Add PostgreSQL support
- [ ] Create mobile app
- [ ] Add more AI model integrations
- [ ] Implement A/B testing framework

---

**Made with ❤️ by RhythrosaLabs**
