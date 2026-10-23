from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from time import monotonic
from typing import Any, Protocol

from .spec import FormalSpecification


@dataclass(frozen=True)
class GenerationRecord:
    provider: str
    model: str
    generation_id: str
    generated_at: str
    specification: FormalSpecification
    prompt_sha256: str = ""
    raw_output: str = ""
    raw_response: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None
    requested_model: str = ""
    requested_service_tier: str = ""
    response_service_tier: str = ""
    response_id: str = ""
    attempts: int = 1
    retry_log: tuple[str, ...] = ()


class GenerationFailure(RuntimeError):
    """A failed real generation with safe, serializable provenance for frozen evidence."""

    def __init__(self, message: str, record: dict[str, Any]) -> None:
        super().__init__(message)
        self.record = record


class Provider(Protocol):
    def generate(self, problem_id: str, problem_text: str) -> GenerationRecord: ...


class FixtureProvider:
    def __init__(self, name: str, fixtures: dict[str, dict[str, Any]]) -> None:
        self.name = name
        self.fixtures = fixtures

    def generate(self, problem_id: str, problem_text: str) -> GenerationRecord:
        del problem_text
        raw = json.loads(json.dumps(self.fixtures[problem_id]))
        raw["generation_id"] = f"{self.name}-{problem_id}"
        specification = FormalSpecification.from_dict(raw)
        return GenerationRecord(
            provider=self.name, model="deterministic-fixture-v1",
            generation_id=specification.generation_id,
            generated_at="1970-01-01T00:00:00+00:00", specification=specification,
        )


class OpenAICompatibleProvider:
    """Optional JSON-only provider. It never receives Gold, labels, or another path's output."""

    def __init__(
        self, *, model: str, system_prompt: str,
        api_url: str = "https://api.openai.com/v1/chat/completions",
        max_retries: int = 0,
        max_completion_tokens: int | None = None,
        service_tier: str | None = None,
    ) -> None:
        if max_retries not in {0, 1}:
            raise ValueError("max_retries must be 0 or 1")
        if max_completion_tokens is not None and max_completion_tokens < 1:
            raise ValueError("max_completion_tokens must be positive")
        if service_tier not in {None, "default"}:
            raise ValueError("only service_tier=default is allowed by the frozen cost model")
        self.model, self.system_prompt, self.api_url = model, system_prompt, api_url
        self.max_retries, self.max_completion_tokens = max_retries, max_completion_tokens
        self.service_tier = service_tier

    def generate(self, problem_id: str, problem_text: str) -> GenerationRecord:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured; real LLM experiment NOT RUN")
        generation_id = str(uuid.uuid4())
        prompt = f"problem_id={problem_id}\nproblem={problem_text}"
        payload_object: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        if self.max_completion_tokens is not None:
            payload_object["max_completion_tokens"] = self.max_completion_tokens
        if self.service_tier is not None:
            payload_object["service_tier"] = self.service_tier
        payload = json.dumps(payload_object).encode()
        request = urllib.request.Request(
            self.api_url, data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        started = monotonic()
        attempts = 0
        retry_log: list[str] = []
        while True:
            attempts += 1
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    body = json.load(response)
                break
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                if attempts > self.max_retries or exc.code not in {429, 500, 502, 503, 504}:
                    raise GenerationFailure(
                        f"HTTP {exc.code} after {attempts} attempt(s)",
                        {
                            "requested_model": self.model,
                            "requested_service_tier": self.service_tier or "auto",
                            "attempts": attempts,
                            "retry_log": retry_log,
                            "raw_response": error_body,
                            "error_type": "HTTPError",
                            "error_message": f"HTTP {exc.code}: {exc.reason}",
                            "latency_ms": round((monotonic() - started) * 1000),
                        },
                    ) from exc
                retry_log.append(f"attempt {attempts}: HTTP {exc.code}")
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempts > self.max_retries:
                    raise GenerationFailure(
                        f"transport failure after {attempts} attempt(s)",
                        {
                            "requested_model": self.model,
                            "requested_service_tier": self.service_tier or "auto",
                            "attempts": attempts,
                            "retry_log": retry_log,
                            "raw_response": "",
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                            "latency_ms": round((monotonic() - started) * 1000),
                        },
                    ) from exc
                retry_log.append(f"attempt {attempts}: {type(exc).__name__}")
        raw_response = json.dumps(body, sort_keys=True, separators=(",", ":"))
        body_fields = body if isinstance(body, dict) else {}
        usage = body_fields.get("usage") or {}
        try:
            raw_output = body["choices"][0]["message"]["content"]
            raw = json.loads(raw_output)
            raw["generation_id"] = generation_id
            specification = FormalSpecification.from_dict(raw)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError) as exc:
            raise GenerationFailure(
                f"response parse/validation failure after {attempts} attempt(s)",
                {
                    "requested_model": self.model,
                    "requested_service_tier": self.service_tier or "auto",
                    "response_model": str(body_fields.get("model", "")),
                    "response_service_tier": str(body_fields.get("service_tier", "")),
                    "response_id": str(body_fields.get("id", "")),
                    "attempts": attempts,
                    "retry_log": retry_log,
                    "raw_response": raw_response,
                    "raw_output": (
                        raw_output if "raw_output" in locals() and isinstance(raw_output, str) else ""
                    ),
                    "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "latency_ms": round((monotonic() - started) * 1000),
                },
            ) from exc
        return GenerationRecord(
            provider="openai-compatible", model=body_fields.get("model", self.model), generation_id=generation_id,
            generated_at=datetime.now(timezone.utc).isoformat(), specification=specification,
            prompt_sha256=sha256((self.system_prompt + "\n" + prompt).encode()).hexdigest(),
            raw_output=raw_output,
            raw_response=raw_response,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=round((monotonic() - started) * 1000),
            requested_model=self.model,
            requested_service_tier=self.service_tier or "auto",
            response_service_tier=str(body_fields.get("service_tier", "")),
            response_id=str(body_fields.get("id", "")),
            attempts=attempts,
            retry_log=tuple(retry_log),
        )


def generate_isolated(
    problem_id: str, problem_text: str, primary: Provider, secondary: Provider
) -> tuple[GenerationRecord, GenerationRecord]:
    """Two fresh calls receive only public problem fields; neither call receives Gold or peer state."""
    return primary.generate(problem_id, problem_text), secondary.generate(problem_id, problem_text)
