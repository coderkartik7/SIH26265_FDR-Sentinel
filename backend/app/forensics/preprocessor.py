import io
from typing import List, Tuple
import numpy as np
import cv2
from PIL import Image
import pymupdf


def pdf_bytes_to_images(pdf_bytes: bytes, dpi: int = 200) -> List[Image.Image]:
    """Convert multi-page PDF bytes to a list of PIL Images"""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    images = []
    zoom = dpi / 72.0
    mat = pymupdf.Matrix(zoom, zoom)

    for page_idx in range(len(doc)):
        page = doc.load_page(page_idx)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        images.append(Image.open(io.BytesIO(img_bytes)).convert("RGB"))

    doc.close()
    return images


def estimate_skew_angle(cv_image: np.ndarray) -> float:
    """
    Estimate text skew angle in degrees using image moments and contours.
    """
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY) if len(cv_image.shape) == 3 else cv_image
    # Threshold to get dark text pixels
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # Find coordinates of all foreground pixels
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 50:
        return 0.0

    rect = cv2.minAreaRect(coords)
    angle = rect[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Filter out extreme false angles
    if abs(angle) > 15:
        return 0.0
    return angle


def deskew_image(cv_image: np.ndarray, angle: float) -> np.ndarray:
    """Rotate image to correct skew"""
    if abs(angle) < 0.2:
        return cv_image

    (h, w) = cv_image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        cv_image, M, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )
    return rotated


def denoise_and_enhance(cv_image: np.ndarray) -> np.ndarray:
    """Denoise and enhance contrast for accurate OCR"""
    # Slight bilateral filter to preserve edges while removing background scanner grain
    denoised = cv2.bilateralFilter(cv_image, d=5, sigmaColor=50, sigmaSpace=50)
    return denoised


def preprocess_document_image(pil_img: Image.Image) -> Tuple[Image.Image, float]:
    """
    Complete preprocessing pipeline:
    1. Deskew
    2. Denoise
    3. Return processed PIL image and estimated skew angle
    """
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    angle = estimate_skew_angle(cv_img)
    deskewed = deskew_image(cv_img, angle)
    cleaned = denoise_and_enhance(deskewed)

    out_pil = Image.fromarray(cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB))
    return out_pil, angle
