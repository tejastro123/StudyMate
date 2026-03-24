"""
services/ollama_service.py
==========================
Handles communication with a local Ollama instance (default: http://localhost:11434).
Provides 'unlimited free' AI by running models locally.
"""

import requests
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 60 # Local LLMs can be slow

    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    def get_local_models(self) -> List[str]:
        """Return a list of locally pulled models."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m["name"] for m in models]
        except Exception as e:
            logger.error(f"Failed to fetch Ollama models: {e}")
        return []

    def chat(self, model: str, messages: List[Dict[str, str]], system: Optional[str] = None) -> str:
        """
        Send a chat request to Ollama.
        Format: [{'role': 'user', 'content': '...'}, ...]
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        if system:
            # Inject system prompt as first message if not already present
            payload["messages"] = [{"role": "system", "content": system}] + messages

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            if response.status_code == 404:
                 raise Exception(f"Model '{model}' not found in Ollama. Please click 'Pull Model' in Settings.")
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            raise Exception(str(e))

    def generate(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        """Single-turn generation using the /api/chat endpoint for better compatibility."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return self.chat(model, messages)

    def pull_model(self, model: str):
        """
        Request Ollama to pull a model. 
        Note: This is a streaming response, but we'll simplify for now.
        """
        try:
            requests.post(f"{self.base_url}/api/pull", json={"name": model}, stream=True)
            return True
        except Exception as e:
            logger.error(f"Failed to start pull for {model}: {e}")
            return False
