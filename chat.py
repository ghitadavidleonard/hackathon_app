import chainlit as cl
import aiohttp

@cl.on_message
async def main(message: cl.Message):
    msg = cl.Message(content="")
    api_url = "http://localhost:8005/ask"
    prompt = {"query": message.content, "history": cl.chat_context.to_openai()}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=prompt) as r:
                async for data in r.content.iter_any():
                    await msg.stream_token(data.decode())
                await msg.send()
                
    except Exception as e:
        print(e)
        elements = [
            cl.Text(name="Description", content=f"Error: {e}", display="inline")
        ]
        await cl.Message(content="We encountered a problem", elements=elements).send()
        return