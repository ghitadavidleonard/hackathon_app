import chainlit as cl
import aiohttp
import re
import json
import tempfile
import os
import asyncio
import uuid
from pathlib import Path
from openai import AsyncOpenAI
from chainlit.logger import logger
from uuid import uuid4
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
# client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Import realtime when available
try:
    from realtime import RealtimeClient
    from realtime.tools import tools
    REALTIME_AVAILABLE = True
except ImportError:
    REALTIME_AVAILABLE = False
    logger.warning("OpenAI Realtime not available. Voice features will use standard Whisper.")

async def setup_openai_realtime():
    """Instantiate and configure the OpenAI Realtime Client"""
    if not REALTIME_AVAILABLE:
        logger.warning("Realtime module not available")
        return None
        
    try:
        # Initialize the realtime client
        openai_realtime = RealtimeClient(api_key=os.getenv("REALTIME_OPENAI_API_KEY"))
        # Generate a unique track ID for audio
        cl.user_session.set("track_id", str(uuid4()))
        
        # Define event handlers
        async def handle_conversation_updated(event):
            """Handle realtime conversation updates and stream audio"""
            delta = event.get("delta", {})
            if delta:
                # Process audio chunks from the API
                if "audio" in delta:
                    audio = delta["audio"]
                    await cl.context.emitter.send_audio_chunk(
                        cl.OutputAudioChunk(
                            mimeType="pcm16",
                            data=audio,
                            track=cl.user_session.get("track_id"),
                        )
                    )
                # Process transcript updates if available
                if "transcript" in delta:
                    transcript = delta["transcript"]
                    logger.info(f"Transcript update: {transcript}")
                # Process function arguments
                if "arguments" in delta:
                    arguments = delta["arguments"]
                    logger.info(f"Function arguments: {arguments}")
        
        async def handle_item_completed(item):
            """Process completed conversation items"""
            logger.info(f"Item completed: {item.get('type')}")
            # Could populate chat context with transcriptions here
        
        async def handle_conversation_interrupt(event):
            """Handle interruptions and reset audio"""
            logger.info("Conversation interrupted")
            cl.user_session.set("track_id", str(uuid4()))
            await cl.context.emitter.send_audio_interrupt()
        
        async def handle_error(event):
            """Process error events"""
            logger.error(f"Realtime error: {event}")
        
        # Register all event handlers
        openai_realtime.on("conversation.updated", handle_conversation_updated)
        openai_realtime.on("conversation.item.completed", handle_item_completed)
        openai_realtime.on("conversation.interrupted", handle_conversation_interrupt)
        openai_realtime.on("error", handle_error)
        
        # Store the client in the user session
        cl.user_session.set("openai_realtime", openai_realtime)
        
        # Add tools if available
        if hasattr(tools, "__iter__"):
            try:
                coros = [
                    openai_realtime.add_tool(tool_def, tool_handler)
                    for tool_def, tool_handler in tools
                ]
                await asyncio.gather(*coros)
                logger.info(f"Registered {len(tools)} tools with realtime client")
            except Exception as e:
                logger.error(f"Error registering tools: {e}")
        
        return openai_realtime
        
    except Exception as e:
        logger.error(f"Failed to setup realtime client: {e}")
        return None

@cl.on_chat_start
async def start():
    """Initialize the chat session with file upload capabilities."""
    # Initialize session variables
    cl.user_session.set("history", [])
    cl.user_session.set("current_turn_id", str(uuid.uuid4()))
    cl.user_session.set("audio_track_id", str(uuid.uuid4()))
    cl.user_session.set("is_listening", False)
    
    # Initialize realtime client but don't connect yet (will connect when audio starts)
    await setup_openai_realtime()
    cl.user_session.set("using_realtime", True)
    
    # Apply noise reduction settings for standard Whisper fallback if needed
    noise_reduction_settings = {
        "noise_reduction_level": "high",
        "ambient_noise_suppression": True,
        "voice_focus": True
    }
    cl.user_session.set("noise_reduction_settings", noise_reduction_settings)
    
    await cl.Message(
        content="🔧 **Welcome to OBD Diagnostic Assistant!**\n\n"
                "I can help you with:\n"
                "• **OBD diagnostic codes** - Tell me your error codes (like P0301, P0420)\n"
                "• **Car symptoms** - Describe what's wrong with your car\n"
                "• **File uploads** - Upload diagnostic reports, scanner outputs, or text files containing OBD codes\n"
                "• **Voice input** - Click the microphone icon to speak your question\n\n"
                "Just type, speak your question, or upload a file containing diagnostic information!"
    ).send()

@cl.on_audio_start
async def on_audio_start():
    """Handle the start of audio input with enhanced noise handling."""
    # First ensure any previous audio session is properly terminated
    await cl.context.emitter.send_audio_interrupt()
    
    # Connect to realtime API when audio starts
    try:
        openai_realtime = cl.user_session.get("openai_realtime")
        if openai_realtime:
            await openai_realtime.connect()
            logger.info("Connected to OpenAI realtime")
            # Generate a new track ID for this audio session
            cl.user_session.set("track_id", str(uuid4()))
            # Mark as listening
            cl.user_session.set("is_listening", True)
            return True
        else:
            # Try to set up realtime as fallback
            realtime_client = await setup_openai_realtime()
            if realtime_client:
                await realtime_client.connect()
                cl.user_session.set("using_realtime", True)
                cl.user_session.set("openai_realtime", realtime_client)
                logger.info("OpenAI Realtime initialized successfully")
                # Generate a new track ID
                cl.user_session.set("track_id", str(uuid4()))
                # Mark as listening
                cl.user_session.set("is_listening", True)
                return True
    except Exception as e:
        logger.error(f"Failed to connect to OpenAI realtime: {e}")
        # Fall back to standard audio handling
        cl.user_session.set("using_realtime", False)
        await cl.Message(content=f"⚠️ Voice mode using realtime failed to initialize. Using standard transcription instead: {str(e)}").send()
    
    # Standard audio handling (Whisper) as fallback
    cl.user_session.set("audio_track_id", str(uuid.uuid4()))
    cl.user_session.set("is_listening", True)
    
    # Apply enhanced noise reduction settings for standard Whisper
    noise_reduction_settings = {
        "noise_reduction_level": "high",      # Maximum noise reduction
        "ambient_noise_suppression": True,    # Filter out constant background sounds
        "voice_focus": True,                  # Focus on human voice frequencies
        "silence_threshold": 400,             # Higher threshold ignores quieter sounds
        "normalize_audio": True               # Normalize volume levels
    }
    cl.user_session.set("noise_reduction_settings", noise_reduction_settings)
    logger.info("Enhanced noise reduction settings applied")
    
    return True

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Process incoming audio chunks."""
    # Mark that we're actively receiving audio
    cl.user_session.set("is_listening", True)
    
    # First, handle noise filtering
    try:
        # Calculate amplitude from audio chunk (simplified version)
        import numpy as np
        audio_data = np.frombuffer(chunk.chunk, dtype=np.int16)
        amplitude = np.abs(audio_data).mean()
        
        # Store the amplitude for noise threshold analysis
        amplitudes = cl.user_session.get("audio_amplitudes", [])
        amplitudes.append(amplitude)
        cl.user_session.set("audio_amplitudes", amplitudes[-10:])  # Keep last 10 samples
        
        # Apply dynamic noise threshold
        noise_threshold = cl.user_session.get("noise_threshold", 500)
        if len(amplitudes) >= 5:
            # Dynamically adjust threshold based on recent audio
            median_amplitude = np.median(amplitudes)
            if amplitude < noise_threshold and amplitude < median_amplitude * 0.7:
                # This is likely background noise, skip processing
                logger.debug(f"Filtering out background noise (amplitude: {amplitude})")
                return
    except Exception as e:
        logger.debug(f"Error in amplitude analysis: {e}")
    
    # Process the chunk with realtime client if available
    openai_realtime = cl.user_session.get("openai_realtime")
    if openai_realtime and openai_realtime.is_connected():
        try:
            await openai_realtime.append_input_audio(chunk.data)
        except Exception as e:
            logger.error(f"Error processing audio chunk with realtime: {e}")
            # Fall back to standard Whisper if realtime fails during processing
            cl.user_session.set("using_realtime", False)
            logger.info("Falling back to standard Whisper after realtime error")
    
    # For standard Whisper, Chainlit's built-in audio processing applies the VAD settings
    # The enhanced settings in config.toml and our amplitude filtering help reduce background noise

@cl.on_audio_end
async def on_audio_end():
    """Handle the end of audio input with enhanced noise handling."""
    # Mark that we're no longer listening
    cl.user_session.set("is_listening", False)
    
    # Check for realtime audio processing
    openai_realtime = cl.user_session.get("openai_realtime")
    if openai_realtime and openai_realtime.is_connected():
        try:
            # Create the response using the collected audio
            await openai_realtime.create_response()
            # Don't disconnect - keep the connection open for potential further conversation
        except Exception as e:
            logger.error(f"Error creating response from realtime: {e}")
            # If there's an error, disconnect and clean up
            await openai_realtime.disconnect()
    
    # Standard audio handling - stop audio input
    await cl.context.emitter.send_audio_interrupt()
    
    # Reset audio state while keeping statistics for noise handling
    cl.user_session.set("audio_track_id", str(uuid.uuid4()))
    
    # Process noise statistics for future noise threshold adjustment
    amplitudes = cl.user_session.get("audio_amplitudes", [])
    if len(amplitudes) > 5:
        import numpy as np
        try:
            median_amplitude = np.median(amplitudes)
            noise_floor = np.percentile(amplitudes, 10)
            
            # Adjust noise threshold for next audio session
            optimal_threshold = noise_floor * 1.5
            cl.user_session.set("noise_threshold", optimal_threshold)
            logger.debug(f"Audio session ended. Median amplitude: {median_amplitude}, Noise floor: {noise_floor}")
        except Exception as e:
            logger.debug(f"Error calculating audio statistics: {e}")
    
    # Clear stored amplitude data for next session
    cl.user_session.set("audio_amplitudes", [])

@cl.on_chat_end
@cl.on_stop
async def on_chat_end():
    """Clean up resources when chat ends or is stopped."""
    # Stop any active audio listening
    if cl.user_session.get("is_listening"):
        # Make sure to stop any audio that might be active
        await cl.context.emitter.send_audio_interrupt()
        cl.user_session.set("is_listening", False)
        
        # Clean up realtime connection if active
        if cl.user_session.get("using_realtime"):
            try:
                openai_realtime = cl.user_session.get("openai_realtime")
                if openai_realtime:
                    await openai_realtime.disconnect()
                    logger.info("Disconnected from OpenAI realtime service")
            except Exception as e:
                logger.debug(f"Error disconnecting from realtime: {e}")
    
    # Reset all session audio data
    cl.user_session.set("audio_track_id", str(uuid.uuid4()))
    cl.user_session.set("audio_amplitudes", [])
    cl.user_session.set("noise_threshold", 500)  # Reset to default

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
    # Generate a unique ID for this conversation turn
    turn_id = str(uuid.uuid4())
    cl.user_session.set("current_turn_id", turn_id)
    
    # Force stop any ongoing audio recording
    if cl.user_session.get("is_listening"):
        # Clean up audio resources properly
        await cl.context.emitter.send_audio_interrupt()
        cl.user_session.set("is_listening", False)
        
        # Clean up realtime connection if active
        if cl.user_session.get("using_realtime"):
            try:
                openai_realtime = cl.user_session.get("openai_realtime")
                if openai_realtime:
                    await openai_realtime.disconnect()
            except Exception as e:
                logger.debug(f"Error disconnecting from realtime during message: {e}")
    
    # Check if we're using realtime and it's connected
    openai_realtime = cl.user_session.get("openai_realtime")
    if openai_realtime and openai_realtime.is_connected() and not (hasattr(message, "audio") and message.audio):
        # Direct message handling through realtime
        await openai_realtime.send_user_message_content([{"type": "input_text", "text": message.content}])
        return
    
    # Create a message object that will be updated in real-time
    msg = cl.Message(content="")
    await msg.send()
    
    # Check if this is a voice message with improved feedback
    if hasattr(message, "audio") and message.audio:
        # Check for empty or very short transcriptions (likely noise)
        if not message.content or len(message.content.strip()) < 3:
            await msg.update(content="⚠️ I couldn't understand what you said. It might have been too quiet or contained only background noise. Could you please try speaking again?")
            return
        
        # Check for obvious non-speech content (like "hmm" or background noise words)
        noise_patterns = ["hmm", "umm", "ahh", "uh", "[inaudible]", "[background noise]"]
        if any(pattern in message.content.lower() for pattern in noise_patterns):
            await msg.update(content="⚠️ I heard some sounds but couldn't make out clear speech. Could you please try speaking again?")
            return
            
        # Show transcription feedback by updating the existing message
        msg.content = f"🎙️ I heard: \"{message.content}\"\n\n💭 Processing your request..."
        await msg.update()
    
    api_url = "http://localhost:8005/ask"
    
    # Check if there are file attachments
    file_content = ""
    files_processed = 0
    file_feedback = None
    
    # Show thinking indicator initially
    if not (hasattr(message, "audio") and message.audio):
        msg.content = "💭 Thinking..."
        await msg.update()
    
    if message.elements:
        # Update the existing message for file processing status
        if hasattr(message, "audio") and message.audio:
            msg.content += "\n\n🔍 **Processing uploaded files...**"
        else:
            msg.content = "🔍 **Processing uploaded files...**"
        await msg.update()
        
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
                    
                    # Update the existing message instead of creating new ones
                    file_status = f"\n✅ **{element.name}** - Found {len(found_codes)} OBD codes: {', '.join(found_codes)}"
                    msg.content += file_status
                    await msg.update()
                else:
                    file_content += f"\n\n📁 **File Analysis - {element.name}:**\n"
                    file_content += f"❌ No OBD codes found in this file.\n"
                    file_content += f"📄 File content excerpt:\n```\n{extracted_text[:500]}{'...' if len(extracted_text) > 500 else ''}\n```\n"
                    
                    # Update the existing message instead of creating new ones
                    file_status = f"\n❌ **{element.name}** - No OBD codes detected"
                    msg.content += file_status
                    await msg.update()
    
    # Combine message content with file analysis
    combined_query = message.content
    if file_content:
        combined_query += file_content
        # Update the existing message instead of creating a new one
        msg.content += f"\n\n🔧 **Starting diagnostic analysis for {files_processed} file(s)...**"
        await msg.update()
    
    # Clear the message content to prepare for response streaming
    msg.content = ""
    
    prompt = {"query": combined_query, "history": cl.chat_context.to_openai()}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=prompt) as r:
                if r.status == 200:
                    response_content = ""
                    async for data in r.content.iter_any():
                        if data:
                            decoded_data = data.decode('utf-8', errors='ignore')
                            response_content += decoded_data
                            await msg.stream_token(decoded_data)
                    
                    # Check if this was a voice message - enable TTS for voice responses
                    is_voice_input = hasattr(message, "audio") and message.audio
                    if is_voice_input:
                        # For voice inputs, create a new message with TTS enabled
                        audio_response = cl.Message(
                            content=response_content,
                            author="Assistant"
                        )
                        await audio_response.send()
                        
                        # Update the original message to indicate audio was generated
                        await msg.update()
                    else:
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