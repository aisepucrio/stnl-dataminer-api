import requests
import time
import logging

logger = logging.getLogger(__name__)


def safe_api_call(
    url: str,
    params: dict,
    max_retries: int = 5,
    backoff_base: int = 2,
    max_backoff: int = 30
) -> dict | None:
    """
    Makes a safe GET request to the Stack Exchange API with retry and backoff.

    Handles:
      - HTTP 429 (rate limit)
      - API JSON "backoff" field (must wait)
      - API JSON "error_id"/"error_name" (throttle_violation, etc.)
      - network timeouts / connection errors
      - low quota early abort

    Returns:
        dict | None: Parsed JSON if successful, None on unrecoverable failure
    """
    retries = 0
    backoff = backoff_base

    while retries < max_retries:
        try:
            response = requests.get(url, params=params, timeout=10)

            # Some SE API errors are 200 with error_id, but keep HTTP checks too.
            if response.status_code == 429:
                logger.warning(f"Rate limited (HTTP 429). Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                retries += 1
                continue

            response.raise_for_status()
            data = response.json()

            # If API explicitly asks to back off, we MUST respect it.
            api_backoff = data.get("backoff")
            if api_backoff is not None:
                try:
                    wait_s = int(api_backoff)
                    logger.warning(f"API requested backoff: waiting {wait_s}s...")
                    time.sleep(wait_s)
                except Exception:
                    # If weird value, fallback to local backoff policy
                    logger.warning(f"API backoff value not parseable: {api_backoff}")

            # API-level error handling (often comes as HTTP 200)
            if "error_id" in data:
                error_name = data.get("error_name")
                error_message = data.get("error_message")

                # Retry-worthy errors
                if error_name in {"throttle_violation", "temporarily_unavailable"}:
                    logger.warning(f"API error {error_name}: {error_message}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff = min(backoff * 2, max_backoff)
                    retries += 1
                    continue

                # Non-retry (bad params / invalid token / etc.)
                logger.error(f"API error {error_name}: {error_message}")
                return None

            # Log and abort early if quota is dangerously low (your original behavior)
            quota = data.get("quota_remaining")
            if quota is not None and quota < 50:
                logger.warning(f"Quota remaining is low: {quota}")
                return None

            return data

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None

            if status == 429:
                logger.warning(f"Rate limited (HTTP 429). Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                retries += 1
                continue

            if status == 400:
                logger.error(f"Bad request (HTTP 400): {e}")
                return None

            logger.error(f"HTTP error {status}: {e}")
            return None

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            logger.warning(f"Connection issue: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
            retries += 1

        except Exception as e:
            logger.exception(f"Unexpected error during API call: {e}")
            return None

    logger.error(f"Failed to get a valid response from {url} after {max_retries} attempts.")
    return None
