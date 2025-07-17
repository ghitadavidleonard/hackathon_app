"""
OBD Diagnostic Tools Module

This module provides comprehensive OBD diagnostic trouble code analysis tools.
It includes functions for code lookup, extraction, and keyword searching.
"""

import json
import re
import os
from typing import List, Dict, Any, Optional


class OBDCodeHandler:
    """Handler for OBD diagnostic trouble codes with database operations."""
    
    def __init__(self):
        """Initialize the OBD code handler and load the database."""
        self.obd_codes = self._load_obd_database()
    
    def _load_obd_database(self) -> Dict[str, Any]:
        """Load OBD codes from JSON database."""
        db_path = os.path.join(os.path.dirname(__file__), "database", "obd-codes.json")
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading OBD database: {e}")
            return {}
    
    def lookup_obd_code(self, code: str) -> Dict[str, Any]:
        """
        Look up a specific OBD code and return its information.
        
        Args:
            code: OBD diagnostic trouble code (e.g., P0301, P0420)
            
        Returns:
            Dictionary containing code information with keys:
            - code: The original code
            - description: Description of the code
            - causes: List of possible causes
            - found: Boolean indicating if code was found
        """
        code = code.upper().strip()
        
        if code in self.obd_codes:
            return {
                "code": code,
                "description": self.obd_codes[code]["description"],
                "causes": self.obd_codes[code]["causes"],
                "found": True
            }
        else:
            return {
                "code": code,
                "description": "Code not found in database",
                "causes": [],
                "found": False
            }
    
    def extract_and_lookup_obd_codes(self, text: str) -> Dict[str, Any]:
        """
        Extract OBD codes from text and analyze them.
        
        Args:
            text: Text that may contain OBD diagnostic trouble codes
            
        Returns:
            Dictionary containing:
            - total_codes: Number of codes found
            - code_details: List of detailed information for each code
        """
        # Regex pattern to match OBD codes (P, B, C, U followed by 4 digits)
        pattern = r'\b[PBCU]\d{4}\b'
        codes = re.findall(pattern, text.upper())
        
        # Remove duplicates while preserving order
        unique_codes = list(dict.fromkeys(codes))
        
        code_details = []
        for code in unique_codes:
            code_info = self.lookup_obd_code(code)
            code_details.append(code_info)
        
        return {
            "total_codes": len(unique_codes),
            "code_details": code_details
        }
    
    def search_obd_codes_by_keyword(self, keyword: str) -> Dict[str, Any]:
        """
        Search for OBD codes by keyword in their descriptions or causes.
        
        Args:
            keyword: Keyword to search for
            
        Returns:
            Dictionary containing:
            - matching_codes: Number of matching codes
            - codes: List of matching code information
        """
        keyword_lower = keyword.lower()
        matching_codes = []
        
        for code, data in self.obd_codes.items():
            # Search in description
            if keyword_lower in data["description"].lower():
                matching_codes.append({
                    "code": code,
                    "description": data["description"],
                    "causes": data["causes"]
                })
                continue
            
            # Search in causes
            for cause in data["causes"]:
                if keyword_lower in cause.lower():
                    matching_codes.append({
                        "code": code,
                        "description": data["description"],
                        "causes": data["causes"]
                    })
                    break
        
        return {
            "matching_codes": len(matching_codes),
            "codes": matching_codes
        }
    
    def list_available_obd_codes(self) -> Dict[str, Any]:
        """
        List all available OBD codes in the database.
        
        Returns:
            Dictionary containing:
            - total_codes: Total number of codes
            - codes: List of all codes with basic info
        """
        codes_list = []
        for code, data in self.obd_codes.items():
            codes_list.append({
                "code": code,
                "description": data["description"]
            })
        
        return {
            "total_codes": len(codes_list),
            "codes": sorted(codes_list, key=lambda x: x["code"])
        }
    
    def get_obd_code_categories(self) -> Dict[str, Any]:
        """
        Get OBD codes organized by category (P, B, C, U codes).
        
        Returns:
            Dictionary with categories as keys and lists of codes as values
        """
        categories = {
            "P": [],  # Powertrain
            "B": [],  # Body
            "C": [],  # Chassis
            "U": []   # Network/Communication
        }
        
        for code in self.obd_codes.keys():
            category = code[0]
            if category in categories:
                categories[category].append(code)
        
        # Sort codes within each category
        for category in categories:
            categories[category].sort()
        
        return {
            "categories": categories,
            "summary": {cat: len(codes) for cat, codes in categories.items()}
        }


class OBDMCPToolExecutor:
    """Tool executor for OBD diagnostic operations."""
    
    def __init__(self):
        """Initialize the tool executor."""
        self.handler = OBDCodeHandler()
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an OBD diagnostic tool.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            
        Returns:
            Result dictionary from the tool execution
        """
        if tool_name == "lookup_obd_code":
            return self.handler.lookup_obd_code(parameters.get("code", ""))
        elif tool_name == "extract_and_lookup_obd_codes":
            return self.handler.extract_and_lookup_obd_codes(parameters.get("text", ""))
        elif tool_name == "search_obd_codes_by_keyword":
            return self.handler.search_obd_codes_by_keyword(parameters.get("keyword", ""))
        elif tool_name == "list_available_obd_codes":
            return self.handler.list_available_obd_codes()
        elif tool_name == "get_obd_code_categories":
            return self.handler.get_obd_code_categories()
        else:
            return {"error": f"Unknown tool: {tool_name}"}
