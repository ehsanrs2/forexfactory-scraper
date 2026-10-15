import json
import logging
import os
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


def load_env(folder: str):
    for name in (".env", ".env.local"):
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.removeprefix("export ").strip()
                os.environ.setdefault(key, value.strip().strip("\"'"))


class UploadError(Exception):
    pass


def upload(payload: dict, attempts: int = 3, timeout: int = 120) -> dict:
    base = os.environ.get("ECON_UPLOAD_URL", "").rstrip("/")
    secret = os.environ.get("ECON_UPLOAD_SECRET", "")
    if not base or not secret:
        raise UploadError("ECON_UPLOAD_URL and ECON_UPLOAD_SECRET must be set")
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/calendar/econ/upload",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "x-upload-secret": secret},
    )
    last = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as error:
            if 400 <= error.code < 500:
                raise UploadError(f"Upload rejected with {error.code}") from error
            last = error
            logger.warning("Upload attempt %d/%d failed: %s", attempt, attempts, error)
            if attempt < attempts:
                time.sleep(10 * attempt)
        except (urllib.error.URLError, TimeoutError) as error:
            last = error
            logger.warning("Upload attempt %d/%d failed: %s", attempt, attempts, error)
            if attempt < attempts:
                time.sleep(10 * attempt)
    raise UploadError(f"Upload failed after {attempts} attempts: {last}")
