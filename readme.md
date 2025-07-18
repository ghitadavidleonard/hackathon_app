# 🚗 OBD Diagnostic AI Agent

An AI-powered automotive diagnostic agent that can analyze OBD (On-Board Diagnostics) trouble codes and provide expert automotive assistance. Built for the **IT Perspectives Hackathon 2025** (July 17-18, 2025).

## 🔧 Features

### 🎤 **Voice & Text Interaction**

- **OpenAI Realtime API**: Voice-enabled diagnostic conversations
- **Text Chat Interface**: Traditional text-based interaction via Chainlit
- **Seamless Mode Switching**: Use voice or text as preferred

### 🔍 **DTC Code Analysis**

- **Automatic Code Detection**: Finds OBD codes in messages and files
- **Comprehensive Database**: Over 100+ DTC codes with descriptions and causes
- **Smart Code Lookup**: Detailed information about specific diagnostic trouble codes
- **Batch Analysis**: Process multiple codes simultaneously

### 📂 **File Upload Support**

- **Diagnostic Reports**: Upload scanner outputs, OBD reports, text files
- **Multiple Formats**: .txt, .log, .csv, .json, and other text-based files
- **Automatic Extraction**: Finds and analyzes OBD codes from uploaded content
- **Real-time Processing**: Instant analysis and feedback

### 🛠️ **Diagnostic Tools**

- **Code Lookup**: Get detailed information about specific codes
- **Symptom Search**: Find relevant codes by searching symptoms or keywords
- **Cause Analysis**: Understand what might be causing the problem
- **Expert Guidance**: Professional automotive diagnostic assistance

### 🌐 **API Integration**

- **FastAPI Backend**: RESTful API for programmatic access
- **Real-time Streaming**: Get responses as they are generated
- **Azure OpenAI**: Powered by GPT-4 for intelligent responses
- **LangChain Integration**: Advanced agent capabilities with tool usage

## 🏗️ Architecture

The application consists of several key components:

### 🤖 **AI Agent Architecture**

- **LangGraph Agent**: React-style agent with tool calling capabilities
- **Azure OpenAI GPT-4**: Advanced language model for intelligent responses
- **Tool Integration**: Seamlessly integrates OBD diagnostic tools
- **Supervisor Pattern**: Manages complex multi-step diagnostic workflows

### 🔧 **Core Components**

- **FastAPI Backend** (`agent.py`): RESTful API server
- **Chainlit Interface** (`chat.py`): Interactive web UI with file upload
- **OBD Tools** (`obd_tools.py`): Core diagnostic functionality
- **Agent Tools** (`agent_tools.py`): LangChain tool wrappers
- **Realtime Module** (`realtime/`): OpenAI Realtime API integration

### 📊 **Data Layer**

- **JSON Database** (`database/obd-codes.json`): OBD trouble codes with descriptions
- **Code Patterns**: Regex-based code extraction from text
- **Structured Analysis**: Organized diagnostic information

## 📁 Project Structure

```
hackathon_app/
├── agent.py                    # FastAPI backend server
├── chat.py                     # Chainlit chat interface
├── agent_tools.py              # LangChain tool wrappers
├── obd_tools.py                # Core OBD diagnostic functionality
├── chainlit.md                 # Chainlit app description
├── requirements.txt            # Python dependencies
├── .env.example               # Environment configuration template
├── .chainlit/
│   ├── config.toml            # Chainlit configuration
│   └── translations/          # Multi-language support
├── database/
│   └── obd-codes.json         # OBD trouble codes database
├── realtime/
│   ├── __init__.py           # Realtime client implementation
│   └── tools.py              # Realtime-specific tools
├── agent/                     # Python virtual environment
└── test-codes.json           # Test data for development
```

## Quick Start

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
# - YOUTUBE_API_KEY (optional)
# - GOOGLE_MAPS_API_KEY (optional)
```

### 2. Create and Activate Virtual Environment

```bash
python -m venv agent
agent\Scripts\activate  # Windows
# or
source agent/bin/activate  # macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

#### Option A: Interactive Chat Interface (Recommended)

```bash
chainlit run chat.py
```

- **Voice Mode**: Click the microphone button for voice conversations
- **Text Mode**: Type messages normally
- **File Upload**: Drag and drop diagnostic files
- **Real-time Responses**: See analysis as it's generated

#### Option B: API Server

```bash
python agent.py
```

The API will be available at: `http://localhost:8005`

## 💡 Usage Examples

### 🎙️ Voice Interaction

1. **Start the chat interface**: `chainlit run chat.py`
2. **Click the microphone button** to start voice mode
3. **Say something like**: "I have a P0301 code on my car"
4. **Get real-time voice response** with detailed analysis

### 💬 Text Chat

1. **Type your question**: "What does code P0420 mean?"
2. **Upload diagnostic files**: Drag and drop scanner outputs
3. **Get comprehensive analysis**: Causes, solutions, and guidance

### 📂 File Upload

1. **Prepare diagnostic files**: Scanner outputs, OBD reports, or text files
2. **Upload via web interface**: Drag and drop or click upload
3. **Automatic analysis**: System extracts and analyzes all found codes

### 🔌 API Usage

Send POST requests to `/ask` endpoint:

```bash
curl -X POST "http://localhost:8005/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What does P0301 mean?",
    "history": []
  }'
```

## 🛠️ Technical Implementation

### 🔧 Core Technologies

- **Python 3.8+**: Main programming language
- **FastAPI**: High-performance web framework
- **Chainlit**: Interactive chat interface
- **LangChain**: AI agent framework
- **LangGraph**: Agent workflow management
- **Azure OpenAI**: GPT-4 language model
- **OpenAI Realtime API**: Voice interaction capabilities

### 📊 OBD Code Database

The system includes a comprehensive database of OBD trouble codes:

- **100+ Codes**: P, B, C, and U-series codes
- **Detailed Descriptions**: What each code means
- **Common Causes**: Typical reasons for each code
- **Code Categories**: Powertrain, Body, Chassis, Network codes

### 🎯 Agent Capabilities

- **Code Recognition**: Detects OBD codes in text using regex patterns
- **Smart Lookup**: Retrieves detailed information from the database
- **Contextual Analysis**: Provides relevant diagnostic guidance
- **Multi-modal Input**: Handles both voice and text interactions
- **File Processing**: Extracts codes from uploaded diagnostic files

## 🔍 Supported OBD Codes

The system recognizes and analyzes various types of diagnostic trouble codes:

- **P-Codes**: Powertrain (engine, transmission)
- **B-Codes**: Body (lighting, airbags, etc.)
- **C-Codes**: Chassis (brakes, suspension, etc.)
- **U-Codes**: Network communication codes

Example codes in the database:

- `P0301`: Cylinder 1 Misfire Detected
- `P0420`: Catalyst System Efficiency Below Threshold
- `P0171`: System Too Lean (Bank 1)
- `B0001`: Various body control module codes
- And many more...

## 🌟 Key Features in Detail

### 🤖 AI Agent Features

- **Context Awareness**: Remembers conversation history
- **Tool Integration**: Seamlessly uses diagnostic tools
- **Streaming Responses**: Real-time response generation
- **Error Handling**: Graceful handling of unknown codes
- **Multi-step Analysis**: Complex diagnostic workflows

### 🎤 Voice Features

- **Real-time Processing**: Instant voice-to-text conversion
- **Natural Conversations**: Speak naturally about car problems
- **Voice Responses**: Text-to-speech for accessibility
- **Interrupt Handling**: Can stop and restart conversations

### � Web Interface Features

- **Modern UI**: Clean, responsive design
- **File Upload**: Drag-and-drop file handling
- **Progress Indicators**: Visual feedback during processing
- **Chat History**: Persistent conversation history
- **Multi-language Support**: Interface translations available

## 🚀 Development

### 🔧 Development Setup

1. **Fork the repository**
2. **Clone your fork**: `git clone https://github.com/yourusername/hackathon_app.git`
3. **Create a branch**: `git checkout -b feature/your-feature`
4. **Set up environment**: Follow the Quick Start guide
5. **Make changes and test**
6. **Submit a pull request**

### 🧪 Testing

The project includes test data for development:

- **test-codes.json**: Sample OBD codes for testing
- **Database validation**: Verify OBD code database integrity
- **API testing**: Test endpoints with various inputs

### 📝 Contributing

1. **Follow Python PEP 8** style guidelines
2. **Add docstrings** to new functions
3. **Update README** for new features
4. **Test your changes** before submitting

## 🎯 Hackathon Project

This project was created for the **IT Perspectives Hackathon 2025** (July 17-18, 2025) with the theme "Let the Code Explode!"

### 🏆 Project Goals

- **Demonstrate AI Integration**: Show practical AI applications in automotive diagnostics
- **Voice Interface Innovation**: Implement cutting-edge voice interaction capabilities
- **Real-world Problem Solving**: Address actual automotive diagnostic challenges
- **Technical Excellence**: Showcase advanced software architecture and best practices

### 💡 Innovation Highlights

- **Multi-modal AI**: Combines voice, text, and file processing
- **Real-time Processing**: Instant response generation and streaming
- **Comprehensive Database**: Extensive OBD code coverage
- **User-friendly Interface**: Intuitive design for technical and non-technical users

## 📞 Support & Contact

For questions, issues, or contributions:

- **GitHub Issues**: Report bugs and request features
- **Pull Requests**: Contribute code improvements
- **Documentation**: Help improve the README and docs

## 🔧 Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all required API keys are set in `.env`
2. **Import Errors**: Verify virtual environment is activated
3. **Port Conflicts**: Check that ports 8005 and 8000 are available
4. **File Upload Issues**: Ensure file permissions are correct

### Debug Mode

Enable debug logging by setting environment variable:

```bash
export CHAINLIT_DEBUG=true
```

## 🌟 Future Enhancements

### Planned Features

- **Real-time Vehicle Data**: Integration with live OBD-II scanners
- **Advanced Diagnostics**: ML-based fault prediction
- **Mobile App**: Native mobile application
- **Extended Database**: More comprehensive code coverage
- **Multi-language Support**: Additional language translations

### Technical Improvements

- **Performance Optimization**: Faster response times
- **Caching Layer**: Improved data retrieval
- **Database Migration**: Move to production database
- **API Versioning**: Backwards compatibility support

---

## 🎉 Acknowledgments

**IT Perspectives Hackathon 2025** - "Let the Code Explode!" 🚀

Built with ❤️ for the automotive diagnostic community.

---

_This project demonstrates the power of AI in solving real-world automotive problems through innovative voice and text interfaces._
