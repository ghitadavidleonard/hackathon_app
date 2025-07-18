import os
import asyncio
import re
import json
from pathlib import Path
from openai import AsyncOpenAI

import chainlit as cl
from uuid import uuid4
from chainlit.logger import logger

from realtime import RealtimeClient
from realtime.tools import tools

# Import your existing OBD tools for fallback text mode
import aiohttp
from agent_tools import (
    lookup_obd_code,
    extract_and_analyze_obd_codes,
    search_obd_codes_by_keyword,
    detect_obd_codes_in_message,
)

client = AsyncOpenAI()


async def setup_openai_realtime():
    """Instantiate and configure the OpenAI Realtime Client for voice mode"""
    openai_realtime = RealtimeClient(api_key=os.getenv("OPENAI_API_KEY"))
    cl.user_session.set("track_id", str(uuid4()))

    # Configure the realtime client with DTC diagnostic personality
    instructions = """
You are an expert automotive diagnostic agent specialized in analyzing DTC (Diagnostic Trouble Codes) and OBD codes.

Your expertise includes:
- Looking up and explaining DTC codes (P, B, C, U codes)
- Analyzing symptoms and connecting them to potential codes
- Providing causes and solutions for automotive problems
- Offering repair guidance and next steps

When users mention error codes, symptoms, or car problems:
1. Use the available tools to look up specific codes
2. Extract codes from their messages if they mention multiple codes
3. Search by symptoms if they describe problems without specific codes
4. Provide clear, actionable advice for repairs

Be conversational, helpful, and thorough in your responses. Ask clarifying questions when needed.
"""

    async def handle_conversation_updated(event):
        item = event.get("item")
        delta = event.get("delta")
        """Currently used to stream audio back to the client."""
        if delta:
            # Only one of the following will be populated for any given event
            if "audio" in delta:
                audio = delta["audio"]  # Int16Array, audio added
                await cl.context.emitter.send_audio_chunk(
                    cl.OutputAudioChunk(
                        mimeType="pcm16",
                        data=audio,
                        track=cl.user_session.get("track_id"),
                    )
                )
            if "transcript" in delta:
                transcript = delta["transcript"]  # string, transcript added
                logger.info(f"Transcript delta: {transcript}")
            if "arguments" in delta:
                arguments = delta["arguments"]  # string, function arguments added
                logger.info(f"Function arguments delta: {arguments}")

    async def handle_item_completed(item):
        """Used to populate the chat context with transcription once an item is completed."""
        # Log completed items for debugging
        if item:
            item_type = item.get("type", "unknown")
            logger.info(f"Item completed: type={item_type}")

    async def handle_conversation_interrupt(event):
        """Used to cancel the client previous audio playback."""
        cl.user_session.set("track_id", str(uuid4()))
        await cl.context.emitter.send_audio_interrupt()

    async def handle_error(event):
        logger.error(f"Realtime API error: {event}")
        # Send user-friendly error message
        await cl.ErrorMessage(
            content="🔧 **Voice Mode Issue**: Connection problem occurred.\n\n"
            "You can still use text mode by typing your DTC questions directly."
        ).send()

    openai_realtime.on("conversation.updated", handle_conversation_updated)
    openai_realtime.on("conversation.item.completed", handle_item_completed)
    openai_realtime.on("conversation.interrupted", handle_conversation_interrupt)
    openai_realtime.on("error", handle_error)

    # Update session with DTC diagnostic instructions
    await openai_realtime.update_session(instructions=instructions)

    cl.user_session.set("openai_realtime", openai_realtime)

    # Add tools with improved error handling
    try:
        coros = [
            openai_realtime.add_tool(tool_def, tool_handler)
            for tool_def, tool_handler in tools
        ]
        await asyncio.gather(*coros)
        logger.info(f"Successfully added {len(tools)} DTC diagnostic tools")
    except Exception as e:
        logger.error(f"Error adding tools to realtime client: {e}")
        raise


async def handle_text_message(message_content: str):
    """Handle text-based DTC analysis using your existing agent tools"""
    try:
        # Check if message contains DTC codes
        if detect_obd_codes_in_message(message_content):
            # Use the extract and analyze tool
            result = extract_and_analyze_obd_codes.invoke({"text": message_content})
            return result
        else:
            # Try to search by symptoms/keywords
            result = search_obd_codes_by_keyword.invoke({"keyword": message_content})
            if "No OBD codes found" in result:
                # Fallback to your existing API if no OBD codes found
                api_url = "http://localhost:8005/ask"
                prompt = {
                    "query": message_content,
                    "history": cl.chat_context.to_openai(),
                }

                response_text = ""
                async with aiohttp.ClientSession() as session:
                    async with session.post(api_url, json=prompt) as r:
                        if r.status == 200:
                            async for data in r.content.iter_any():
                                response_text += data.decode()
                        else:
                            response_text = "I'm here to help with automotive diagnostics. Please describe your car problem or provide any error codes you're seeing."

                return response_text
            else:
                return result
    except Exception as e:
        logger.error(f"Error in text message handling: {e}")
        return "I'm here to help with automotive diagnostics. Please describe your car problem or provide any error codes you're seeing."


@cl.on_chat_start
async def start():
    await cl.Message(
        content="🚗 **Welcome to your DTC Diagnostic Assistant!**\n\n"
        "I'm here to help you diagnose automotive problems and analyze DTC codes.\n\n"
        "**How to use me:**\n"
        "- **Voice mode**: Press `P` to talk (recommended for detailed explanations)\n"
        "- **Text mode**: Type your message (works immediately)\n"
        "- **File uploads**: Upload diagnostic reports, scanner outputs, or text files with OBD codes\n\n"
        "**I can help with:**\n"
        "- Looking up specific DTC codes (P0301, P0420, etc.)\n"
        "- Analyzing symptoms and finding related codes\n"
        "- Providing causes and solutions for car problems\n"
        "- Offering repair guidance and next steps\n"
        "- Processing uploaded diagnostic files\n\n"
        "Try saying, typing, or uploading something like:\n"
        '- "What does code P0301 mean?"\n'
        '- "My car has a rough idle"\n'
        '- "I\'m getting codes P0420 and P0171"\n'
        "- Upload a .txt file with diagnostic scanner output"
    ).send()
    await setup_openai_realtime()


@cl.on_message
async def on_message(message: cl.Message):
    openai_realtime: RealtimeClient = cl.user_session.get("openai_realtime")

    # Enhanced file processing capabilities
    file_content = ""
    files_processed = 0

    if message.elements:
        await cl.Message(content="🔍 **Processing uploaded files...**").send()

        for element in message.elements:
            if hasattr(element, "path") and element.path:
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
                        content=f"❌ **{element.name}** - No OBD codes detected. Content preview: {extracted_text[:100]}..."
                    ).send()

    # Combine message content with file analysis
    combined_query = message.content
    if file_content:
        combined_query += file_content
        await cl.Message(
            content=f"🔧 **Starting diagnostic analysis for {files_processed} file(s)...**"
        ).send()

    # Check if realtime is connected (voice mode active)
    if openai_realtime and openai_realtime.is_connected():
        # Send to realtime for voice mode
        await openai_realtime.send_user_message_content(
            [{"type": "input_text", "text": combined_query}]
        )
    else:
        # Handle as text message using existing tools
        msg = cl.Message(content="")

        try:
            # Show typing indicator
            await msg.stream_token("🔍 Analyzing your message...")

            # Process with DTC diagnostic tools
            result = await handle_text_message(combined_query)

            # Clear the typing indicator and send result
            msg.content = ""
            await msg.stream_token(result)
            await msg.send()

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            elements = [cl.Text(name="Error", content=f"Error: {e}", display="inline")]
            await cl.Message(
                content="I encountered an issue processing your request. Please try again or describe your car problem differently.",
                elements=elements,
            ).send()


@cl.on_audio_start
async def on_audio_start():
    """Start voice mode - connect to OpenAI Realtime"""
    try:
        openai_realtime: RealtimeClient = cl.user_session.get("openai_realtime")
        await openai_realtime.connect()
        logger.info("Connected to OpenAI realtime")

        # Send a welcome message for voice mode
        await cl.Message(
            content="🎙️ **Voice mode activated!** I'm ready to help with your automotive diagnostics.\n\n"
            "I have access to comprehensive DTC diagnostic tools. You can now speak your questions or describe your car problems."
        ).send()

        return True
    except Exception as e:
        logger.error(f"Failed to connect to OpenAI realtime: {e}")
        await cl.ErrorMessage(
            content=f"Failed to connect to voice mode: {e}\n\n"
            "Don't worry! You can still use text mode by typing your questions."
        ).send()
        return False


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Handle incoming audio chunks in voice mode"""
    openai_realtime: RealtimeClient = cl.user_session.get("openai_realtime")
    if openai_realtime and openai_realtime.is_connected():
        await openai_realtime.append_input_audio(chunk.data)
    else:
        logger.warning("RealtimeClient is not connected")


@cl.on_audio_end
@cl.on_chat_end
@cl.on_stop
async def on_end():
    """Clean up connections when session ends"""
    openai_realtime: RealtimeClient = cl.user_session.get("openai_realtime")
    if openai_realtime and openai_realtime.is_connected():
        await openai_realtime.disconnect()
        logger.info("Disconnected from OpenAI realtime")


def extract_text_from_file(file_path: str, file_name: str) -> str:
    """Extract text content from uploaded files."""
    try:
        file_extension = Path(file_name).suffix.lower()

        # Handle different file types
        if file_extension in [".txt", ".log", ".csv", ".dat", ".out"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                return content
        elif file_extension == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
        elif file_extension in [".xml", ".html", ".htm"]:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Basic text extraction from XML/HTML (remove tags)
                clean_text = re.sub(r"<[^>]+>", " ", content)
                return clean_text
        elif file_extension in [".pdf"]:
            # For PDF files, return a message indicating the limitation
            return f"PDF file detected: {file_name}. Please convert to text format or copy/paste the OBD codes directly."
        else:
            # Try to read as text anyway for unknown extensions
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
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
    pattern_standard = r"\b[PBCU]\d{4}\b"
    standard_codes = re.findall(pattern_standard, text.upper())
    codes.extend(standard_codes)

    # Secondary pattern: Codes with dashes or spaces (P0301, P-0301, P 0301)
    pattern_separated = r"\b[PBCU][-\s]?\d{4}\b"
    separated_codes = re.findall(pattern_separated, text.upper())
    # Clean up the separated codes
    for code in separated_codes:
        clean_code = re.sub(r"[-\s]", "", code)
        if clean_code not in codes:
            codes.append(clean_code)

    # Tertiary pattern: Look for "code" or "DTC" followed by OBD code
    pattern_keyword = r"(?:code|dtc|error)[\s:]*([PBCU][-\s]?\d{4})"
    keyword_matches = re.findall(pattern_keyword, text.upper(), re.IGNORECASE)
    for match in keyword_matches:
        clean_code = re.sub(r"[-\s]", "", match)
        if clean_code not in codes:
            codes.append(clean_code)

    # Remove duplicates and return
    return list(set(codes))
