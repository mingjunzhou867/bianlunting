"""Small wrapper around the configured LLM provider."""
from __future__ import annotations

import json
from typing import Optional

from loguru import logger

from config.settings import settings


def _build_openai_client():
    from openai import OpenAI

    kwargs = {"api_key": settings.llm_api_key}
    base_url = settings.get_effective_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _chat_openai_compat(
    system_prompt: str,
    user_message: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tools: Optional[list[dict]] = None,
    response_format: Optional[dict] = None,
) -> str | dict:
    client = _build_openai_client()
    kwargs = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature if temperature is not None else settings.llm_temperature,
        "max_tokens": max_tokens if max_tokens is not None else settings.llm_max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
    if response_format:
        kwargs["response_format"] = response_format

    response = client.chat.completions.create(**kwargs)
    message = response.choices[0].message

    if message.tool_calls:
        return {
            "type": "tool_calls",
            "tool_calls": [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in message.tool_calls
            ],
            "content": message.content,
        }

    return message.content or ""


def _chat_anthropic(
    system_prompt: str,
    user_message: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    response_format: Optional[dict] = None,
) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.llm_api_key)
    message = client.messages.create(
        model=settings.llm_model,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
        temperature=temperature if temperature is not None else settings.llm_temperature,
        max_tokens=max_tokens if max_tokens is not None else settings.llm_max_tokens,
    )
    if not message.content:
        return ""
    return message.content[0].text


def llm_chat(
    system_prompt: str,
    user_message: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tools: Optional[list[dict]] = None,
    response_format: Optional[dict] = None,
) -> str | dict:
    """Send one chat request to the configured provider."""

    if not settings.llm_api_key:
        raise ValueError("LLM_API_KEY not configured. Please set it in config/.env.")

    logger.debug(
        "llm_chat provider={} model={} temperature={} tools={}",
        settings.llm_provider,
        settings.llm_model,
        temperature if temperature is not None else settings.llm_temperature,
        len(tools) if tools else 0,
    )

    if settings.use_openai_compat:
        return _chat_openai_compat(system_prompt, user_message, temperature, max_tokens, tools, response_format)
    return _chat_anthropic(system_prompt, user_message, temperature, max_tokens, response_format)


def ping_llm() -> bool:
    """Simple smoke test for the configured LLM backend."""

    try:
        reply = llm_chat(
            system_prompt="你是一个测试助手，只返回“连接成功”。",
            user_message="测试",
            temperature=0.0,
            max_tokens=20,
        )
        logger.info(
            "LLM 连接成功: {} / {} -> {}",
            settings.llm_provider,
            settings.llm_model,
            reply.strip(),
        )
        return True
    except Exception as exc:
        logger.error("LLM 连接失败: {}", exc)
        return False
