# 🌍 Queska Backend API

**AI-Powered All-in-One Travel Experience Platform**

Queska is a revolutionary travel platform that transforms how people explore the world by providing intelligent, accessible, and culturally immersive travel experiences through AI agents.

---

## 🚀 Features

### Core Features
- 🎯 **Smart Destination Discovery** - AI-powered recommendations based on interests
- 📅 **Experience Creation** - Build complete travel experiences in minutes
- 💳 **Single Checkout** - One payment for flights, hotels, events, dining, and more
- 💬 **24/7 AI Concierge** - Real-time travel assistance
- 📍 **Geolocation Intelligence** - Location-aware recommendations
- 🔔 **Real-time Notifications** - Stay updated on your journey

### User Types
| User Type | Description |
|-----------|-------------|
| **Travelers** | Create and book travel experiences |
| **Vendors** | Hotels, restaurants, tour operators, activity providers |
| **Agents** | Travel agents helping clients plan journeys |
| **Consultants** | Travel consultation and advisory services |
| **Admins** | Platform management and administration |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI (Python 3.11+) |
| **Database** | MongoDB (Motor + Beanie ODM) |
| **Cache** | Redis |
| **Task Queue** | Celery |
| **Search** | Meilisearch / Elasticsearch |
| **Vector DB** | Qdrant / ChromaDB |
| **AI** | Google Gemini / Perplexity AI |
| **Payments** | Stripe |
| **Maps** | Mapbox |
| **Media Storage** | Cloudinary / MinIO |
| **Email** | SendGrid |
| **Push Notifications** | Firebase FCM |

---

## 📁 Project Structure

```
queskabackend/
├── app/                        # Main API application
│   ├── api/                    # API routes
│   │   └── v1/                 # API version 1
│   │       └── endpoints/      # Route handlers
│   ├── core/                   # Core configurations
│   ├── models/                 # MongoDB document models
│   ├── schemas/                # Pydantic schemas
│   ├── repositories/           # Data access layer
│   ├── services/               # Business logic layer
│   └── utils/                  # Utilities
├── ai_service/                 # AI Agent service
│   ├── agents/                 # AI agents (support, discovery, etc.)
│   ├── prompts/                # Agent prompts
│   └── tools/                  # Agent tools
├── crawler_service/            # Web crawler module
├── integrations/               # External API integrations
│   ├── payments/               # Stripe
│   ├── maps/                   # Mapbox, Google Maps
│   ├── travel_apis/            # Booking.com, Expedia
│   ├── ai/                     # Gemini, Perplexity, OpenAI
│   └── media/                  # Cloudinary, MinIO
├── workers/                    # Background task workers
└── tests/                      # Test suite
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MongoDB 7.0+
- Redis 7.0+
- Docker & Docker Compose (optional)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/lumicoria/queska-backend.git
cd queska-backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run the application**
```bash
# Development mode with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python
python -m app.main
```

### Using Docker

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

---

## 📚 API Documentation

Once the server is running, access the API documentation:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

---

## 🔑 API Endpoints

### Vendors API (`/api/v1/vendors`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new vendor |
| POST | `/login` | Vendor login |
| GET | `/` | List vendors |
| GET | `/featured` | Get featured vendors |
| GET | `/category/{category}` | Get vendors by category |
| GET | `/nearby` | Get nearby vendors |
| GET | `/me` | Get current vendor profile |
| PUT | `/me` | Update vendor profile |
| POST | `/me/verification` | Submit verification documents |

### Agents API (`/api/v1/agents`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new agent |
| POST | `/login` | Agent login |
| GET | `/` | List agents |
| GET | `/featured` | Get featured agents |
| GET | `/available` | Get available agents |
| GET | `/me` | Get current agent profile |
| PUT | `/me` | Update agent profile |
| POST | `/me/clients` | Add client |
| GET | `/me/referrals` | Get referral stats |

---

## 🔐 Authentication

The API uses JWT (JSON Web Tokens) for authentication.

### Getting a Token

```bash
# Vendor Login
curl -X POST "http://localhost:8000/api/v1/vendors/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "vendor@example.com", "password": "password123"}'
```

### Using the Token

```bash
# Include token in Authorization header
curl -X GET "http://localhost:8000/api/v1/vendors/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## ⚙️ Configuration

Key environment variables:

```env
# Application
DEBUG=false
ENVIRONMENT=production

# Database
MONGODB_URI=mongodb://localhost:27017/queska
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Payments
STRIPE_SECRET_KEY=sk_test_xxx

# Maps
MAPBOX_ACCESS_TOKEN=pk.xxx

# AI
GEMINI_API_KEY=xxx
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific tests
pytest tests/unit/
pytest tests/integration/
```

---

## 📦 Deployment

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure strong `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Set up MongoDB Atlas or production MongoDB
- [ ] Configure Redis for caching
- [ ] Set up Sentry for error tracking
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS
- [ ] Set up monitoring (Prometheus, Grafana)

### Docker Deployment

```bash
# Build production image
docker build --target production -t queska-api:latest .

# Run container
docker run -d -p 8000:8000 --env-file .env queska-api:latest
```

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

Proprietary - Lumicoria Ltd. All rights reserved.

---

## 👥 Team

**Queska by Lumicoria**

- 📧 Email: dev@queska.com
- 🌐 Website: https://queska.com
- 📍 Uyo, Akwa Ibom State, Nigeria

---

## 🗺️ Roadmap

### Phase 1 (Current)
- [x] Core API structure
- [x] Vendor management
- [x] Agent management
- [x] Authentication system
- [ ] User management
- [ ] Experience creation flow

### Phase 2
- [ ] Booking system
- [ ] Payment integration
- [ ] AI agents implementation
- [ ] Real-time notifications

### Phase 3
- [ ] Web crawler integration
- [ ] Advanced search
- [ ] Analytics dashboard
- [ ] Mobile API optimization

---

*Built with ❤️ by Lumicoria*
