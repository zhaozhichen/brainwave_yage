import os
from abc import ABC, abstractmethod
import google.generativeai as genai
from openai import AsyncOpenAI
from typing import AsyncGenerator, Optional
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class LLMProcessor(ABC):
    @abstractmethod
    async def process_text(self, text: str, prompt: str) -> AsyncGenerator[str, None]:
        pass

class GeminiProcessor(LLMProcessor):
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY is not set")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')

    async def process_text(self, text: str, prompt: str) -> AsyncGenerator[str, None]:
        all_prompt = f"{prompt}\n\nBelow is the text to be processed:\n\n{text}\n\n"
        logger.info(f"Prompt: {all_prompt}")
        response = await self.model.generate_content_async(
            all_prompt,
            stream=True
        )
        async for chunk in response:
            if chunk.text:
                yield chunk.text

class GPTProcessor(LLMProcessor):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set")
        self.client = AsyncOpenAI(api_key=api_key)

    async def process_text(self, text: str, prompt: str) -> AsyncGenerator[str, None]:
        all_prompt = f"{prompt}\n\nBelow is the text to be processed:\n\n{text}\n\n"
        logger.info(f"Prompt: {all_prompt}")
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": all_prompt}
            ],
            stream=True
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

def get_llm_processor(processor_type: str = "gemini") -> LLMProcessor:
    processors = {
        "gemini": GeminiProcessor,
        "gpt": GPTProcessor
    }
    processor_class = processors.get(processor_type.lower())
    if not processor_class:
        raise ValueError(f"Unsupported processor type: {processor_type}")
    return processor_class()
