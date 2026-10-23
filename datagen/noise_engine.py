import io
import fitz # PyMuPDF
from PIL import Image, ImageFilter, ImageEnhance


def render_pdf_to_image(pdf_path: str, page_num: int = 0, dpi: int = 150) -> Image.Image:
    """Render a PDF page to a PIL Image at specified DPI"""
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img_data = pix.tobytes("png")
    doc.close()
    return Image.open(io.BytesIO(img_data)).convert("RGB")


def apply_scanner_noise(
    pil_img: Image.Image,
    rotate_deg: float = 1.5,
    blur_radius: float = 0.6,
    contrast_factor: float = 0.85,
    brightness_factor: float = 1.05
) -> Image.Image:
    """
    Simulate real-world scanner degradation:
    1. Slight deskew angle (rotation)
    2. Subtle lens blur
    3. Scanner lamp contrast/brightness variation
    """
    # 1. Rotate with white background fill
    if abs(rotate_deg) > 0.01:
        pil_img = pil_img.rotate(rotate_deg, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=(255, 255, 255))

    # 2. Blur
    if blur_radius > 0:
        pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # 3. Contrast & Brightness
    enhancer_con = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer_con.enhance(contrast_factor)

    enhancer_bri = ImageEnhance.Brightness(pil_img)
    pil_img = enhancer_bri.enhance(brightness_factor)

    return pil_img


def convert_pdf_to_scanned_image(
    pdf_path: str,
    output_image_path: str,
    rotate_deg: float = 1.2,
    blur_radius: float = 0.5,
    jpeg_quality: int = 45
) -> str:
    """
    Renders PDF to JPEG/PNG with scanner noise and JPEG compression artifacts.
    """
    pil_img = render_pdf_to_image(pdf_path, dpi=150)
    noisy_img = apply_scanner_noise(pil_img, rotate_deg=rotate_deg, blur_radius=blur_radius)

    if output_image_path.lower().endswith((".jpg", ".jpeg")):
        noisy_img.save(output_image_path, "JPEG", quality=jpeg_quality)
    else:
        noisy_img.save(output_image_path, "PNG")

    return output_image_path
