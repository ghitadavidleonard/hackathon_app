from typing import Any, Awaitable, Callable, Dict, List, Tuple, TypedDict, cast

# Tool definitions and their handlers
tools: List[Tuple[Dict[str, Any], Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]]] = []

class EchoToolArguments(TypedDict):
    text: str

# Example tool - you can add your OBD-specific tools here
async def echo_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Echo the input text."""
    args = cast(EchoToolArguments, args)
    return {"text": args["text"]}

# Define the echo tool
echo_tool_def = {
    "name": "echo",
    "description": "Echo the input text.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to echo.",
            },
        },
        "required": ["text"],
    },
}

# Register the tool
tools.append((echo_tool_def, echo_handler))

# Add OBD-specific tools
import os
import json
from pathlib import Path

# Load OBD code database
def load_obd_codes():
    try:
        database_path = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'obd-codes.json'))
        if database_path.exists():
            with open(database_path, 'r') as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        print(f"Error loading OBD codes database: {e}")
        return {}

obd_database = load_obd_codes()

class OBDCodeToolArguments(TypedDict):
    code: str

# OBD Code lookup tool
async def lookup_obd_code_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Look up information about an OBD diagnostic code."""
    args = cast(OBDCodeToolArguments, args)
    code = args["code"].upper()
    
    # Perform lookup in the database
    if obd_database and code in obd_database:
        info = obd_database[code]
        return {
            "code": code,
            "description": info.get("description", "Unknown code"),
            "severity": info.get("severity", "Unknown"),
            "causes": info.get("causes", []),
            "solutions": info.get("solutions", [])
        }
    else:
        return {
            "code": code,
            "description": "OBD code not found in database",
            "severity": "Unknown",
            "causes": [],
            "solutions": ["Consult vehicle manual or professional mechanic"]
        }

lookup_obd_code_tool_def = {
    "name": "lookup_obd_code",
    "description": "Look up information about an OBD diagnostic code.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The OBD code to look up (e.g., P0301).",
            },
        },
        "required": ["code"],
    },
}

tools.append((lookup_obd_code_tool_def, lookup_obd_code_handler))
