from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from threading import Thread
from typing import Any, Literal

from pydantic import BaseModel

from src.core.llm.base import LLMProvider
from src.core.llm.models import LLMRequest, LLMResponse

logger = logging.getLogger(__name__)

_INSTALL_MSG = (
    "HuggingFace provider requires: torch, transformers, accelerate, bitsandbytes. "
    "Install with: pip install pormetheus[local]"
)

# Lazy module-level imports — set to None when the packages are missing so the
# module can still be imported.  Tests patch these names directly.
try:
    import torch as torch  # noqa: I001
    from transformers import AutoModelForCausalLM as AutoModelForCausalLM
    from transformers import AutoTokenizer as AutoTokenizer
    from transformers import BitsAndBytesConfig as BitsAndBytesConfig
    from transformers import TextIteratorStreamer as TextIteratorStreamer
except ImportError:
    torch = None
    AutoModelForCausalLM = None
    AutoTokenizer = None
    BitsAndBytesConfig = None
    TextIteratorStreamer = None


class HuggingFaceConfig(BaseModel):
    """Validated configuration for the HuggingFace local provider."""

    model_id: str = "Qwen/Qwen3-4B"
    device_map: str = "auto"
    quantization: Literal["none", "4bit", "8bit"] = "4bit"
    torch_dtype: str = "float16"
    max_new_tokens: int = 2048
    trust_remote_code: bool = True


class HuggingFaceProvider(LLMProvider):
    """LLM provider for locally-loaded HuggingFace Transformers models.

    Loads the model once at construction time.  Inference calls are
    offloaded to a thread pool via ``asyncio.to_thread`` to avoid
    blocking the event loop.
    """

    def __init__(self, config: HuggingFaceConfig | None = None) -> None:
        if torch is None or AutoModelForCausalLM is None or AutoTokenizer is None:
            raise ImportError(_INSTALL_MSG)

        self._config = config or HuggingFaceConfig()

        # Build quantization config
        quant_config = self._build_quant_config()

        # Resolve torch dtype
        dtype_map: dict[str, Any] = {
            "float16": torch.float16,
            "bfloat16": torch.bfloat16,
            "float32": torch.float32,
        }
        torch_dtype = dtype_map.get(self._config.torch_dtype, torch.float16)

        # Load tokenizer
        self._tokenizer: Any = AutoTokenizer.from_pretrained(
            self._config.model_id,
            trust_remote_code=self._config.trust_remote_code,
        )

        # Load model (slow — happens once at startup)
        load_kwargs: dict[str, Any] = {
            "pretrained_model_name_or_path": self._config.model_id,
            "device_map": self._config.device_map,
            "torch_dtype": torch_dtype,
            "trust_remote_code": self._config.trust_remote_code,
        }
        if quant_config is not None:
            load_kwargs["quantization_config"] = quant_config

        logger.info("Loading model %s ...", self._config.model_id)
        self._model: Any = AutoModelForCausalLM.from_pretrained(**load_kwargs)
        logger.info("Model loaded successfully.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_quant_config(self) -> Any | None:
        if self._config.quantization == "4bit":
            return BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype="float16",
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        if self._config.quantization == "8bit":
            return BitsAndBytesConfig(load_in_8bit=True)
        return None

    def _build_messages(self, request: LLMRequest) -> list[dict[str, str]]:
        """Convert ``LLMRequest`` messages into the list-of-dicts expected by
        ``tokenizer.apply_chat_template()``."""
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for msg in request.messages:
            messages.append({"role": msg.role, "content": msg.content})
        return messages

    def _sync_generate(self, request: LLMRequest) -> LLMResponse:
        """Blocking generation — called via ``asyncio.to_thread``."""
        messages = self._build_messages(request)
        input_ids = self._tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(self._model.device)

        prompt_length: int = input_ids.shape[1]

        with torch.no_grad():
            output_ids = self._model.generate(
                input_ids,
                max_new_tokens=min(request.max_tokens, self._config.max_new_tokens),
                temperature=max(request.temperature, 1e-7),
                do_sample=request.temperature > 0,
            )

        new_token_ids = output_ids[0][prompt_length:]
        content: str = self._tokenizer.decode(new_token_ids, skip_special_tokens=True)
        completion_length = len(new_token_ids)

        return LLMResponse(
            content=content,
            model=self._config.model_id,
            usage={
                "prompt_tokens": prompt_length,
                "completion_tokens": completion_length,
                "total_tokens": prompt_length + completion_length,
            },
            finish_reason="stop",
        )

    def _threaded_generate(self, kwargs: dict[str, Any]) -> None:
        """Target for the background generation thread (streaming)."""
        with torch.no_grad():
            self._model.generate(**kwargs)

    # ------------------------------------------------------------------
    # Public LLMProvider interface
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "huggingface"

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Async generate — offloads blocking inference to thread pool."""
        return await asyncio.to_thread(self._sync_generate, request)

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        """Async streaming via ``TextIteratorStreamer`` + background thread."""
        messages = self._build_messages(request)
        input_ids = self._tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(self._model.device)

        streamer = TextIteratorStreamer(
            self._tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        generation_kwargs: dict[str, Any] = {
            "input_ids": input_ids,
            "max_new_tokens": min(request.max_tokens, self._config.max_new_tokens),
            "temperature": max(request.temperature, 1e-7),
            "do_sample": request.temperature > 0,
            "streamer": streamer,
        }

        thread = Thread(
            target=self._threaded_generate,
            args=(generation_kwargs,),
            daemon=True,
        )
        thread.start()

        for text in streamer:
            if text:
                yield text
