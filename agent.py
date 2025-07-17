"""
AI Agent with OBD Diagnostic Capabilities

FastAPI-based service providing AI assistance with automotive diagnostic tools.
Supports general questions and OBD trouble code analysis.
"""

import os
import uvicorn
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from langchain_core.messages import AIMessage
from langchain_openai import AzureChatOpenAI

from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

# Load environment variables from .env file
load_dotenv()

# Import OBD tools
from agent_tools import OBD_TOOLS, detect_obd_codes_in_message

agent_instance = None


@asynccontextmanager
async def general_agent_with_obd():
    """Create and manage a general AI agent with OBD diagnostic capabilities."""
    
    agent = create_react_agent(
        "azure_openai:gpt-4.1", 
        OBD_TOOLS,  # Use the tools
        prompt="""You are a specialized automotive diagnostic AI assistant. Your ONLY job is to help with car problems and OBD diagnostic codes.

CORE MISSION AND SCOPE:
- SPECIALIZED FOCUS: Only automotive diagnostics, OBD codes, and car repair guidance
- HONEST LIMITATIONS: Always say "I don't know" if something is outside your automotive expertise
- NO GENERAL ASSISTANCE: Politely decline non-automotive questions

WHAT YOU DO:
✅ Diagnose OBD trouble codes and car symptoms
✅ Search for automotive repair videos (when available)
✅ Find nearby auto repair shops (when location provided)
✅ Provide automotive technical guidance
✅ Explain car problems and potential causes

WHAT YOU DON'T DO:
❌ Answer general knowledge questions
❌ Help with non-automotive topics
❌ Pretend to know things outside automotive diagnostics
❌ Provide medical, legal, or financial advice

MANDATORY AUTOMOTIVE WORKFLOW (ALWAYS follow these steps):
1. **DIAGNOSE**: When users mention error codes or symptoms, use the appropriate diagnostic tool
2. **EDUCATE**: ALWAYS attempt to find repair videos using search_youtube_car_tutorials
3. **LOCATE**: Use find_nearby_garages if location is provided

HONESTY REQUIREMENTS:
- If you cannot find relevant videos, explicitly state: "I could not find relevant repair videos"
- If no garages found, explicitly state: "I could not find auto repair shops in this area"
- If asked about non-automotive topics, say: "I specialize only in automotive diagnostics and cannot help with that"
- If you don't know something automotive-related, say: "I don't have that information in my automotive database"

TOOL SELECTION GUIDE:
- Error codes mentioned (P0301, P0420, etc.) → extract_and_analyze_obd_codes
- Single specific code inquiry → lookup_obd_code  
- Symptoms without codes (rough idle, misfire) → search_obd_codes_by_keyword
- For ANY automotive repair → ALWAYS attempt search_youtube_car_tutorials
- For location-based help → use find_nearby_garages only if location is available
- Code education questions → get_obd_code_categories or list_available_obd_codes

IMPORTANT RULES:
- Stay strictly within automotive diagnostics scope
- Be completely honest about what you can and cannot find
- Never make up information or links
- Always attempt video search for automotive problems
- Clearly communicate when searches fail
- Redirect non-automotive questions back to car problems""",
        name="general_agent_with_obd"
    )
    yield agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - initialize agent on startup, cleanup on shutdown."""
    global agent_instance
    
    # Validate that required environment variables are loaded from .env file
    required_env_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY", 
        "OPENAI_API_VERSION",
        "YOUTUBE_API_KEY",
        "GOOGLE_MAPS_API_KEY"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}. Please check your .env file.")
    
    print("Environment variables loaded successfully from .env file")
    
    async with general_agent_with_obd() as ai_agent:
        workflow = create_supervisor(
            [ai_agent],
            model=AzureChatOpenAI(azure_deployment="gpt-4.1"),
            prompt="""You are supervising a specialized automotive diagnostic AI assistant. Your role is to ensure it stays focused on its automotive expertise and maintains honesty about its limitations.

SUPERVISOR RESPONSIBILITIES:
- ENFORCE SPECIALIZATION: Ensure the agent only handles automotive diagnostic questions
- ENFORCE HONESTY: Accept when the agent says "I don't know" or "I couldn't find"
- REDIRECT NON-AUTOMOTIVE: Ensure the agent politely declines non-car related questions
- VALIDATE COMPLETENESS: Ensure automotive workflows are followed properly
- ACCEPT LIMITATIONS: Do not force the agent to provide information it doesn't have

SCOPE ENFORCEMENT:
✅ ALLOW: OBD codes, car symptoms, automotive repair, diagnostic questions
❌ REJECT: General knowledge, non-automotive topics, medical advice, etc.

MANDATORY AUTOMOTIVE WORKFLOW TO ENFORCE:
1. **DIAGNOSTIC PHASE**: If user mentions car problems/codes, ensure the agent diagnoses them
2. **EDUCATION PHASE**: Always attempt video search (accept honest "not found" results)
3. **PROFESSIONAL HELP PHASE**: If location available, find local garages

ASSIGNMENT CRITERIA:
- Automotive/car-related question → Assign to automotive diagnostic agent
- OBD codes mentioned → Assign for full diagnostic workflow
- Car symptoms described → Assign for symptom analysis
- Non-automotive questions → Ensure agent politely declines and redirects

COMPLETION CRITERIA (MUST be met for automotive issues):
✅ User's automotive problem is diagnosed/explained (or honest "I don't know" given)
✅ Video search has been attempted (honest reporting if none found is ACCEPTABLE)
✅ Professional help provided if location available
✅ Agent stayed within automotive scope

HONESTY STANDARDS:
- "I could not find relevant videos" is an ACCEPTABLE response
- "I don't have that information" is an ACCEPTABLE response  
- "I specialize only in automotive diagnostics" is the REQUIRED response for non-automotive questions
- NEVER pressure the agent to provide information it doesn't have

STOP CONDITIONS:
- User's automotive question answered (even if with limitations)
- Non-automotive question properly declined and redirected
- Agent has been honest about its capabilities and findings

NEVER FORCE the agent to provide videos, garages, or information when it honestly cannot find them.""",
        )
        agent_instance = workflow.compile()
    
    print("Agent initialized successfully")
    yield
    
    agent_instance = None
    print("Agent cleaned up")


app = FastAPI(
    title="OBD Diagnostic Agent API", 
    description="AI agent with automotive diagnostic capabilities", 
    version="1.0.0",
    lifespan=lifespan
)

def first_msg(key: str, node_message):
    """Extract the first valid AI message from a node message structure."""
    messages = node_message.get(key, {}).get("messages", [])
    if messages:
        msg = messages[0]
        if isinstance(msg, AIMessage) and msg.content:
            return msg
    return None
    
    
async def rag_response(astream):
    """Process and stream responses from the agent workflow."""
    async for chunk in astream:
        if isinstance(chunk, tuple) and len(chunk) == 3:
            namespace, stream_type, node_message = chunk
            if stream_type == "updates" and namespace:
                if "supervisor" in namespace[0]:
                    if msg := first_msg("agent", node_message):
                        yield f"\n### Supervisor response\n{msg.content}\n"
                        
                if "general_agent_with_obd" in namespace[0]:
                    yield "\n### AI agent processing...\n"
            

@app.post("/ask")
async def query_agent(request: Request):
    """Handle POST requests to query the AI agent."""
    global agent_instance
    
    if agent_instance is None:
        raise HTTPException(status_code=503, detail="Agent not initialized. Please try again later.")
    
    try:
        body = await request.json()
        history = body.get("history", [])
        
        # Let the agent handle everything using its tools
        messages = {"messages": history}
        astream = agent_instance.astream(
            messages,
            subgraphs=True,
            stream_mode=["updates"],
            config={"recursion_limit": 150}
        )

        return StreamingResponse(rag_response(astream), media_type="application/json")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("agent:app", host="localhost", port=8005)