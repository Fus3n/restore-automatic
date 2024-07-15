import base64
from PIL import Image
import io


DEFAULT_RESTORE_PROMPT = "realistic, clean, clear, ultra-sharp, super sharp, high-res, DSLR quality, high-quality"
DEFAULT_RESTORE_NEGATIVE_PROMPT = "{ugly}, {unrealistic}, bad-quality, jpg-artifacts, unclear, smooth, weird, artifacts, {anime}, {cartoon}, {hand drawn}, {overexposed}"

def img2base64(path) -> str:
    """Converts image into base64 string"""
    with open(path, "rb") as image_file:
        image_bytes = image_file.read()

    base64_string = base64.b64encode(image_bytes).decode("utf-8")
    return base64_string

def base64_to_bytes(b64_str) -> io.BytesIO:
    """Converts base64 into io.BytesIO object"""
    image_bytes = base64.b64decode(b64_str)
    img = io.BytesIO(image_bytes)
    return img

def save_image(img, path) -> None:
    """Saves base64 string as image"""
    img = base64_to_bytes(img)
    with open(path, "wb") as f:
        f.write(img)

def base64_to_pillowimg(b64_str) -> Image.Image:
    """Converts base64 string into pillow image"""
    img = base64_to_bytes(b64_str)
    return Image.open(img)

def pillowimg_to_base64(img: Image.Image):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_byte = buffered.getvalue()
    img_base64 = base64.b64encode(img_byte)
    img_base64_string = img_base64.decode()
    return img_base64_string