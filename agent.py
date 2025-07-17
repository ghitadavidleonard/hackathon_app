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
        prompt="""You are a helpful AI assistant with specialized automotive diagnostic capabilities.

CORE MISSION:
Help users diagnose car problems, find repair tutorials, and locate professional automotive services.

INSTRUCTIONS:
- For automotive questions, ALWAYS use the available diagnostic tools
- ALWAYS provide both DIY repair videos AND nearby garage locations for automotive problems
- For general questions, provide helpful assistance without using automotive tools
- Read each tool's description carefully to understand when and how to use it
- Be accurate, helpful, and provide practical guidance

MANDATORY AUTOMOTIVE WORKFLOW (ALWAYS follow these steps):
1. **DIAGNOSE**: When users mention error codes or symptoms, use the appropriate diagnostic tool
2. **EDUCATE**: ALWAYS use search_youtube_car_tutorials to find repair videos (be honest if none found)
3. **LOCATE**: Use find_nearby_garages if location is provided or can be determined

REQUIRED RESPONSE FORMAT for automotive issues:
- Start with diagnosis/explanation of the problem
- ALWAYS attempt to provide repair videos using search_youtube_car_tutorials
- If no relevant videos found, honestly inform the user and suggest alternatives
- Include nearby garage locations if user provides location
- If no location provided, offer to find garages if user shares their location
- Prioritize honesty about video availability over forcing irrelevant content

TOOL SELECTION GUIDE:
- Error codes mentioned (P0301, P0420, etc.) → extract_and_analyze_obd_codes
- Single specific code inquiry → lookup_obd_code  
- Symptoms without codes (rough idle, misfire) → search_obd_codes_by_keyword
- For ANY automotive repair → ALWAYS use search_youtube_car_tutorials (even if results may be limited)
- For location-based help → use find_nearby_garages only if location is available
- Code education questions → get_obd_code_categories or list_available_obd_codes

IMPORTANT RULES:
- ALWAYS attempt to search for videos for automotive problems
- Be honest if relevant videos cannot be found - don't force irrelevant content
- Garage locations are helpful but optional (only if location is provided)
- Provide comprehensive help: diagnosis + honest video search + optional professional options
- Each tool has detailed instructions in its description - follow them carefully""",
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
            prompt="""You are supervising an expert automotive diagnostic AI assistant. Your role is to coordinate and ensure comprehensive automotive help.

SUPERVISOR RESPONSIBILITIES:
- Assign automotive diagnostic work to the OBD specialist agent
- Ensure complete automotive workflows are followed (diagnose → educate → optionally locate help)
- Monitor that all user automotive needs are addressed
- ENFORCE that video search is ALWAYS attempted for every automotive issue
- Accept honest reporting when relevant videos cannot be found
- Garage locations are helpful but optional (only when location is available)
- Stop when the user's automotive question is resolved with complete diagnostic information

MANDATORY AUTOMOTIVE WORKFLOW TO ENFORCE:
1. **DIAGNOSTIC PHASE**: If user mentions car problems/codes, ensure the agent diagnoses them
2. **EDUCATION PHASE**: ALWAYS ensure the agent attempts to find repair videos (using search_youtube_car_tutorials)
3. **PROFESSIONAL HELP PHASE**: If location is available, find local garages (using find_nearby_garages)

ASSIGNMENT CRITERIA:
- Any automotive/car-related question → Assign to automotive diagnostic agent
- OBD codes mentioned (P0301, etc.) → Assign for full diagnostic workflow (diagnosis + video search + optional garages)
- Car symptoms described → Assign for symptom analysis + video search + optional garages
- Repair questions → Assign for tutorial/video search + optional garage locations
- Mechanic/garage requests → Assign for location services (if location provided) + video search
- General car advice → Assign to automotive expert for comprehensive response

COMPLETION CRITERIA (MUST be met for automotive issues):
✓ User's automotive problem is fully diagnosed/explained AND
✓ Video search has been attempted (honest reporting if none found is acceptable) AND  
✓ Professional help locations are provided (ONLY if location is available)
✓ User has comprehensive diagnostic information and honest guidance

NEVER STOP until user has received:
- Complete problem diagnosis
- Honest attempt at finding repair tutorial videos (even if none found)
- If location provided: nearby garage locations with contact information

Honesty about video availability is preferred over forcing irrelevant content.""",
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