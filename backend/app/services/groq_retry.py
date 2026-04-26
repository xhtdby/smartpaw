"""Shared retry helper for Groq API calls with pacing and 429 backoff."""

import asyncio
import logging
import time

import httpx

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 1.5  # seconds
MIN_REQUEST_INTERVAL = 0.75

_REQUEST_LOCK = asyncio.Lock()
_last_request_at = 0.0


async def groq_post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    json_body: dict,
) -> httpx.Response:
    """POST to Groq API with automatic retry on 429 rate limit errors."""
    global _last_request_at

    for attempt in range(MAX_RETRIES + 1):
        async with _REQUEST_LOCK:
            now = time.monotonic()
            wait_time = (_last_request_at + MIN_REQUEST_INTERVAL) - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            response = await client.post(url, headers=headers, json=json_body)
            _last_request_at = time.monotonic()

        if response.status_code == 429 and attempt < MAX_RETRIES:
            retry_after = response.headers.get("retry-after")
            if retry_after:
                try:
                    delay = max(float(retry_after), BASE_DELAY)
                except ValueError:
                    delay = BASE_DELAY * (2 ** attempt)
            else:
                delay = BASE_DELAY * (2 ** attempt)
            logger.warning(f"Groq rate limited (429), retrying in {delay:.1f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            await asyncio.sleep(delay)
            continue
        return response
    return response  # unreachable but satisfies type checker
