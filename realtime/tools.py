import chainlit as cl
import plotly
import os
import sys

# Add the parent directory to the path to import obd_tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from obd_tools import OBDCodeHandler

# Create OBD handler instance
_obd_handler = OBDCodeHandler()

# DTC Code Lookup Tool
lookup_dtc_code_def = {
    "name": "lookup_dtc_code",
    "description": "Look up detailed information about a specific DTC (Diagnostic Trouble Code) like P0301, P0420, B0001, etc. Returns description, causes, and solutions.",
    "parameters": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The DTC code to look up (e.g., P0301, P0420, B0001)",
            },
        },
        "required": ["code"],
    },
}

async def lookup_dtc_code_handler(code):
    """Look up detailed information about a specific DTC code."""
    try:
        result = _obd_handler.lookup_obd_code(code)
        if result.get("found"):
            return {
                "code": result["code"],
                "description": result["description"],
                "causes": result.get("causes", []),
                "solutions": result.get("solutions", []),
                "found": True
            }
        else:
            return {"error": f"DTC code {code} not found in database", "found": False}
    except Exception as e:
        return {"error": str(e), "found": False}

lookup_dtc_code = (lookup_dtc_code_def, lookup_dtc_code_handler)

# Extract and Analyze DTC Codes Tool
extract_dtc_codes_def = {
    "name": "extract_dtc_codes",
    "description": "Extract and analyze all DTC codes found in a text message. Use when user mentions multiple codes or describes error messages.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The text to search for DTC codes",
            },
        },
        "required": ["text"],
    },
}

async def extract_dtc_codes_handler(text):
    """Extract and analyze all DTC codes found in text."""
    try:
        result = _obd_handler.extract_codes(text)
        if result:
            analysis = []
            for code in result:
                code_info = _obd_handler.lookup_obd_code(code)
                if code_info.get("found"):
                    analysis.append({
                        "code": code,
                        "description": code_info["description"],
                        "causes": code_info.get("causes", []),
                        "solutions": code_info.get("solutions", [])
                    })
            return {"codes_found": result, "analysis": analysis}
        else:
            return {"error": "No DTC codes found in the provided text", "codes_found": []}
    except Exception as e:
        return {"error": str(e), "codes_found": []}

extract_dtc_codes = (extract_dtc_codes_def, extract_dtc_codes_handler)

# Search DTC Codes by Symptoms Tool
search_dtc_by_symptoms_def = {
    "name": "search_dtc_by_symptoms",
    "description": "Search for DTC codes related to specific symptoms, problems, or components like 'engine misfire', 'rough idle', 'catalytic converter', etc.",
    "parameters": {
        "type": "object",
        "properties": {
            "symptoms": {
                "type": "string",
                "description": "The symptoms, problems, or components to search for",
            },
        },
        "required": ["symptoms"],
    },
}

async def search_dtc_by_symptoms_handler(symptoms):
    """Search for DTC codes by symptoms or keywords."""
    try:
        result = _obd_handler.search_by_keyword(symptoms)
        if result:
            return {"matches": result, "found": True}
        else:
            return {"error": f"No DTC codes found matching symptoms: {symptoms}", "found": False}
    except Exception as e:
        return {"error": str(e), "found": False}

search_dtc_by_symptoms = (search_dtc_by_symptoms_def, search_dtc_by_symptoms_handler)

draw_plotly_chart_def = {
    "name": "draw_plotly_chart",
    "description": "Draws a Plotly chart based on the provided JSON figure and displays it with an accompanying message.",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The message to display alongside the chart",
            },
            "plotly_json_fig": {
                "type": "string",
                "description": "A JSON string representing the Plotly figure to be drawn",
            },
        },
        "required": ["message", "plotly_json_fig"],
    },
}


async def draw_plotly_chart_handler(message: str, plotly_json_fig):
    fig = plotly.io.from_json(plotly_json_fig)
    elements = [cl.Plotly(name="chart", figure=fig, display="inline")]

    await cl.Message(content=message, elements=elements).send()


draw_plotly_chart = (draw_plotly_chart_def, draw_plotly_chart_handler)


tools = [lookup_dtc_code, extract_dtc_codes, search_dtc_by_symptoms, draw_plotly_chart]
