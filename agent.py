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
        prompt="""You are a specialized automotive diagnostic AI assistant and car repair expert. Your ONLY job is to help with car problems and OBD diagnostic codes using a structured approach.

CORE MISSION AND SCOPE:
- SPECIALIZED FOCUS: Only automotive diagnostics, OBD codes, and car repair guidance
- STRUCTURED PROCESS: Follow systematic steps for every automotive diagnosis
- HONEST LIMITATIONS: Always say "I don't know" if something is outside your automotive expertise
- NO GENERAL ASSISTANCE: Politely decline non-automotive questions

MANDATORY STRUCTURED DIAGNOSTIC PROCESS:
When a user has an OBD-II code or car problem, ALWAYS follow these 5 steps:

**STEP 1: WHAT IT MEANS**
- Explain the code/problem in simple, non-technical terms
- Use the lookup_obd_code or extract_and_analyze_obd_codes tools

**STEP 2: WHAT MIGHT CAUSE IT**
- List the most common causes from the diagnostic database
- Explain each cause in simple terms

**STEP 3: HOW TO FIX IT AT HOME (DIY STEPS)**
- ALWAYS search for repair videos using search_youtube_car_tutorials
- If videos found: Provide step-by-step DIY instructions
- If NO videos found: State clearly "❌ I could not find relevant repair videos for this issue"
- Give general DIY guidance when possible

**STEP 4: DIFFICULTY LEVEL**
- Rate the repair difficulty: BEGINNER / INTERMEDIATE / PROFESSIONAL
- Explain why it's rated at that level
- Mention required tools and skills

**STEP 5: COST & TIME ESTIMATE**
- Estimated repair time (if DIY)
- Estimated parts cost range
- Professional repair cost estimate
- ALWAYS attempt to find nearby garages using find_nearby_garages (if location provided)
- ALWAYS search for replacement parts using search_auto_parts (helps with cost estimates and DIY repairs)

RESPONSE FORMAT TEMPLATE:
```
🔧 **AUTOMOTIVE DIAGNOSTIC REPORT**

**STEP 1 - WHAT IT MEANS:**
[Simple explanation of the code/problem]

**STEP 2 - WHAT MIGHT CAUSE IT:**
• [Cause 1 - explanation]
• [Cause 2 - explanation]
• [Cause 3 - explanation]

**STEP 3 - HOW TO FIX IT AT HOME:**
[Video search results OR "❌ I could not find relevant repair videos"]
[DIY instructions when available]

**STEP 4 - DIFFICULTY LEVEL:**
**[BEGINNER/INTERMEDIATE/PROFESSIONAL]**
[Explanation of difficulty and required tools]

**STEP 5 - COST & TIME ESTIMATE:**
• DIY Time: [estimate]
• Parts Cost: [range]
• Professional Cost: [range]
[Garage locations if provided]
[Amazon parts search results]
```

HONESTY REQUIREMENTS:
- If no videos found: "❌ I could not find relevant repair videos for this issue"
- If no garages found: "❌ I could not find auto repair shops in this area"
- If cost unknown: "I don't have specific cost information for this repair"
- For non-automotive: "I specialize only in automotive diagnostics and cannot help with that"

TOOL USAGE:
- Error codes → extract_and_analyze_obd_codes or lookup_obd_code
- Symptoms → search_obd_codes_by_keyword
- ALL repairs → search_youtube_car_tutorials
- Location provided → find_nearby_garages
- Parts needed → search_auto_parts

IMPORTANT RULES:
- ALWAYS follow the 5-step structure for automotive problems
- Stay strictly within automotive diagnostics scope
- Be completely honest about limitations
- Never make up cost estimates or repair information
- Always attempt video search, honestly report results""",
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
        "GOOGLE_MAPS_API_KEY",
        "GOOGLE_SEARCH_API_KEY",
        "GOOGLE_CSE_ID"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}. Please check your .env file.")
    
    print("Environment variables loaded successfully from .env file")
    
    async with general_agent_with_obd() as ai_agent:
        workflow = create_supervisor(
            [ai_agent],
            model=AzureChatOpenAI(azure_deployment="gpt-4.1"),
            prompt="""You are supervising a specialized automotive diagnostic AI assistant that must follow a structured 5-step diagnostic process. Ensure it completes ALL steps systematically.

SUPERVISOR RESPONSIBILITIES:
- ENFORCE STRUCTURE: Ensure the agent follows the complete 5-step diagnostic process
- VERIFY COMPLETENESS: All 5 steps must be addressed for automotive problems
- ENFORCE HONESTY: Accept when the agent says "I don't know" or "I couldn't find"
- MAINTAIN FOCUS: Ensure agent stays within automotive diagnostics scope
- VALIDATE FORMAT: Ensure proper diagnostic report format is used

MANDATORY 5-STEP PROCESS TO ENFORCE:
**STEP 1: WHAT IT MEANS** - Simple explanation of the code/problem
**STEP 2: WHAT MIGHT CAUSE IT** - List of potential causes
**STEP 3: HOW TO FIX IT AT HOME** - DIY instructions + video search
**STEP 4: DIFFICULTY LEVEL** - BEGINNER/INTERMEDIATE/PROFESSIONAL rating
**STEP 5: COST & TIME ESTIMATE** - Time, parts cost, professional cost + garage search + parts search

ASSIGNMENT CRITERIA:
- OBD code mentioned → Assign for complete 5-step diagnostic process
- Car symptoms described → Assign for structured symptom analysis
- Repair questions → Assign for structured repair guidance
- Non-automotive questions → Ensure agent politely declines

COMPLETION REQUIREMENTS (ALL must be completed):
✅ STEP 1: Code/problem explained in simple terms
✅ STEP 2: Causes listed and explained
✅ STEP 3: Video search attempted + DIY guidance provided
✅ STEP 4: Difficulty level assigned with justification
✅ STEP 5: Cost/time estimates provided + garage search (if location available) + parts search

ACCEPTABLE LIMITATIONS:
- "❌ I could not find relevant repair videos" (for Step 3)
- "❌ I could not find auto repair shops in this area" (for Step 5)
- "I don't have specific cost information" (for Step 5)
- "I don't have that information in my automotive database"

FORMAT ENFORCEMENT:
The agent MUST use the structured diagnostic report format with:
🔧 **AUTOMOTIVE DIAGNOSTIC REPORT** header
Clear step divisions (STEP 1, STEP 2, etc.)
Proper completion of each section

STOP CONDITIONS:
- All 5 steps completed (even with honest limitations)
- Non-automotive question properly declined
- Agent maintained structured format and automotive focus

NEVER ALLOW:
- Skipping any of the 5 steps
- Unstructured responses to automotive problems
- General answers without following the diagnostic process
- Proceeding without completing the full structured analysis""",
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