"""OCR with Tesseract (ADR-003, D-033). Runs inside the parser's child process.

The binary is the one found on PATH (installed in the container image), called with an argument list,
`shell=False`, and only a file this process created in its own temporary directory. Nothing from the document
reaches the command line. Text from OCR is marked `ocr_tesseract`; evidence located in it is never `verified`
(app/capabilities/evidence.py), because it is not the document's own text.
"""

import io
import re
import shutil
import subprocess  # nosec B404
import tempfile
import unicodedata
from pathlib import Path

from PIL import Image

LANGUAGE = "jpn"
PAGE_TIMEOUT_S = 40.0
RENDER_DPI = 300
# Tesseract may put a space between Japanese characters ("請 求 書"); a space between two CJK / full-width
# characters is never meaningful in Japanese text.
_CJK = "　-ヿ㐀-鿿豈-﫿＀-￯"
_CJK_GAP = re.compile(f"(?<=[{_CJK}])[ \t]+(?=[{_CJK}])")


class OcrUnavailableError(RuntimeError):
    """The node asked for OCR but no Tesseract binary is installed (fail closed instead of empty text)."""


def tesseract_path() -> str:
    found = shutil.which("tesseract")
    if found is None:
        raise OcrUnavailableError("tesseract is not installed")
    return str(Path(found).resolve())


def ocr_image(image: Image.Image) -> str:
    """Text of one page image. Tesseract's page separator (form feed) is removed."""
    binary = tesseract_path()
    with tempfile.TemporaryDirectory(prefix="easf-ocr-") as folder:
        path = Path(folder) / "page.png"
        image.convert("L").save(path, format="PNG")
        # Absolute path of the installed binary; the only variable argument is our own temporary file.
        done = subprocess.run(  # noqa: S603  # nosec B603
            [binary, str(path), "stdout", "-l", LANGUAGE, "--psm", "6"],
            capture_output=True,
            timeout=PAGE_TIMEOUT_S,
            check=False,
            shell=False,
        )
    if done.returncode != 0:
        raise RuntimeError("tesseract failed")
    return normalize(done.stdout.decode("utf-8", errors="replace"))


def normalize(text: str) -> str:
    """NFKC (circled or full-width digits become digits) and no spaces inside Japanese words. Evidence offsets
    index this normalized text, which is what the parser returns."""
    text = unicodedata.normalize("NFKC", text.replace("\f", ""))
    return _CJK_GAP.sub("", text).rstrip()


def ocr_image_bytes(data: bytes) -> str:
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        return ocr_image(image)
