import requests
import time
import logging

logger = logging.getLogger(__name__)

def safe_api_call(url: str, params: dict, max_retries: int = 5, backoff_base: int = 2, max_backoff: int = 30) -> dict | None:
    """
    Makes a safe GET request to the Stack Exchange API with retry and backoff.

    Args:
        url (str): Full URL to call (should include base + endpoint + path)
        params (dict): Query parameters for the request
        max_retries (int): Number of times to retry on recoverable errors
        backoff_base (int): Base seconds to wait on first backoff
        max_backoff (int): Max seconds to wait between retries

    Returns:
        dict | None: Parsed JSON if successful, None on unrecoverable failure
    """
    retries = 0
    backoff = backoff_base

    while retries < max_retries:
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Log and abort early if quota is dangerously low
            quota = data.get("quota_remaining")
            if quota is not None and quota < 50:
                logger.warning(f"Quota remaining is low: {quota}")
                return None

            return data

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 429:
                logger.warning(f"Rate limited (HTTP 429). Retrying in {backoff}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                retries += 1
            elif status == 400:
                logger.error(f"Bad request: {e}")
                return None
            else:
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