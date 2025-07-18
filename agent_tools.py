"""
OBD Diagnostic Tools Module

This module provides OBD diagnostic functionality as LangChain tools.
The agent can use these tools to provide automotive assistance.
"""

import os
import re
import json
import requests
from typing import Optional
from urllib.parse import quote, unquote
from langchain.tools import tool
from obd_tools import OBDCodeHandler
from googleapiclient.discovery import build


# Create a single instance to reuse
_obd_handler = OBDCodeHandler()


def validate_and_format_url(url: str, title: str = "") -> str:
    """
    Validate URL and format it properly for display - ALWAYS returns full URLs, never shortened.
    
    Args:
        url: URL to validate and format
        title: Optional title for the link
        
    Returns:
        Formatted URL string with full URL guaranteed
    """
    if not url:
        return "❌ No URL available"
    
    try:
        # Start with the original URL - DO NOT expand shortened URLs to avoid new shortening
        final_url = url
        
        # Ensure URL has proper protocol
        if not final_url.startswith(('http://', 'https://')):
            final_url = 'https://' + final_url
        
        # Special handling for YouTube URLs to ensure they're full format
        if 'youtube.com' in final_url or 'youtu.be' in final_url:
            # Convert youtu.be to full youtube.com format
            if 'youtu.be/' in final_url:
                video_id = final_url.split('youtu.be/')[-1].split('?')[0].split('&')[0]
                final_url = f"https://www.youtube.com/watch?v={video_id}"
            # Ensure youtube.com URLs are in full format
            elif 'youtube.com' in final_url and 'watch?v=' not in final_url:
                # Handle other YouTube URL formats and convert to standard watch URL
                if '/embed/' in final_url:
                    video_id = final_url.split('/embed/')[-1].split('?')[0].split('&')[0]
                    final_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Format for display - always return the full URL
        if title:
            return f"🔗 **{title}**: {final_url}"
        else:
            return f"🔗 {final_url}"
            
    except Exception:
        # Return original URL if validation fails
        return f"🔗 {url}"


@tool(description="Process uploaded diagnostic files, scan reports, or text files to extract and analyze OBD codes. Use this tool when user mentions they have uploaded a file, attached a diagnostic report, scanner output, or any document containing car diagnostic information. This tool will extract OBD codes from file contents and provide detailed analysis.")
def process_diagnostic_file(file_content: str, file_name: str = "uploaded_file") -> str:
    """Process uploaded diagnostic files to extract and analyze OBD codes."""
    if not file_content.strip():
        return "The uploaded file appears to be empty or unreadable."
    
    # Extract OBD codes from the file content
    pattern = r'\b[PBCU]\d{4}\b'
    found_codes = re.findall(pattern, file_content.upper())
    found_codes = list(set(found_codes))  # Remove duplicates
    
    if not found_codes:
        # Check for common diagnostic keywords even if no codes found
        diagnostic_keywords = [
            'engine', 'transmission', 'abs', 'airbag', 'check engine', 'malfunction',
            'error', 'fault', 'trouble', 'diagnostic', 'scanner', 'obd', 'dtc'
        ]
        
        found_keywords = [kw for kw in diagnostic_keywords if kw.lower() in file_content.lower()]
        
        if found_keywords:
            return f"""📁 **File Analysis Results for {file_name}:**

❌ **No OBD codes found** in the uploaded file, but detected automotive-related content.

**Keywords found:** {', '.join(found_keywords)}

**File content preview:**
```
{file_content[:800]}{'...' if len(file_content) > 800 else ''}
```

**Suggestions:**
• If this is a diagnostic report, the codes might be in a different format
• Try uploading a text file or CSV export from your scanner
• You can also tell me the codes directly (e.g., "I have codes P0301 and P0420")
"""
        else:
            return f"""📁 **File Analysis Results for {file_name}:**

❌ **No OBD codes or automotive content detected** in this file.

**File content preview:**
```
{file_content[:500]}{'...' if len(file_content) > 500 else ''}
```

**This appears to be a non-automotive file. Please upload:**
• OBD scanner reports
• Diagnostic trouble code lists  
• Car diagnostic text files
• Or simply tell me your trouble codes directly"""
    
    # Analyze found codes using existing OBD handler
    analysis_result = f"""📁 **File Analysis Results for {file_name}:**

✅ **Found {len(found_codes)} OBD diagnostic codes:** {', '.join(found_codes)}

**Detailed Analysis:**
"""
    
    # Get detailed analysis for each code
    for code in found_codes:
        code_info = _obd_handler.lookup_obd_code(code)
        if code_info.get("found", False):
            analysis_result += f"""
**{code}:** {code_info['description']}
• **Possible causes:** {', '.join(code_info['causes'])}
"""
        else:
            analysis_result += f"""
**{code}:** Code not found in database (may be manufacturer-specific)
"""
    
    analysis_result += f"""

**File content preview:**
```
{file_content[:400]}{'...' if len(file_content) > 400 else ''}
```

**Next Steps:**
I'll now provide a complete diagnostic analysis following my 5-step process for each code found."""
    
    return analysis_result


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


@tool(description="Search for YouTube repair tutorials and how-to videos for automotive problems. Use this tool when user asks 'how do I fix...' any car problem, after diagnosing OBD codes to find repair videos, when user wants DIY repair instructions, asks for video tutorials or guides, or mentions wanting to learn how to repair something. ALWAYS use this tool after analyzing OBD codes to provide repair guidance. If no relevant videos are found, it will inform the user honestly.")
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
            maxResults=10,  # Get more results to filter better
            type='video',
            order='relevance',
            videoDuration='medium'  # Focus on medium-length tutorials
        ).execute()
        
        if not search_response.get('items'):
            return f"**I could not find any YouTube tutorials for: {query}**\n\n❌ **No relevant repair videos found** - The YouTube search returned no results for this automotive issue.\n\n**Alternative suggestions:**\n• Try searching manually on YouTube with more specific terms\n• Check manufacturer-specific repair channels\n• Consult professional repair documentation\n• Consider seeking help from a qualified mechanic"
        
        # Filter for automotive-related content - Make filtering less restrictive
        automotive_keywords = ['car', 'auto', 'repair', 'fix', 'diagnostic', 'obd', 'engine', 'vehicle', 'mechanic', 'garage', 'toyota', 'ford', 'honda', 'chevrolet', 'bmw', 'mercedes', 'audi', 'volkswagen', 'nissan', 'hyundai', 'kia', 'mazda', 'subaru', 'maintenance', 'service', 'problem', 'issue', 'diy', 'tutorial', 'how', 'code', 'trouble']
        
        relevant_results = []
        all_results = []  # Store all results as backup
        
        for item in search_response['items']:
            title = item['snippet']['title'].lower()
            description = item['snippet']['description'].lower()
            
            title_display = item['snippet']['title']
            channel = item['snippet']['channelTitle']
            video_id = item['id']['videoId']
            
            # Construct full YouTube URL - ALWAYS use full format, never shortened
            full_youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            
            description_snippet = item['snippet']['description'][:100] + "..." if item['snippet']['description'] else "No description available"
            
            # Format video info with full URL guaranteed
            video_info = f"**{title_display}**\nChannel: {channel}\n🔗 YouTube Link: {full_youtube_url}\nDescription: {description_snippet}\n"
            all_results.append(video_info)
            
            # Check if the video is likely automotive-related
            if any(keyword in title or keyword in description for keyword in automotive_keywords):
                relevant_results.append(video_info)
        
        # If no automotive-specific results found, use all results but with a note
        if not relevant_results and all_results:
            display_results = all_results[:5]
            return f"**⚠️ Limited relevant content found for: {query}**\n\nI found {len(display_results)} YouTube tutorials, but they may not be specifically automotive-related:\n\n" + "\n".join(display_results) + "\n\n**❌ Note**: These videos may not be specifically automotive-related. I could not find videos that clearly match automotive repair content. Please review carefully or try more specific search terms."
        
        if not relevant_results:
            return f"**❌ I could not find relevant automotive tutorials for: {query}**\n\n**No automotive-specific content found** - While some videos were found in the search, none appeared to be specifically related to automotive repair.\n\n**Alternative suggestions:**\n• Try more specific search terms (include car make/model)\n• Look for manufacturer-specific repair guides\n• Consult a professional mechanic for this issue\n• Search manually on YouTube with different keywords"
        
        # Limit to top 5 relevant results
        display_results = relevant_results[:5]
        
        return f"Found {len(display_results)} relevant YouTube tutorials for '{query}':\n\n" + "\n".join(display_results)
        
    except Exception as e:
        return f"**❌ Error searching YouTube for repair videos**\n\nI encountered an error while trying to find YouTube tutorials: {str(e)}\n\n**I was unable to retrieve repair videos at this time.** Please try:\n• Searching YouTube manually\n• Checking back later\n• Consulting professional repair resources"


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
            return f"**❌ Error accessing Google Places API**: Status code {response.status_code}\n\n**I was unable to search for nearby garages** due to an API error. Please try:\n• Searching Google Maps directly for 'auto repair near {location}'\n• Using a different location format\n• Trying again later"
        
        data = response.json()
        
        if data['status'] != 'OK' or not data.get('results'):
            return f"**❌ No auto repair shops found near {location}**\n\n**I could not find any garages in this area.** This could be because:\n• The location name might need to be more specific\n• There may be limited auto repair shops in this area\n• The location might not be recognized\n\n**Please try:**\n• Using a more specific address or zip code\n• Searching a nearby larger city\n• Checking Google Maps directly for 'auto repair near {location}'"
        
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
            
            # Create Google Maps link - Force full URLs, avoid shortened links
            maps_link = None
            lat = place.get('geometry', {}).get('location', {}).get('lat')
            lng = place.get('geometry', {}).get('location', {}).get('lng')
            
            # Force full Google Maps URLs (avoid shortened goo.gl links)
            if lat and lng:
                # Use direct coordinates URL (most reliable, always full URL)
                maps_url = f"https://www.google.com/maps/@{lat},{lng},15z"
                maps_link = f"🔗 **View on Google Maps**: {maps_url}"
            elif place_id:
                # Use place_id in search format (avoids shortened URLs)
                maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"
                maps_link = f"🔗 **View on Google Maps**: {maps_url}"
            elif address:
                # Use address search format with proper encoding
                encoded_address = quote(address)
                maps_url = f"https://www.google.com/maps/search/{encoded_address}"
                maps_link = f"🔗 **View on Google Maps**: {maps_url}"
            else:
                # Additional fallback: create a direct search URL
                search_query = f"{name} {location if location else ''}"
                encoded_query = quote(search_query.strip())
                maps_url = f"https://www.google.com/maps/search/{encoded_query}"
                maps_link = f"🔗 **Search on Google Maps**: {maps_url}"
            
            result_text += f"**{i+1}. {name}** {status_icon}\n"
            result_text += f"📍 **Full Address**: {address}\n"
            result_text += f"⭐ **Rating**: {rating_display}\n"
            
            # Always include phone number information
            phone_number = details.get('phone')
            if phone_number:
                result_text += f"📞 **Phone**: {phone_number}\n"
            else:
                result_text += f"📞 **Phone**: Not available (call directory assistance or check Google Maps)\n"
            
            # Google Maps link should always be available now - Force full URLs
            if maps_link:
                result_text += f"{maps_link}\n"
            else:
                # Final fallback with direct search URL (never use shortened links)
                fallback_query = quote(f"{name} auto repair")
                fallback_url = f"https://www.google.com/maps/search/{fallback_query}"
                result_text += f"🔗 **Search on Google Maps**: {fallback_url}\n"
            
            # Website information
            website = details.get('website')
            if website:
                result_text += f"🌐 **Website**: {website}\n"
            
            # Business hours information
            opening_hours = details.get('opening_hours')
            if opening_hours and isinstance(opening_hours, list) and opening_hours:
                # Show first 2 lines of hours (usually current day and next)
                hours_to_show = opening_hours[:2] if len(opening_hours) >= 2 else opening_hours
                hours_text = " | ".join(hours_to_show)
                result_text += f"🕒 **Hours**: {hours_text}\n"
            else:
                result_text += f"🕒 **Hours**: Not available (call for current hours)\n"
            
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
        return f"**❌ Error finding garages**: {str(e)}\n\n**I was unable to search for nearby auto repair shops** due to an error. Please try:\n• Searching Google Maps directly for 'auto repair near {location}'\n• Using a different location format\n• Checking your internet connection\n• Trying again later"


@tool(description="Search for replacement auto parts on Amazon for specific OBD codes or car components. Use this tool when user needs to find replacement parts after diagnosing a problem, asks 'where can I buy parts?', mentions needing to replace a component, or wants to see part prices for DIY repairs. This helps complete the repair process by finding the actual parts needed.")
def search_auto_parts(query: str) -> str:
    """Search for replacement auto parts on Amazon for specific OBD codes or car components."""
    try:
        # Get Google Custom Search API credentials
        api_key = os.environ.get("GOOGLE_SEARCH_API_KEY")
        cse_id = os.environ.get("GOOGLE_CSE_ID")
        
        if not api_key or not cse_id:
            return "**❌ Parts search not configured**\n\nGoogle Custom Search API credentials not available. Please try:\n• Searching Amazon directly for replacement parts\n• Using the specific part names I mentioned in the diagnosis\n• Consulting your local auto parts store"
        
        # Enhanced search query to focus on replacement parts
        search_query = f"{query} replacement part automotive site:amazon.com"
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": cse_id,
            "q": search_query,
            "num": 5,  # number of results to return
        }

        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return f"**❌ Error accessing parts search**: Status code {response.status_code}\n\n**I was unable to search for replacement parts** due to an API error. Please try searching Amazon directly for the part names mentioned in the diagnosis."
        
        results = response.json()
        
        if not results.get("items"):
            return f"**❌ No replacement parts found for: {query}**\n\n**I could not find specific parts on Amazon** for this component. You may want to:\n• Search manually on Amazon with more specific part numbers\n• Check your vehicle's manual for exact part specifications\n• Visit your local auto parts store (AutoZone, O'Reilly, etc.)\n• Contact your car dealer for OEM parts"
        
        parts_list = []
        for item in results.get("items", []):
            title = item.get("title", "Unknown")
            link = item.get("link", "")
            snippet = item.get("snippet", "No description available")
            
            # Clean up the snippet (remove extra whitespace and truncate)
            snippet = " ".join(snippet.split())[:150] + "..." if len(snippet) > 150 else snippet
            
            # Format URL directly without validation to avoid any URL shortening
            if link:
                if not link.startswith(('http://', 'https://')):
                    link = 'https://' + link
                formatted_url = f"🔗 **Amazon Link**: {link}"
            else:
                formatted_url = "🔗 **Amazon Link**: Not available"
            
            parts_list.append(f"**{title}**\n{formatted_url}\n📝 Description: {snippet}\n")
        
        parts_text = f"🛒 **REPLACEMENT PARTS FOUND FOR: {query}**\n\n"
        parts_text += f"Found {len(parts_list)} replacement parts on Amazon:\n\n"
        parts_text += "\n".join(parts_list)
        
        parts_text += "\n**💡 Parts Shopping Tips:**\n"
        parts_text += "• Verify part compatibility with your specific vehicle year/make/model\n"
        parts_text += "• Check seller ratings and reviews before purchasing\n"
        parts_text += "• Compare prices across multiple sellers\n"
        parts_text += "• Consider OEM vs aftermarket options\n"
        parts_text += "• Read return policy before ordering"
        
        return parts_text
        
    except Exception as e:
        return f"**❌ Error searching for replacement parts**: {str(e)}\n\n**I was unable to search for parts** due to an error. Please try:\n• Searching Amazon directly for the component names\n• Visiting your local auto parts store\n• Checking your vehicle manual for part numbers\n• Trying again later"


def get_place_details(place_id: str, api_key: str) -> dict:
    """
    Get detailed information about a specific place using Google Places API.
    
    Args:
        place_id: Google Places ID
        api_key: Google Maps API key
        
    Returns:
        Dictionary with place details including phone, website, and hours
    """
    if not place_id or not api_key:
        return {}
        
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'place_id': place_id,
            'key': api_key,
            'fields': 'formatted_phone_number,international_phone_number,website,opening_hours,formatted_address,business_status'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'OK':
                result = data.get('result', {})
                
                # Handle opening hours more safely
                opening_hours_data = result.get('opening_hours', {})
                weekday_text = opening_hours_data.get('weekday_text', []) if isinstance(opening_hours_data, dict) else []
                
                # Get the best available phone number
                phone = result.get('formatted_phone_number') or result.get('international_phone_number')
                
                return {
                    'phone': phone,
                    'website': result.get('website'),
                    'opening_hours': weekday_text,
                    'business_status': result.get('business_status', 'UNKNOWN')
                }
        
        return {}
        
    except Exception:
        # Silently fail and return empty dict to not break the main function
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
    process_diagnostic_file,
    lookup_obd_code,
    extract_and_analyze_obd_codes,
    search_obd_codes_by_keyword,
    list_available_obd_codes,
    get_obd_code_categories,
    search_youtube_car_tutorials,
    find_nearby_garages,
    search_auto_parts
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
    "process_diagnostic_file": process_diagnostic_file.func,
    "lookup_obd_code": lookup_obd_code.func,
    "extract_and_analyze_obd_codes": extract_and_analyze_obd_codes.func,
    "search_obd_codes_by_keyword": search_obd_codes_by_keyword.func,
    "list_available_obd_codes": list_available_obd_codes.func,
    "get_obd_code_categories": get_obd_code_categories.func,
    "search_youtube_car_tutorials": search_youtube_car_tutorials.func,
    "find_nearby_garages": find_nearby_garages.func,
    "search_auto_parts": search_auto_parts.func,
    "get_place_details": get_place_details,
    "detect_obd_codes_in_message": detect_obd_codes_in_message
}
