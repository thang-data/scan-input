import cv2
import numpy as np
from PIL import Image


def pil_to_cv(image: Image.Image) -> np.ndarray:
    if image.mode != "RGB":
        image = image.convert("RGB")
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def cv_to_pil(image: np.ndarray) -> Image.Image:
    if len(image.shape) == 2:
        return Image.fromarray(image)
    return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))


def remove_red_stamp(img: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, (0, 70, 50), (10, 255, 255))
    mask2 = cv2.inRange(hsv, (160, 70, 50), (180, 255, 255))
    red_mask = mask1 | mask2
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    red_mask = cv2.dilate(red_mask, kernel, iterations=1)
    img[red_mask > 0] = [255, 255, 255]
    return img


def upscale(img: np.ndarray, min_width: int = 2500) -> np.ndarray:
    h, w = img.shape[:2]
    if w < min_width:
        scale = min_width / w
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return img


def to_grayscale(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def add_border(img: np.ndarray, border: int = 15) -> np.ndarray:
    value = [255, 255, 255] if len(img.shape) == 3 else 255
    return cv2.copyMakeBorder(img, border, border, border, border,
                              cv2.BORDER_CONSTANT, value=value)


def prepare_tesseract(image: Image.Image) -> Image.Image:
    """Tesseract: remove stamp, upscale, grayscale, border."""
    img = pil_to_cv(image)
    img = remove_red_stamp(img)
    img = upscale(img)
    img = to_grayscale(img)
    img = add_border(img)
    return cv_to_pil(img)


def prepare_paddle(image: Image.Image) -> Image.Image:
    """PaddleOCR: keep color, only remove stamp + border. Paddle handles the rest."""
    img = pil_to_cv(image)
    img = remove_red_stamp(img)
    img = add_border(img)
    return cv_to_pil(img)
