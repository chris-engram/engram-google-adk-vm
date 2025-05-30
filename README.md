# Google ADK Agent Configuration

This repository contains the configuration and setup for Google Agent Development Kit (ADK) agents with Scalar API documentation.

## 🚀 Features

- **Google ADK Agent**: AI assistant for qualifying revenue support candidates
- **RESTful API**: Full API access via ADK's built-in server
- **Scalar Documentation**: Beautiful, interactive API documentation
- **CORS Support**: Browser-friendly API access through proxy endpoints

## 📋 Prerequisites

- Python 3.8+
- Google API Key (set in `.env` file)
- Ubuntu/Linux environment (tested on Ubuntu)

## 🛠️ Installation

1. Clone this repository:
```bash
git clone https://github.com/YOUR_USERNAME/google-adk-agents.git
cd google-adk-agents
```

2. Create a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory:
```bash
echo "GOOGLE_API_KEY=your_api_key_here" > .env
```

## 🏗️ Project Structure

```
google-adk-agents/
├── revsup-candidate-qualify/     # Agent configuration
│   ├── __init__.py
│   └── agent.py                  # Agent definition
├── scalar_docs.py                # Scalar documentation server
├── api_server_with_scalar.py     # Combined server (alternative)
├── requirements.txt              # Python dependencies
├── .env                         # Environment variables (not committed)
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

## 🤖 Agent Configuration

The main agent is defined in `revsup-candidate-qualify/agent.py`:

```python
from google.adk.agents import LlmAgent

root_agent = LlmAgent(
    name="revsup_candidate_qualify",
    model="gemini-1.5-flash",
    description="AI assistant for qualifying revenue support candidates",
    instruction="""You are a helpful AI assistant for qualifying revenue support candidates..."""
)
```

## 🚦 Running the Services

### Start ADK API Server
```bash
adk api_server --host 0.0.0.0 --port 8000
```

### Start Scalar Documentation Server
```bash
python3 scalar_docs.py
```

## 📡 API Endpoints

### Core Endpoints

- **GET `/list-agents`** - List all agents with detailed information
- **POST `/apps/{app_name}/users/{user_id}/sessions`** - Create a new chat session
- **POST `/run`** - Send a message to an agent

### Example: List Agents
```bash
curl http://localhost:8080/api/list-agents
```

Response:
```json
{
    "agents": [
        {
            "name": "revsup-candidate-qualify",
            "display_name": "Revsup Candidate Qualify",
            "status": "active",
            "model": "gemini-1.5-flash",
            "instruction": "You are a helpful AI assistant...",
            "description": "AI assistant for qualifying revenue support candidates",
            "internal_name": "revsup_candidate_qualify"
        }
    ],
    "total": 1
}
```

### Example: Chat with Agent

1. Create a session:
```bash
curl -X POST http://localhost:8000/apps/revsup-candidate-qualify/users/test-user/sessions \
  -H "Content-Type: application/json" \
  -d '{}'
```

2. Send a message:
```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{
    "appName": "revsup-candidate-qualify",
    "userId": "test-user",
    "sessionId": "YOUR_SESSION_ID",
    "newMessage": {
      "role": "user",
      "parts": [{"text": "Hello!"}]
    }
  }'
```

## 🌐 Remote Access

If deployed on a server with public IP:

- **Scalar Documentation**: http://YOUR_IP:8080/scalar
- **API Server**: http://YOUR_IP:8000
- **Proxy API (with CORS)**: http://YOUR_IP:8080/api/*

## 🔧 Configuration

### Environment Variables
- `GOOGLE_API_KEY`: Your Google API key for Gemini access

### Ports
- `8000`: ADK API Server
- `8080`: Scalar Documentation Server

## 🚀 Deployment

For production deployment:

1. Use systemd services (see `systemd/` directory)
2. Set up reverse proxy with nginx
3. Enable HTTPS with SSL certificates
4. Configure firewall rules

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google ADK team for the excellent agent framework
- Scalar for the beautiful API documentation UI