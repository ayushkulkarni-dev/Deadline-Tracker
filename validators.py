import io
from PIL import Image

MAX_MB = 5
MAX_PIXELS = 25_000_000
FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg"}


def validate_image(file):
    """Returns (ok, mime_type, problem). Checks real content, not just the extension."""
    data = file.getvalue()
    if not data:
        return False, None, "file is empty"
    if len(data) > MAX_MB * 1024 * 1024:
        return False, None, f"larger than {MAX_MB} MB"
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            width, height = img.size
            img.verify()
    except Exception:
        return False, None, "not a valid image"
    if fmt not in FORMATS:
        return False, None, f"unsupported format ({fmt}), use PNG or JPG"
    if width * height > MAX_PIXELS:
        return False, None, "image resolution is too large"
    return True, FORMATS[fmt], ""