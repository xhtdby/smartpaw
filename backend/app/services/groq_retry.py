"""Shared retry helper for Groq API calls with 429 backoff."""

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 1.5  # seconds


async def groq_post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    json_body: dict,
) -> httpx.Response:
    """POST to Groq API with automatic retry on 429 rate limit errors."""
    for attempt in range(MAX_RETRIES + 1):
        response = await client.post(url, headers=headers, json=json_body)
        if response.status_code == 429 and attempt < MAX_RETRIES:
            delay = BASE_DELAY * (2 ** attempt)
            logger.warning(f"Groq rate limited (429), retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            await asyncio.sleep(delay)
            continue
        return response
    return response  # unreachable but satisfies type checker
