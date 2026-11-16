"""Read QR codes in images. Needs OpenCV (pip install opencv-python-headless); without it the check is skipped."""

from typing import Any

try:  # optional, the bot runs without it
    import cv2
    import numpy
except ImportError:  # pragma: no cover - depends on the installation
    cv2 = None  # type: ignore[assignment]
    numpy = None  # type: ignore[assignment]

MAX_SIDE = 1600


def available() -> bool:
    """True when QR codes can be read on this installation."""
    return cv2 is not None


def decode(data: bytes) -> list[str]:
    """The texts of all QR codes in an image. An image that cannot be read gives an empty list."""
    if cv2 is None or not data:
        return []
    try:
        image: Any = cv2.imdecode(numpy.frombuffer(data, dtype=numpy.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None:
            return []
        height, width = image.shape[:2]
        if max(height, width) > MAX_SIDE:
            scale = MAX_SIDE / max(height, width)
            image = cv2.resize(image, (int(width * scale), int(height * scale)))
        found, texts, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(image)
        return [t for t in texts if t] if found else []
    except Exception:  # OpenCV raises its own error types on broken images
        return []
