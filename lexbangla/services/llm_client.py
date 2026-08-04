"""
Unified LLM client with support for:
  - DeepSeek API (direct)   → best for L2 legal reasoning (full R1 capability)
  - Groq + DeepSeek models  → best for L1 extraction (ultra-fast, ~400 tok/s)
  - Google Gemini           → L2 Jurisdictional Firewall option
  - Anthropic Claude        → L3 Publication Standard

DeepSeek decision:
  Use DEEPSEEK_PROVIDER=groq   for L1 extraction (speed > capability).
  Use DEEPSEEK_PROVIDER=direct for L2 analysis  (capability > speed; full R1).
  Direct DeepSeek R1 has no rate-limit lag behind Groq's hosted version
  and supports longer context windows needed for full statute analysis.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any


def _system_prompt(path: str) -> str:
    base = os.path.dirname(os.path.dirname(__file__))
    prompt_path = os.path.join(base, "prompts", path)
    with open(prompt_path, "r") as f:
        return f.read()


def _hash_prompt(system: str, user: str) -> str:
    h = hashlib.sha256(f"{system}\n\n{user}".encode()).hexdigest()
    return h


class DeepSeekDirectClient:
    """DeepSeek API (api.deepseek.com) — recommended for L2."""

    def __init__(self):
        import openai  # DeepSeek is OpenAI-compatible
        self.client = openai.OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url="https://api.deepseek.com",
        )
        # R1 for reasoning-heavy tasks; V3 (deepseek-chat) for lighter tasks
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-reasoner")

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        usage = {
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
            "model": self.model,
        }
        return response.choices[0].message.content, usage


class GroqDeepSeekClient:
    """DeepSeek via Groq inference — recommended for L1 (high throughput)."""

    def __init__(self):
        from groq import Groq
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])
        # Groq hosts distilled variants; llama-based is fastest
        self.model = os.environ.get(
            "GROQ_DEEPSEEK_MODEL", "deepseek-r1-distill-llama-70b"
        )

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        usage = {
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
            "model": self.model,
        }
        return response.choices[0].message.content, usage


class GeminiClient:
    """Google Gemini — alternative L2 backend."""

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        self.model = genai.GenerativeModel(
            os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp")
        )
        self.model_id = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp")

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        prompt = f"{system}\n\n{user}"
        response = self.model.generate_content(prompt)
        usage = {
            "input": response.usage_metadata.prompt_token_count,
            "output": response.usage_metadata.candidates_token_count,
            "model": self.model_id,
        }
        return response.text, usage


class ClaudeClient:
    """Anthropic Claude — L3 Publication Standard."""

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

    def complete(self, system: str, user: str) -> tuple[str, dict]:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        usage = {
            "input": message.usage.input_tokens,
            "output": message.usage.output_tokens,
            "model": self.model,
        }
        return message.content[0].text, usage


def get_l2_client():
    """
    Select L2 client based on L2_PROVIDER env var.
    Options: deepseek (default), groq, gemini
    """
    provider = os.environ.get("L2_PROVIDER", "deepseek").lower()
    if provider == "groq":
        return GroqDeepSeekClient()
    elif provider == "gemini":
        return GeminiClient()
    else:
        return DeepSeekDirectClient()


def get_l1_client():
    """
    L1 uses Groq by default (throughput) or direct DeepSeek if configured.
    """
    provider = os.environ.get("DEEPSEEK_PROVIDER", "groq").lower()
    if provider == "direct":
        return DeepSeekDirectClient()
    return GroqDeepSeekClient()


def parse_json_response(raw: str) -> Any:
    """Strip markdown fences if model wraps JSON in them."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    return json.loads(raw)
