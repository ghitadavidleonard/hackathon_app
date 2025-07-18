# 🚗 OBD Diagnostic AI Agent

An AI-powered automotive diagnostic agent that can analyze OBD (On-Board Diagnostics)## 🔧 Features

- **📂 File Upload Support**: Upload diagnostic reports, scanner outputs, text files
- **🔍 Automatic Code Detection**: Finds OBD codes in uploaded files
- **📋 Structured Analysis**: Complete 5-step diagnostic process
- **OBD Code Lookup**: Get detailed information about specific diagnostic trouble codes
- **Code Extraction**: Automatically extract and analyze OBD codes from text
- **Keyword Search**: Find relevant codes by searching symptoms or keywords
- **🎥 Video Tutorials**: Find YouTube repair videos for each problem
- **🗺️ Smart Garage Search**:
  - Single code: Integrated garage search in analysis
  - Multiple codes: One consolidated garage search at the end
- **🛒 Parts Search**: Find replacement parts on Amazon
- **Real-time Streaming**: Get responses as they are generated

### 🏪 Intelligent Garage Search Behavior

When you provide multiple OBD codes and a location, the system optimizes garage searching:

- **Multiple codes**: Complete analysis for all codes first, then show nearby garages once at the end
- **Single code**: Include garage information directly in the diagnostic analysis
- **No location**: Skip garage search entirelyes and provide expert automotive assistance.

## 📁 Project Structure

```
├── agent.py                 # Main AI agent with OBD capabilities
├── chat.py                 # Chainlit chat interface with file upload support
├── agent_tools.py          # OBD diagnostic tools and handlers
├── obd_tools.py            # Core OBD functionality
├── chainlit.md             # Chainlit configuration
├── config.toml            # Chainlit settings
├── sample_diagnostic_report.txt  # Example file for testing uploads
├── database/
│   └── obd-codes.json     # OBD trouble codes database
└── requirements.txt       # Python dependencies
```

## ✨ New Features

### 📂 File Upload Support

- **Upload diagnostic reports** - Scanner outputs, OBD reports, text files
- **Automatic OBD code extraction** - Finds codes like P0301, P0420, B0001, etc.
- **Intelligent file analysis** - Provides context and suggestions
- **Supported formats** - .txt, .log, .csv, .json files

### 🔧 Enhanced Diagnostic Process

The agent follows a structured 5-step diagnostic process:

1. **What it means** - Simple explanation of codes/problems
2. **What might cause it** - List of potential causes
3. **How to fix it at home** - DIY instructions with video tutorials
4. **Difficulty level** - BEGINNER/INTERMEDIATE/PROFESSIONAL rating
5. **Cost & time estimate** - Parts cost, labor cost, repair time

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
# - GOOGLE_SEARCH_API_KEY
# - GOOGLE_CSE_ID
```

### 2. Create and activate the Virtual Environment

```bash
python -m venv agent
agent\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

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

## � Using File Upload Feature

### Supported File Types

- **Text files** (.txt, .log) - Scanner outputs, diagnostic reports
- **CSV files** (.csv) - Data exports from diagnostic tools
- **JSON files** (.json) - Structured diagnostic data
- **Any text-based file** - The system will attempt to read as text

### How to Upload Files

1. **Open the Chainlit interface** by running `chainlit run chat.py`
2. **Click the attachment/file upload button** in the chat interface
3. **Select your diagnostic file** (use `sample_diagnostic_report.txt` for testing)
4. **Send the file** - The agent will automatically:
   - Extract any OBD codes found (P0301, P0420, B0001, etc.)
   - Provide file analysis and code summary
   - Follow the complete 5-step diagnostic process for each code

### Example Usage

Try uploading the included `sample_diagnostic_report.txt` file to see the system in action:

- Contains codes: P0301, P0420, P0171, B0001
- Shows typical diagnostic report format
- Demonstrates automatic code extraction and analysis

## �🔧 Features

- **📂 File Upload Support**: Upload diagnostic reports, scanner outputs, text files
- **🔍 Automatic Code Detection**: Finds OBD codes in uploaded files
- **📋 Structured Analysis**: Complete 5-step diagnostic process
- **OBD Code Lookup**: Get detailed information about specific diagnostic trouble codes
- **Code Extraction**: Automatically extract and analyze OBD codes from text
- **Keyword Search**: Find relevant codes by searching symptoms or keywords
- **🎥 Video Tutorials**: Find YouTube repair videos for each problem
- **🗺️ Local Garages**: Find nearby auto repair shops
- **🛒 Parts Search**: Find replacement parts on Amazon
- **Real-time Streaming**: Get responses as they are generated

## 📚 API Usage

Send POST requests to `/ask` endpoint:

```json
{
  "query": "What does P0301 mean?",
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
