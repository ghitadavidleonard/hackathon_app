"""
OBD Diagnostic Tools Module

This module provides OBD diagnostic functionality as LangChain tools.
The agent can use these tools to provide automotive assistance.
"""

import os
import re
import requests
from langchain.tools import tool
from obd_tools import OBDCodeHandler
from googleapiclient.discovery import build


# Create a single instance to reuse
_obd_handler = OBDCodeHandler()


@tool(description="Look up detailed information about a specific OBD diagnostic trouble code. Use this tool when user provides a single specific OBD code (like P0301, P0420, B0001, etc.), you need detailed information about one particular code, or user asks 'What does code P0301 mean?'")
def lookup_obd_code(code: str) -> str:
    """Look up detailed information about a specific OBD diagnostic trouble code."""
    result = _obd_handler.lookup_obd_code(code)
    
    if result.get("found", False):
        return f"OBD Code {result['code']}: {result['description']}. Possible causes: {', '.join(result['causes'])}"
    else:
        return f"OBD Code {result['code']} not found in database."


@tool(description="Extract and analyze ALL OBD diagnostic trouble codes found in user's message text. Use this tool when user mentions error codes in their message (like 'my car shows P0301 and P0420'), says 'I have these codes' or 'scanner shows codes', provides multiple codes at once, or describes error messages from their car's display. This is the PRIMARY tool for OBD code analysis - use this first when users mention any error codes.")
def extract_and_analyze_obd_codes(text: str) -> str:
    """Extract and analyze ALL OBD diagnostic trouble codes found in user's message text."""
    result = _obd_handler.extract_and_lookup_obd_codes(text)
    
    if result['total_codes'] == 0:
        return "No OBD diagnostic trouble codes found in the provided text."
    
    analysis = f"Found {result['total_codes']} OBD codes in the text:\n\n"
    
    for code_detail in result['code_details']:
        if code_detail['found']:
            analysis += f"• {code_detail['code']}: {code_detail['description']}\n"
            analysis += f"  Possible causes: {', '.join(code_detail['causes'])}\n\n"
        else:
            analysis += f"• {code_detail['code']}: Code not found in database\n\n"
    
    return analysis


@tool(description="Search for OBD codes by symptoms, problems, or component keywords. Use this tool when user describes symptoms without mentioning specific codes (like 'engine misfire', 'rough idle'), asks 'what codes are related to...' a specific problem, mentions car parts or systems (like 'catalytic converter', 'oxygen sensor'), or describes problems like 'car won't start', 'engine shaking', 'poor fuel economy'.")
def search_obd_codes_by_keyword(keyword: str) -> str:
    """Search for OBD codes by symptoms, problems, or component keywords."""
    result = _obd_handler.search_obd_codes_by_keyword(keyword)
    
    if result['matching_codes'] == 0:
        return f"No OBD codes found matching keyword '{keyword}'."
    
    search_results = f"Found {result['matching_codes']} OBD codes matching '{keyword}':\n\n"
    
    # Limit to first 10 results to avoid overwhelming output
    for i, code in enumerate(result['codes'][:10]):
        search_results += f"• {code['code']}: {code['description']}\n"
        if i >= 9 and len(result['codes']) > 10:
            search_results += f"... and {len(result['codes']) - 10} more codes\n"
            break
    
    return search_results


@tool(description="List all available OBD codes in the diagnostic database. Use this tool when user asks 'what codes do you have?' or 'show me all codes', wants to browse available diagnostic codes, asks about the database contents or coverage, or for general information about what codes are supported.")
def list_available_obd_codes() -> str:
    """List all available OBD codes in the diagnostic database."""
    result = _obd_handler.list_available_obd_codes()
    
    codes_summary = f"Database contains {result['total_codes']} OBD codes:\n\n"
    
    # Show first 20 codes as preview
    for i, code in enumerate(result['codes'][:20]):
        codes_summary += f"• {code['code']}: {code['description']}\n"
        if i >= 19 and len(result['codes']) > 20:
            codes_summary += f"... and {len(result['codes']) - 20} more codes\n"
            break
    
    return codes_summary


@tool(description="Get overview of OBD code categories and their meanings. Use this tool when user asks about different types of OBD codes, wants to understand what P, B, C, U codes mean, asks 'what's the difference between P and B codes?', or for educational information about OBD code classification.")
def get_obd_code_categories() -> str:
    """Get overview of OBD code categories and their meanings."""
    # Create categories from the database
    categories = {"P": 0, "B": 0, "C": 0, "U": 0}
    
    for code in _obd_handler.obd_codes.keys():
        first_char = code[0] if code else ""
        if first_char in categories:
            categories[first_char] += 1
    
    summary = "OBD Code Categories:\n\n"
    
    category_names = {
        "P": "Powertrain",
        "B": "Body", 
        "C": "Chassis",
        "U": "Network/Communication"
    }
    
    for category, count in categories.items():
        category_name = category_names.get(category, category)
        summary += f"• {category} ({category_name}): {count} codes\n"
    
    return summary


@tool(description="Search for YouTube repair tutorials and how-to videos for automotive problems. Use this tool when user asks 'how do I fix...' any car problem, after diagnosing OBD codes to find repair videos, when user wants DIY repair instructions, asks for video tutorials or guides, or mentions wanting to learn how to repair something. ALWAYS use this tool after analyzing OBD codes to provide repair guidance.")
def search_youtube_car_tutorials(query: str) -> str:
    """Search for YouTube repair tutorials and how-to videos for automotive problems."""
    try:
        # You'll need to get a YouTube Data API key from Google Cloud Console
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            return "YouTube API key not configured. Please set YOUTUBE_API_KEY environment variable."
        
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Enhanced search query to focus on car repair tutorials
        search_query = f"{query} car repair tutorial how to fix"
        
        search_response = youtube.search().list(
            q=search_query,
            part='id,snippet',
            maxResults=5,
            type='video',
            order='relevance',
            videoDuration='medium'  # Focus on medium-length tutorials
        ).execute()
        
        if not search_response.get('items'):
            return f"No YouTube tutorials found for: {query}"
        
        results = []
        for item in search_response['items']:
            title = item['snippet']['title']
            channel = item['snippet']['channelTitle']
            video_id = item['id']['videoId']
            url = f"https://www.youtube.com/watch?v={video_id}"
            description = item['snippet']['description'][:100] + "..."
            
            results.append(f"**{title}**\nChannel: {channel}\nURL: {url}\nDescription: {description}\n")
        
        return f"Found {len(results)} YouTube tutorials for '{query}':\n\n" + "\n".join(results)
        
    except Exception as e:
        return f"Error searching YouTube: {str(e)}"


@tool(description="Find nearby auto repair garages with ratings, contact info, and business details using Google Maps. Use this tool when user asks for garages, mechanics, or auto repair shops near them, needs professional help after diagnosing codes, mentions a location and wants local services, asks 'where can I get this fixed?' or 'find a mechanic near me', or provides location like city, zip code, or address. ALWAYS use this tool when users need professional automotive services.")
def find_nearby_garages(location: str = None, service_type: str = "auto repair") -> str:
    """Find nearby auto repair garages with ratings, contact info, and business details using Google Maps."""
    try:
        if not location:
            return """To find nearby garages, please provide your location (city, zip code, or address).

Example: "Find garages near 12345" or "Find garages in New York, NY"

**General Tips for Finding Quality Auto Repair Shops:**
• Check online reviews (Google, Yelp, BBB)
• Look for ASE certified technicians
• Ask for estimates before work begins
• Verify licenses and insurance
• Check if they specialize in your car's make/model"""
        
        # Get Google Maps API key
        api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        if not api_key:
            return f"""**Auto Repair Shops Near {location}:**

*Google Maps API key not configured. Using general recommendations:*

**National Chains (Usually Available):**
• **AutoZone** - Parts and basic diagnostics
• **Jiffy Lube** - Oil changes and basic maintenance  
• **Valvoline Instant Oil Change** - Quick maintenance
• **Midas** - Full automotive repair services
• **AAMCO** - Transmission and general repair
• **Firestone Complete Auto Care** - Comprehensive services

**How to Find Local Shops:**
1. Search Google Maps for "auto repair near {location}"
2. Check Yelp reviews for quality ratings
3. Call your car dealer for recommended service centers
4. Ask for referrals from friends and family

**When Calling Shops, Ask About:**
• Diagnostic fees (usually $100-150)
• Labor rates per hour
• Warranty on repairs
• Estimated completion time
• If they work on your car's make/model"""
        
        # Use Google Places API to find nearby garages
        base_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        # Search query for auto repair shops
        query = f"auto repair shop near {location}"
        
        params = {
            'query': query,
            'key': api_key,
            'type': 'car_repair',
            'radius': 10000,  # 10km radius
        }
        
        response = requests.get(base_url, params=params)
        
        if response.status_code != 200:
            return f"Error accessing Google Places API: {response.status_code}"
        
        data = response.json()
        
        if data['status'] != 'OK' or not data.get('results'):
            return f"No auto repair shops found near {location}. Try a different location or check spelling."
        
        # Format the results
        result_text = f"🏪 **Auto Repair Shops Near {location}:**\n\n"
        
        # Limit to top 8 results
        for i, place in enumerate(data['results'][:8]):
            name = place.get('name', 'Unknown')
            address = place.get('formatted_address', 'Address not available')
            rating = place.get('rating', 'No rating')
            user_ratings_total = place.get('user_ratings_total', 0)
            
            # Get business status
            business_status = place.get('business_status', 'UNKNOWN')
            status_icon = "🟢" if business_status == "OPERATIONAL" else "🟡"
            
            # Format rating display
            if isinstance(rating, (int, float)):
                stars = "⭐" * int(rating)
                rating_display = f"{rating}/5 {stars} ({user_ratings_total} reviews)"
            else:
                rating_display = "No rating available"
            
            # Get place details for more info (phone, website)
            place_id = place.get('place_id')
            details = get_place_details(place_id, api_key) if place_id else {}
            
            result_text += f"**{i+1}. {name}** {status_icon}\n"
            result_text += f"📍 Address: {address}\n"
            result_text += f"⭐ Rating: {rating_display}\n"
            
            if details.get('phone'):
                result_text += f"📞 Phone: {details['phone']}\n"
            
            if details.get('website'):
                result_text += f"🌐 Website: {details['website']}\n"
            
            if details.get('opening_hours'):
                result_text += f"🕒 Hours: {details['opening_hours']}\n"
            
            result_text += "\n"
        
        # Add helpful tips
        result_text += """**💡 Tips for Choosing a Garage:**
• Check reviews and ratings carefully
• Ask about warranties on repairs
• Get estimates before agreeing to work
• Verify they work on your car's make/model
• Ask about diagnostic fees upfront
• Look for ASE certified technicians"""
        
        return result_text
        
    except Exception as e:
        return f"Error finding garages: {str(e)}\n\nPlease try searching Google Maps directly for 'auto repair near {location}'"


def get_place_details(place_id: str, api_key: str) -> dict:
    """
    Get detailed information about a specific place using Google Places API.
    
    Args:
        place_id: Google Places ID
        api_key: Google Maps API key
        
    Returns:
        Dictionary with place details
    """
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'place_id': place_id,
            'key': api_key,
            'fields': 'formatted_phone_number,website,opening_hours'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK':
                result = data.get('result', {})
                return {
                    'phone': result.get('formatted_phone_number'),
                    'website': result.get('website'),
                    'opening_hours': result.get('opening_hours', {}).get('weekday_text', [])
                }
        
        return {}
        
    except Exception:
        return {}


def detect_obd_codes_in_message(message: str) -> bool:
    """
    Detect if a message contains OBD diagnostic trouble codes.
    
    Args:
        message: User's message text
        
    Returns:
        Boolean indicating if OBD codes were detected
    """
    # Regex pattern to match OBD codes (P, B, C, U followed by 4 digits)
    pattern = r'\b[PBCU]\d{4}\b'
    codes = re.findall(pattern, message.upper())
    return len(codes) > 0


# List of tools for the agent to use
OBD_TOOLS = [
    lookup_obd_code,
    extract_and_analyze_obd_codes,
    search_obd_codes_by_keyword,
    list_available_obd_codes,
    get_obd_code_categories,
    search_youtube_car_tutorials,
    find_nearby_garages
]

# Keep the non-tool functions for direct access
def detect_obd_codes_in_message(message: str) -> bool:
    """
    Detect if a message contains OBD diagnostic trouble codes.
    
    Args:
        message: User's message text
        
    Returns:
        Boolean indicating if OBD codes were detected
    """
    # Regex pattern to match OBD codes (P, B, C, U followed by 4 digits)
    pattern = r'\b[PBCU]\d{4}\b'
    codes = re.findall(pattern, message.upper())
    return len(codes) > 0


# Backward compatibility - keep AVAILABLE_FUNCTIONS for any direct function calls
AVAILABLE_FUNCTIONS = {
    "lookup_obd_code": lookup_obd_code.func,
    "extract_and_analyze_obd_codes": extract_and_analyze_obd_codes.func,
    "search_obd_codes_by_keyword": search_obd_codes_by_keyword.func,
    "list_available_obd_codes": list_available_obd_codes.func,
    "get_obd_code_categories": get_obd_code_categories.func,
    "search_youtube_car_tutorials": search_youtube_car_tutorials.func,
    "find_nearby_garages": find_nearby_garages.func,
    "get_place_details": get_place_details,
    "detect_obd_codes_in_message": detect_obd_codes_in_message
}
