# 🚗 OBD Diagnostic AI Agent

An AI-powered automotive diagnostic agent that can analyze OBD (On-Board Diagnostics) trouble codes and provide expert automotive assistance.

## 📁 Project Structure

```
├── agent.py                 # Main AI agent with OBD capabilities
├── chat.py                 # Chainlit chat interface
├── obd_tools.py            # OBD diagnostic tools and handlers
├── obd_fastmcp_server.py   # FastMCP server for OBD tools
├── chainlit.md             # Chainlit configuration
├── database/
│   └── obd-codes.json     # OBD trouble codes database
└── requirements.txt       # Python dependencies
```

## 🚀 Quick Start

### 1. Environment Setup

First, copy the example environment file and configure your API keys:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your actual API keys
# Required keys:
# - AZURE_OPENAI_ENDPOINT
# - AZURE_OPENAI_API_KEY
# - OPENAI_API_VERSION
# - YOUTUBE_API_KEY
# - GOOGLE_MAPS_API_KEY
```

### 2. Create and activate the Virtual Environment

```bash
python -m venv agent
agent\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

#### Option A: Web API (Recommended)

```bash
python agent.py
```

The agent API will be available at: http://localhost:8005

#### Option B: Chat Interface

```bash
chainlit run chat.py
```

Interactive chat interface will open in your browser.

## 🔧 Features

- **OBD Code Lookup**: Get detailed information about specific diagnostic trouble codes
- **Code Extraction**: Automatically extract and analyze OBD codes from text
- **Keyword Search**: Find relevant codes by searching symptoms or keywords
- **General AI Assistant**: Handle both automotive and general questions
- **Real-time Streaming**: Get responses as they are generated

## 📚 API Usage

Send POST requests to `/ask` endpoint:

```json
{
  "history": [{ "role": "user", "content": "What does P0301 mean?" }]
}
```

## 🛠️ Components

- **AI Agent**: Azure OpenAI-powered agent with automotive expertise
- **OBD Tools**: Comprehensive diagnostic trouble code analysis
- **FastMCP Server**: MCP-compatible server for tool integration
- **Database**: JSON database with OBD trouble codes and descriptions

---

## Quick Start Commands

```bash
# To activate environment
agent\Scripts\activate
# To install dependencies
pip install -r .\requirements.txt
# Run the API
python .\agent.py
# Run the UI
chainlit run .\chat.py
```
