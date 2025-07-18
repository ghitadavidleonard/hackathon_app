import chainlit as cl
import aiohttp
import re
import json
import tempfile
import os
from pathlib import Path

@cl.on_chat_start
async def start():
    """Initialize the chat session with file upload capabilities."""
    await cl.Message(
        content="🔧 **Welcome to OBD Diagnostic Assistant!**\n\n"
                "I can help you with:\n"
                "• **OBD diagnostic codes** - Tell me your error codes (like P0301, P0420)\n"
                "• **Car symptoms** - Describe what's wrong with your car\n"
                "• **File uploads** - Upload diagnostic reports, scanner outputs, or text files containing OBD codes\n\n"
                "Just type your question or upload a file containing diagnostic information!"
    ).send()

def extract_text_from_file(file_path: str, file_name: str) -> str:
    """Extract text content from uploaded files."""
    try:
        file_extension = Path(file_name).suffix.lower()
        
        # Handle different file types
        if file_extension in ['.txt', '.log', '.csv', '.dat', '.out']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return content
        elif file_extension == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        elif file_extension in ['.xml', '.html', '.htm']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Basic text extraction from XML/HTML (remove tags)
                import re
                clean_text = re.sub(r'<[^>]+>', ' ', content)
                return clean_text
        elif file_extension in ['.pdf']:
            # For PDF files, return a message indicating the limitation
            return f"PDF file detected: {file_name}. Please convert to text format or copy/paste the OBD codes directly."
        else:
            # Try to read as text anyway for unknown extensions
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Check if content looks like text
                if len(content) > 0 and content.isprintable():
                    return content
                else:
                    return f"Binary or unreadable file: {file_name}. Please upload text-based diagnostic files."
    except UnicodeDecodeError:
        return f"Unable to read file {file_name}: appears to be binary or uses unsupported encoding."
    except json.JSONDecodeError:
        return f"Invalid JSON file: {file_name}. Please check file format."
    except Exception as e:
        return f"Error reading file {file_name}: {str(e)}"

def find_obd_codes_in_text(text: str) -> list:
    """Find OBD codes in text using regex with enhanced detection."""
    codes = []
    
    # Primary pattern: Standard OBD codes (P, B, C, U followed by 4 digits)
    pattern_standard = r'\b[PBCU]\d{4}\b'
    standard_codes = re.findall(pattern_standard, text.upper())
    codes.extend(standard_codes)
    
    # Secondary pattern: Codes with dashes or spaces (P0301, P-0301, P 0301)
    pattern_separated = r'\b[PBCU][-\s]?\d{4}\b'
    separated_codes = re.findall(pattern_separated, text.upper())
    # Clean up the separated codes
    for code in separated_codes:
        clean_code = re.sub(r'[-\s]', '', code)
        if clean_code not in codes:
            codes.append(clean_code)
    
    # Tertiary pattern: Look for "code" or "DTC" followed by OBD code
    pattern_keyword = r'(?:code|dtc|error)[\s:]*([PBCU][-\s]?\d{4})'
    keyword_matches = re.findall(pattern_keyword, text.upper(), re.IGNORECASE)
    for match in keyword_matches:
        clean_code = re.sub(r'[-\s]', '', match)
        if clean_code not in codes:
            codes.append(clean_code)
    
    # Remove duplicates and return
    return list(set(codes))

@cl.on_message
async def main(message: cl.Message):
    msg = cl.Message(content="")
    api_url = "http://localhost:8005/ask"
    
    # Check if there are file attachments
    file_content = ""
    files_processed = 0
    
    if message.elements:
        await cl.Message(content="🔍 **Processing uploaded files...**").send()
        
        for element in message.elements:
            if hasattr(element, 'path') and element.path:
                files_processed += 1
                
                # Extract text from uploaded file
                extracted_text = extract_text_from_file(element.path, element.name)
                
                # Find OBD codes in the file
                found_codes = find_obd_codes_in_text(extracted_text)
                
                if found_codes:
                    file_content += f"\n\n📁 **File Analysis - {element.name}:**\n"
                    file_content += f"✅ Found {len(found_codes)} OBD codes: {', '.join(found_codes)}\n"
                    file_content += f"📄 File content excerpt:\n```\n{extracted_text[:500]}{'...' if len(extracted_text) > 500 else ''}\n```\n"
                    
                    # Show immediate feedback to user
                    await cl.Message(
                        content=f"✅ **{element.name}** - Found {len(found_codes)} OBD codes: {', '.join(found_codes)}"
                    ).send()
                else:
                    file_content += f"\n\n📁 **File Analysis - {element.name}:**\n"
                    file_content += f"❌ No OBD codes found in this file.\n"
                    file_content += f"📄 File content excerpt:\n```\n{extracted_text[:500]}{'...' if len(extracted_text) > 500 else ''}\n```\n"
                    
                    # Show feedback for files without codes
                    await cl.Message(
                        content=f"❌ **{element.name}** - No OBD codes detected. File appears to contain: {extracted_text[:100]}..."
                    ).send()
    
    # Combine message content with file analysis
    combined_query = message.content
    if file_content:
        combined_query += file_content
        await cl.Message(content=f"🔧 **Starting diagnostic analysis for {files_processed} file(s)...**").send()
    
    prompt = {"query": combined_query, "history": cl.chat_context.to_openai()}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=prompt) as r:
                if r.status == 200:
                    async for data in r.content.iter_any():
                        if data:
                            decoded_data = data.decode('utf-8', errors='ignore')
                            await msg.stream_token(decoded_data)
                    await msg.send()
                else:
                    error_text = await r.text()
                    await cl.Message(
                        content=f"❌ **Server Error ({r.status}):** {error_text}"
                    ).send()
                
    except aiohttp.ClientConnectorError:
        await cl.Message(
            content="❌ **Connection Error:** Cannot connect to the diagnostic agent.\n\n"
                   "Please make sure the agent is running:\n"
                   "```bash\n"
                   "python agent.py\n"
                   "```\n"
                   "The agent should be available at http://localhost:8005"
        ).send()
        return
    except Exception as e:
        print(f"Error details: {e}")
        elements = [
            cl.Text(name="Error Details", content=f"Error: {str(e)}", display="inline")
        ]
        await cl.Message(
            content="❌ **Unexpected Error:** We encountered a problem processing your request.",
            elements=elements
        ).send()
        return