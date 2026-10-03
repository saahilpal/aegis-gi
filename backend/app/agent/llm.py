import os
import json
import logging
import hashlib
import random
from typing import Optional, Dict, Any, List, Generator
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..config import settings

logger = logging.getLogger("aegis_llm")

class LLMClient:
    """
    Production Multi-Provider LLM Client.
    Supports Local Ollama models (offline, privacy-preserving) and Google Gemini (cloud),
    with live token streaming, vector embeddings, retries, and dynamic provider switching.
    """
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        self.ollama_base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.ollama_model = settings.OLLAMA_MODEL
        self.ollama_embed_model = settings.OLLAMA_EMBED_MODEL
        self.gemini_api_key = settings.GEMINI_API_KEY or os.getenv("GOOGLE_API_KEY", "")
        self.gemini_model = settings.GEMINI_MODEL
        self._genai_client = None

        # Resolve provider if "auto"
        self._resolve_provider()

    def _resolve_provider(self):
        """Auto-detect available provider or configure selected provider."""
        if self.provider in ("auto", "ollama"):
            # Probe Ollama availability
            try:
                with httpx.Client(timeout=2.0) as client:
                    resp = client.get(f"{self.ollama_base_url}/api/tags")
                    if resp.status_code == 200:
                        models_data = resp.json().get("models", [])
                        model_names = [m.get("name", "") for m in models_data]
                        logger.info(f"Ollama connected at {self.ollama_base_url}. Found models: {model_names}")
                        
                        # Verify or select available model
                        if self.ollama_model not in model_names:
                            # If configured model not found, pick first completion-capable model
                            for candidate in ["llama3.2:3b", "qwen2.5-coder:14b", "gemma4:12b"]:
                                if candidate in model_names:
                                    self.ollama_model = candidate
                                    break
                            else:
                                if model_names:
                                    self.ollama_model = model_names[0]

                        self.provider = "ollama"
                        logger.info(f"Selected Local Ollama provider with model: '{self.ollama_model}'")
                        return
            except Exception as e:
                logger.info(f"Ollama not reachable at {self.ollama_base_url}: {e}")

        # Fallback to Gemini if API key present
        if self.gemini_api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.gemini_api_key)
                self.provider = "gemini"
                logger.info(f"Gemini API client initialized with model '{self.gemini_model}'")
                return
            except Exception as e:
                logger.error(f"Failed to initialize google-genai client: {e}")

        # If neither resolved, keep configured provider but log status
        if self.provider == "ollama":
            logger.warning(f"Ollama provider configured at {self.ollama_base_url}, but service not currently responding.")
        else:
            logger.warning("No LLM provider configured with valid credentials or active local daemon.")

    @property
    def api_key(self) -> str:
        """Compatibility property for legacy checks."""
        if self.provider == "ollama":
            return "ollama-local"
        return self.gemini_api_key

    def is_available(self) -> bool:
        """Check if any LLM provider is currently operational."""
        if self.provider == "ollama":
            try:
                with httpx.Client(timeout=1.5) as client:
                    return client.get(f"{self.ollama_base_url}/api/tags").status_code == 200
            except Exception:
                return False
        elif self.provider == "gemini":
            return bool(self._genai_client)
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True
    )
    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Execute LLM generation via configured provider (Ollama or Gemini).
        """
        if self.provider == "ollama":
            try:
                payload = {
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                }
                if system_instruction:
                    payload["system"] = system_instruction

                with httpx.Client(timeout=45.0) as client:
                    resp = client.post(f"{self.ollama_base_url}/api/generate", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    ans = data.get("response", "").strip()
                    # Strip thinking tags if generated by reasoning models
                    if "</think>" in ans:
                        ans = ans.split("</think>")[-1].strip()
                    return ans
            except Exception as e:
                logger.error(f"Ollama generation failed: {e}")
                raise

        elif self.provider == "gemini" and self._genai_client:
            try:
                full_contents = []
                if system_instruction:
                    full_contents.append(f"System Instructions:\n{system_instruction}\n")
                full_contents.append(f"User Request:\n{prompt}")

                response = self._genai_client.models.generate_content(
                    model=self.gemini_model,
                    contents="\n".join(full_contents),
                )
                if response and response.text:
                    return response.text.strip()
                return ""
            except Exception as e:
                logger.error(f"Gemini API call failed: {e}")
                raise

        raise RuntimeError(
            f"No LLM provider available. Provider='{self.provider}'. Ensure Ollama is running or GEMINI_API_KEY is set."
        )

    def generate_stream(self, prompt: str, system_instruction: Optional[str] = None) -> Generator[str, None, None]:
        """
        Stream live LLM tokens from Ollama or Gemini.
        """
        if self.provider == "ollama":
            try:
                payload = {
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": True,
                }
                if system_instruction:
                    payload["system"] = system_instruction

                with httpx.stream("POST", f"{self.ollama_base_url}/api/generate", json=payload, timeout=45.0) as resp:
                    resp.raise_for_status()
                    in_thinking = False
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        try:
                            item = json.loads(line)
                            token = item.get("response", "")
                            if "<think>" in token:
                                in_thinking = True
                                continue
                            if "</think>" in token:
                                in_thinking = False
                                continue
                            if not in_thinking and token:
                                yield token
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"Ollama streaming error: {e}")
                yield f"\n[Local Inference Error: {str(e)}]"
            return

        elif self.provider == "gemini" and self._genai_client:
            try:
                full_contents = []
                if system_instruction:
                    full_contents.append(f"System Instructions:\n{system_instruction}\n")
                full_contents.append(f"User Request:\n{prompt}")

                response_stream = self._genai_client.models.generate_content_stream(
                    model=self.gemini_model,
                    contents="\n".join(full_contents),
                )
                for chunk in response_stream:
                    if chunk and chunk.text:
                        yield chunk.text
            except Exception as e:
                logger.error(f"Gemini streaming error: {e}")
                yield f"\n[Inference Error: {str(e)}]"
            return

        yield f"Configuration error: Neither Ollama nor GEMINI_API_KEY is configured."

    def embed_text(self, text: str) -> List[float]:
        """
        Generate 768-dimensional text vector embeddings.
        Uses local Ollama nomic-embed-text (if available) or Gemini text-embedding-004.
        """
        # Try Ollama embedding first if available
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.ollama_embed_model, "prompt": text}
                )
                if resp.status_code == 200:
                    emb = resp.json().get("embedding", [])
                    if len(emb) == 768:
                        return emb
        except Exception:
            pass

        # Try Gemini embedding if client is ready
        if self._genai_client:
            try:
                result = self._genai_client.models.embed_content(
                    model="text-embedding-004",
                    contents=text,
                )
                if hasattr(result, "embedding") and hasattr(result.embedding, "values"):
                    return result.embedding.values
            except Exception as e:
                logger.warning(f"Embedding generation failed via Gemini: {e}")

        # Deterministic 768-dimensional hash vector fallback
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(768)]

llm_client = LLMClient()
