# Advanced conversion endpoints for image, PDF, office, security, and utilities
import tempfile
from pathlib import Path
from typing import Optional
import json
import csv
import hashlib
import base64
import xml.etree.ElementTree as ET

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from pypdf import PdfReader
from cryptography.fernet import Fernet
import subprocess
import shutil

router = APIRouter()


def _save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename).suffix or ""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with open(path, "wb") as f:
        f.write(upload.file.read())
    return Path(path)


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


# ===== ADVANCED IMAGE PROCESSING =====
@router.post("/convert/image/psd-to-jpg")
def psd_to_jpg(file: UploadFile = File(...), quality: int = Form(85)):
    """Convert PSD to JPG. Requires Pillow with PSD support."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.jpg'))
    try:
        img = Image.open(src)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        img.save(out, quality=quality)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/image/color-mode")
def image_color_mode(file: UploadFile = File(...), target_mode: str = Form("RGB")):
    """Convert color mode: RGB, CMYK, RGBA, L (grayscale), etc."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.png'))
    try:
        img = Image.open(src)
        target_mode = target_mode.upper()
        if target_mode == "CMYK":
            if img.mode != "CMYK":
                img = img.convert("RGB").convert("CMYK")
        else:
            img = img.convert(target_mode)
        img.save(out)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/image/effects")
def image_effects(file: UploadFile = File(...), effect: str = Form("sharpen")):
    """Apply effects: sharpen, blur, grayscale, sepia, negative, edge_enhance."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.png'))
    try:
        img = Image.open(src).convert("RGBA")
        if effect == "sharpen":
            img = img.filter(ImageFilter.SHARPEN)
        elif effect == "blur":
            img = img.filter(ImageFilter.GaussianBlur(radius=2))
        elif effect == "grayscale":
            img = img.convert("L").convert("RGBA")
        elif effect == "sepia":
            img_rgb = img.convert("RGB")
            data = img_rgb.getdata()
            new_data = []
            for r, g, b in data:
                tr = int(r * 0.393 + g * 0.769 + b * 0.189)
                tg = int(r * 0.349 + g * 0.686 + b * 0.168)
                tb = int(r * 0.272 + g * 0.534 + b * 0.131)
                new_data.append((min(255, tr), min(255, tg), min(255, tb)))
            img_rgb.putdata(new_data)
            img = img_rgb.convert("RGBA")
        elif effect == "negative":
            img = ImageOps.invert(img.convert("RGB")).convert("RGBA")
        elif effect == "edge_enhance":
            img = img.filter(ImageFilter.EDGE_ENHANCE)
        img.save(out)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/image/add-watermark")
def image_add_watermark(image: UploadFile = File(...), text: str = Form("Watermark")):
    """Add text watermark to image."""
    src = _save_upload(image)
    out = Path(tempfile.mktemp(suffix='.png'))
    try:
        img = Image.open(src).convert("RGBA")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        bbox = draw.textbbox((0, 0), text, font=font)
        w, h = img.size
        x = w - (bbox[2] - bbox[0]) - 10
        y = h - (bbox[3] - bbox[1]) - 10
        draw.text((x, y), text, fill=(255, 255, 255, 128), font=font)
        img.save(out)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ===== PDF OCR & ENTERPRISE =====
@router.post("/convert/pdf/ocr")
def pdf_ocr(file: UploadFile = File(...)):
    """Extract text from PDF via OCR. Requires pytesseract + Tesseract."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.txt'))
    try:
        try:
            import pytesseract
            from pdf2image import convert_from_path
            pages = convert_from_path(str(src))
            text = []
            for page in pages:
                text.append(pytesseract.image_to_string(page))
            with open(out, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text))
            return FileResponse(str(out), filename=out.name, media_type='text/plain')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/pdf/to-json")
def pdf_to_json(file: UploadFile = File(...)):
    """Extract PDF content to JSON."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.json'))
    try:
        reader = PdfReader(str(src))
        data = {"pages": [], "total_pages": len(reader.pages)}
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            data["pages"].append({"page": i + 1, "text": text})
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return FileResponse(str(out), filename=out.name, media_type='application/json')
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/json/to-pdf")
def json_to_pdf(file: UploadFile = File(...)):
    """Convert JSON data to PDF."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.pdf'))
    try:
        data = json.load(open(src))
        text = json.dumps(data, indent=2)
        lines = text.splitlines()
        img = Image.new("RGB", (1200, 72 * max(1, len(lines))), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        for i, line in enumerate(lines):
            draw.text((10, i * 18), line, fill=(0, 0, 0), font=font)
        img.save(out, "PDF")
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ===== OFFICE & DATA =====
@router.post("/convert/data/csv-to-json")
def csv_to_json(file: UploadFile = File(...)):
    """Convert CSV to JSON."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.json'))
    try:
        rows = []
        with open(src, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(rows, f, indent=2)
        return FileResponse(str(out), filename=out.name, media_type='application/json')
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/data/json-to-csv")
def json_to_csv(file: UploadFile = File(...)):
    """Convert JSON to CSV."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.csv'))
    try:
        data = json.load(open(src))
        if isinstance(data, list) and len(data) > 0:
            keys = data[0].keys()
            with open(out, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
            return FileResponse(str(out), filename=out.name)
        else:
            raise HTTPException(status_code=400, detail="Invalid JSON structure for CSV conversion")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/data/xml-to-json")
def xml_to_json(file: UploadFile = File(...)):
    """Convert XML to JSON."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.json'))
    try:
        tree = ET.parse(src)
        root = tree.getroot()
        def elem_to_dict(elem):
            d = {elem.tag: {} if elem.attrib else None}
            children = list(elem)
            if children:
                dd = {}
                for child in children:
                    cd = elem_to_dict(child)
                    for k, v in cd.items():
                        if k in dd:
                            if not isinstance(dd[k], list):
                                dd[k] = [dd[k]]
                            dd[k].append(v)
                        else:
                            dd[k] = v
                d[elem.tag] = dd
            elif elem.text:
                d[elem.tag] = elem.text
            return d
        data = elem_to_dict(root)
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return FileResponse(str(out), filename=out.name, media_type='application/json')
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ===== SECURITY & UTILITIES =====
@router.post("/convert/file/hash")
def file_hash(file: UploadFile = File(...)):
    """Compute file hash (SHA256)."""
    src = _save_upload(file)
    try:
        sha = hashlib.sha256()
        with open(src, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha.update(chunk)
        return {"sha256": sha.hexdigest()}
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/file/exif-cleaner")
def exif_cleaner(file: UploadFile = File(...)):
    """Remove EXIF metadata from images."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=Path(src).suffix))
    try:
        try:
            img = Image.open(src)
            img.info.pop('exif', None)
            img.save(out)
            return FileResponse(str(out), filename=out.name)
        except Exception:
            import shutil
            shutil.copy(src, out)
            return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/file/encrypt")
def file_encrypt(file: UploadFile = File(...), password: str = Form(...)):
    """Encrypt file using Fernet with password-derived key."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=Path(src).suffix + '.enc'))
    try:
        key = base64.urlsafe_b64encode(hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt', 100000)[:32])
        f = Fernet(key)
        with open(src, 'rb') as file_obj:
            data = file_obj.read()
        encrypted = f.encrypt(data)
        with open(out, 'wb') as file_obj:
            file_obj.write(encrypted)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/file/decrypt")
def file_decrypt(file: UploadFile = File(...), password: str = Form(...)):
    """Decrypt file using Fernet with password-derived key."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.bin'))
    try:
        key = base64.urlsafe_b64encode(hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt', 100000)[:32])
        f = Fernet(key)
        with open(src, 'rb') as file_obj:
            encrypted = file_obj.read()
        decrypted = f.decrypt(encrypted)
        with open(out, 'wb') as file_obj:
            file_obj.write(decrypted)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decryption failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/batch/rename")
def batch_rename(files: list[UploadFile] = File(...), pattern: str = Form("file_{i}")):
    """Rename multiple files in batch."""
    import zipfile
    tmpdir = Path(tempfile.mkdtemp())
    try:
        for i, f in enumerate(files):
            src = _save_upload(f)
            suffix = Path(src).suffix
            renamed = tmpdir / f"{pattern.replace('{i}', str(i + 1))}{suffix}"
            src.rename(renamed)
        out_zip = Path(tempfile.mktemp(suffix='.zip'))
        with zipfile.ZipFile(out_zip, 'w') as z:
            for f in tmpdir.glob('*'):
                z.write(f, f.name)
        return FileResponse(str(out_zip), filename=out_zip.name)
    finally:
        try:
            for f in tmpdir.glob('*'):
                f.unlink()
            tmpdir.rmdir()
        except Exception:
            pass


@router.post("/convert/thumbnail/generate")
def thumbnail_generate(file: UploadFile = File(...), size: int = Form(200)):
    """Generate thumbnail for image or video."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.jpg'))
    try:
        if src.suffix.lower() in ('.mp4', '.avi', '.mkv', '.mov', '.webm'):
            if _ffmpeg_available():
                cmd = ["ffmpeg", "-y", "-i", str(src), "-vf", f"scale={size}:{size}", "-frames:v", "1", str(out)]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return FileResponse(str(out), filename=out.name)
        else:
            img = Image.open(src)
            img.thumbnail((size, size), Image.LANCZOS)
            img.save(out, quality=85)
            return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.get("/convert/formats")
def list_formats():
    """List all supported conversion formats and endpoints."""
    return {
        "categories": {
            "document": ["pdf", "word", "excel", "ppt"],
            "image": ["jpg", "png", "webp", "bmp", "gif", "svg"],
            "video": ["mp4", "avi", "mkv", "mov", "webm", "gif"],
            "audio": ["mp3", "wav", "aac", "ogg", "flac", "m4a"],
            "data": ["csv", "json", "xml", "yaml"],
            "archive": ["zip", "7z", "rar", "tar"],
        },
        "endpoints": "Visit /docs for full API documentation"
    }
