import asyncio
import json
import os
import numpy as np
from fastapi import FastAPI, WebSocket, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
import uvicorn
import logging
from prompts import PROMPTS
from openai_realtime_client import OpenAIRealtimeAudioTextClient
from starlette.websockets import WebSocketState
import wave
import datetime
import scipy.signal
from openai import OpenAI, AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Generator
from llm_processor import get_llm_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY is not set in environment variables.")
    raise EnvironmentError("OPENAI_API_KEY is not set.")

# Initialize with a default model
llm_processor = get_llm_processor("gpt-4o")  # Default processor

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_realtime_page(request: Request):
    return FileResponse("static/realtime.html")

class AudioProcessor:
    def __init__(self, target_sample_rate=24000):
        self.target_sample_rate = target_sample_rate
        self.source_sample_rate = 48000  # Most common sample rate for microphones
        
    def process_audio_chunk(self, audio_data):
        # Convert binary audio data to Int16 array
        pcm_data = np.frombuffer(audio_data, dtype=np.int16)
        
        # Convert to float32 for better precision during resampling
        float_data = pcm_data.astype(np.float32) / 32768.0
        
        # Resample from 48kHz to 24kHz
        resampled_data = scipy.signal.resample_poly(
            float_data, 
            self.target_sample_rate, 
            self.source_sample_rate
        )
        
        # Convert back to int16 while preserving amplitude
        resampled_int16 = (resampled_data * 32768.0).clip(-32768, 32767).astype(np.int16)
        return resampled_int16.tobytes()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection attempt")
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    client = OpenAIRealtimeAudioTextClient(os.getenv("OPENAI_API_KEY"))
    audio_processor = AudioProcessor()
    audio_buffer = []  # Initialize audio buffer
    recording_stopped = asyncio.Event()  # Event to signal recording stop
    
    try:
        await client.connect()
        logger.info("Successfully connected to OpenAI client")
        
        # Define handlers for OpenAI messages
        async def handle_text_delta(data):
            await websocket.send_text(json.dumps({
                "type": "text",
                "content": data.get("delta", ""),
                "isNewResponse": False
            }))
            logger.info("Handled response.text.delta")

        async def handle_response_created(data):
            await websocket.send_text(json.dumps({
                "type": "text",
                "content": "",
                "isNewResponse": True
            }))
            logger.info("Handled response.created")

        async def handle_error(data):
            error_msg = data.get("error", {}).get("message", "Unknown error")
            logger.error(f"OpenAI error: {error_msg}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": error_msg
            }))
            logger.info("Handled error message from OpenAI")

        async def handle_response_done(data):
            logger.info("Handled response.done")
            # Signal that recording has stopped and processing is complete
            recording_stopped.set()
            # You can implement logic to notify the client that the response is complete

        async def handle_generic_event(event_type, data):
            logger.info(f"Handled {event_type} with data: {json.dumps(data, ensure_ascii=False)}")

        # Replace individual handlers with generic handler
        client.register_handler("session.updated", lambda data: handle_generic_event("session.updated", data))
        client.register_handler("input_audio_buffer.cleared", lambda data: handle_generic_event("input_audio_buffer.cleared", data))
        client.register_handler("input_audio_buffer.speech_started", lambda data: handle_generic_event("input_audio_buffer.speech_started", data))
        client.register_handler("rate_limits.updated", lambda data: handle_generic_event("rate_limits.updated", data))
        client.register_handler("response.output_item.added", lambda data: handle_generic_event("response.output_item.added", data))
        client.register_handler("conversation.item.created", lambda data: handle_generic_event("conversation.item.created", data))
        client.register_handler("response.content_part.added", lambda data: handle_generic_event("response.content_part.added", data))
        client.register_handler("response.text.done", lambda data: handle_generic_event("response.text.done", data))
        client.register_handler("response.content_part.done", lambda data: handle_generic_event("response.content_part.done", data))
        client.register_handler("response.output_item.done", lambda data: handle_generic_event("response.output_item.done", data))
        client.register_handler("response.done", lambda data: handle_response_done(data))
        client.register_handler("error", lambda data: handle_error(data))
        client.register_handler("response.text.delta", lambda data: handle_text_delta(data))
        client.register_handler("response.created", lambda data: handle_response_created(data))

        # Create a queue to handle incoming audio chunks
        audio_queue = asyncio.Queue()

        async def receive_messages():
            while True:
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    logger.info("WebSocket client disconnected")
                    await audio_queue.put(None)  # Signal send_audio_messages to exit
                    break
                try:
                    data = await websocket.receive()
                    logger.info(f"Received message type: {data['type']}")

                    if "bytes" in data:
                        chunk_size = len(data["bytes"])
                        logger.info(f"Received audio chunk, size: {chunk_size} bytes")
                        
                        processed_audio = audio_processor.process_audio_chunk(data["bytes"])
                        logger.info(f"Processed audio chunk, length: {len(processed_audio)} bytes")
                        await audio_queue.put(processed_audio)
                        
                    elif "text" in data:
                        msg = json.loads(data["text"])
                        msg_type = msg.get("type")
                        logger.info(f"Received text message: {msg_type}")
                        
                        if msg_type == "start_recording":
                            logger.info("Starting new recording")
                            recording_stopped.clear()  # Reset the event
                            await client.clear_audio_buffer()
                            
                        elif msg_type == "stop_recording":
                            logger.info("Stopping recording and generating response")
                            await client.commit_audio()
                            await client.start_response(PROMPTS['paraphrase-gpt-realtime'])
                            
                            # Signal that no more audio chunks will be sent
                            recording_stopped.set()
                            
                            # Wait until all audio chunks are processed
                            await recording_stopped.wait()
                            
                            # Clear the audio buffer without saving
                            if audio_buffer:
                                audio_buffer.clear()  # Clear the buffer
                            
                except websockets.exceptions.ConnectionClosed:
                    logger.info("WebSocket connection closed by client")
                    await audio_queue.put(None)  # Signal send_audio_messages to exit
                    break
                except Exception as e:
                    logger.error(f"Error in receive_messages: {str(e)}", exc_info=True)
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "content": "Internal server error"
                    }))
                    break

        async def send_audio_messages():
            while True:
                try:
                    processed_audio = await audio_queue.get()
                    if processed_audio is None:
                        break
                    
                    # Add validation
                    if len(processed_audio) == 0:
                        logger.warning("Empty audio chunk received, skipping")
                        continue
                    
                    # Append the processed audio to the buffer
                    audio_buffer.append(processed_audio)

                    await client.send_audio(processed_audio)
                    logger.info(f"Audio chunk sent to OpenAI client, size: {len(processed_audio)} bytes")
                    
                except Exception as e:
                    logger.error(f"Error in send_audio_messages: {str(e)}", exc_info=True)
                    break

            # After processing all audio, set the event
            recording_stopped.set()

        # Start concurrent tasks for receiving and sending
        receive_task = asyncio.create_task(receive_messages())
        send_task = asyncio.create_task(send_audio_messages())

        # Wait for both tasks to complete
        await asyncio.gather(receive_task, send_task)
    
    finally:
        await client.close()
        logger.info("OpenAI client connection closed")

class ReadabilityRequest(BaseModel):
    text: str = Field(..., description="The text to improve readability for.")

class ReadabilityResponse(BaseModel):
    enhanced_text: str = Field(..., description="The text with improved readability.")

@app.post(
    "/readability",
    response_model=ReadabilityResponse,
    summary="Enhance Text Readability",
    description="Improve the readability of the provided text using GPT-4."
)
async def enhance_readability(request: ReadabilityRequest):
    prompt = PROMPTS.get('readability-enhance')
    if not prompt:
        raise HTTPException(status_code=500, detail="Readability prompt not found.")

    try:
        async def text_generator():
            # Use gpt-4o specifically for readability
            async for part in llm_processor.process_text(request.text, prompt, model="gpt-4o"):
                yield part

        return StreamingResponse(text_generator(), media_type="text/plain")

    except Exception as e:
        logger.error(f"Error enhancing readability: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing readability enhancement.")

class AskAIRequest(BaseModel):
    text: str = Field(..., description="The question to ask AI.")

class AskAIResponse(BaseModel):
    answer: str = Field(..., description="AI's answer to the question.")

@app.post(
    "/ask_ai",
    response_model=AskAIResponse,
    summary="Ask AI a Question",
    description="Ask AI to provide insights using O1-mini model."
)
def ask_ai(request: AskAIRequest):
    prompt = PROMPTS.get('ask-ai')
    if not prompt:
        raise HTTPException(status_code=500, detail="Ask AI prompt not found.")

    try:
        # Use o1-mini specifically for ask_ai
        answer = llm_processor.process_text_sync(request.text, prompt, model="o1-mini")
        return AskAIResponse(answer=answer)
    except Exception as e:
        logger.error(f"Error processing AI question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing AI question.")

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=3005)
