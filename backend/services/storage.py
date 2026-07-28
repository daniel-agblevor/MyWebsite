import io
import secrets
import warnings
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlparse

import requests
from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_INPUT_FORMATS = {"JPEG", "PNG", "WEBP", "AVIF"}
ALLOWED_FOLDERS = {"profile", "portfolio", "slideshow", "blog", "uploads"}
MAX_INPUT_BYTES = 5 * 1024 * 1024
MAX_OUTPUT_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 8_000
MAX_IMAGE_PIXELS = 40_000_000
CACHE_SECONDS = 31_536_000


class StorageError(Exception):
    pass


@dataclass(frozen=True)
class StoredImage:
    url: str
    path: str
    content_type: str = "image/webp"


def _secret_key():
    return current_app.config.get("SUPABASE_SECRET_KEY") or current_app.config.get("SUPABASE_SERVICE_ROLE_KEY", "")


def _validated_folder(folder):
    value = str(folder or "uploads").strip().lower()
    if value not in ALLOWED_FOLDERS:
        raise StorageError("Choose an approved image destination.")
    return value


def _normalize_image(data):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                image_format = (probe.format or "").upper()
                if image_format not in ALLOWED_INPUT_FORMATS:
                    raise StorageError("Only JPEG, PNG, WebP, and AVIF images are accepted.")
                if getattr(probe, "is_animated", False):
                    raise StorageError("Animated images are not accepted.")
                width, height = probe.size
                if (
                    not width
                    or not height
                    or width > MAX_IMAGE_DIMENSION
                    or height > MAX_IMAGE_DIMENSION
                    or width * height > MAX_IMAGE_PIXELS
                ):
                    raise StorageError("Image dimensions are too large.")
                probe.verify()

            with Image.open(io.BytesIO(data)) as source:
                source.seek(0)
                image = ImageOps.exif_transpose(source)
                image.load()
                if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
                    image = image.convert("RGBA")
                else:
                    image = image.convert("RGB")
                output = io.BytesIO()
                image.save(output, format="WEBP", quality=88, method=6)
    except StorageError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError, ValueError) as exc:
        raise StorageError("The selected file is not a valid image.") from exc

    normalized = output.getvalue()
    if not normalized or len(normalized) > MAX_OUTPUT_BYTES:
        raise StorageError("The processed image exceeds the 5 MB limit.")
    return normalized


def _storage_url(path):
    base = current_app.config["SUPABASE_URL"]
    bucket = current_app.config["SUPABASE_MEDIA_BUCKET"]
    return f"{base}/storage/v1/object/public/{bucket}/{quote(path, safe='/')}"


def upload_image(file_storage, folder="uploads"):
    folder = _validated_folder(folder)
    data = file_storage.read(MAX_INPUT_BYTES + 1)
    if not data or len(data) > MAX_INPUT_BYTES:
        raise StorageError("Image must be between 1 byte and 5 MB.")
    normalized = _normalize_image(data)
    path = f"{folder}/{secrets.token_urlsafe(18)}.webp"
    bucket = current_app.config["SUPABASE_MEDIA_BUCKET"]
    base = current_app.config["SUPABASE_URL"]
    response = requests.post(
        f"{base}/storage/v1/object/{bucket}/{quote(path, safe='/')}",
        headers={
            "apikey": _secret_key(),
            "Content-Type": "image/webp",
            "cache-control": str(CACHE_SECONDS),
            "x-upsert": "false",
        },
        data=normalized,
        timeout=20,
    )
    if response.status_code not in {200, 201}:
        current_app.logger.warning("Supabase image upload failed with status %s", response.status_code)
        raise StorageError("The image could not be stored.")
    return StoredImage(url=_storage_url(path), path=path)


def path_from_public_url(url):
    if not url:
        return None
    base = urlparse(current_app.config["SUPABASE_URL"])
    parsed = urlparse(str(url))
    bucket = current_app.config["SUPABASE_MEDIA_BUCKET"]
    prefix = f"/storage/v1/object/public/{bucket}/"
    if parsed.scheme != base.scheme or parsed.netloc != base.netloc or not parsed.path.startswith(prefix):
        return None
    path = unquote(parsed.path[len(prefix) :])
    if not path or ".." in path.split("/") or path.split("/", 1)[0] not in ALLOWED_FOLDERS:
        return None
    return path


def delete_image(path):
    if not path:
        return True
    folder = path.split("/", 1)[0]
    _validated_folder(folder)
    if "/" not in path or ".." in path.split("/"):
        raise StorageError("The stored image path is invalid.")
    bucket = current_app.config["SUPABASE_MEDIA_BUCKET"]
    base = current_app.config["SUPABASE_URL"]
    response = requests.delete(
        f"{base}/storage/v1/object/{bucket}/{quote(path, safe='/')}",
        headers={"apikey": _secret_key()},
        timeout=20,
    )
    if response.status_code not in {200, 204, 404}:
        current_app.logger.warning("Supabase image deletion failed with status %s", response.status_code)
        return False
    return True


def delete_image_safely(path):
    if not path:
        return
    try:
        delete_image(path)
    except (StorageError, requests.RequestException):
        current_app.logger.warning("Stored image cleanup failed", exc_info=True)