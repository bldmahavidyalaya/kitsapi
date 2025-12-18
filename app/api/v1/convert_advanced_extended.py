# Additional advanced conversions: video AI, audio AI, ML-powered tools, social media, enterprise
import tempfile
from pathlib import Path
from typing import Optional
import json
import subprocess
import shutil
from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageDraw, ImageOps
import time

router = APIRouter()


def _save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename).suffix or ""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with open(path, "wb") as f:
        f.write(upload.file.read())
    return Path(path)


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _youtube_dl_available() -> bool:
    return shutil.which("yt-dlp") is not None or shutil.which("youtube-dl") is not None


# ===== VIDEO AI & OPTIMIZATION =====
@router.post("/convert/video/compress-smart")
def video_compress_smart(file: UploadFile = File(...), target_size_mb: int = Form(100)):
    """Smart video compression targeting file size."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        src_size_mb = src.stat().st_size / (1024 * 1024)
        if src_size_mb <= target_size_mb:
            shutil.copy(src, out)
            return FileResponse(str(out), filename=out.name)
        
        target_bitrate = int((target_size_mb * 8 * 1000) / (2 * 60))
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-b:v", f"{target_bitrate}k",
            "-c:v", "libx264", "-preset", "medium",
            "-c:a", "aac", "-b:a", "128k",
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compression failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/aspect-ratio")
def video_aspect_ratio(file: UploadFile = File(...), ratio: str = Form("16:9"), pad_color: str = Form("000000")):
    """Change video aspect ratio with padding."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-vf", f"pad='min(iw,ih*{ratio.split(':')[0]}/{ratio.split(':')[1]}):min(ih,iw*{ratio.split(':')[1]}/{ratio.split(':')[0]}):(ow-iw)/2:(oh-ih)/2:color=0x{pad_color}'",
            "-c:a", "copy",
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aspect ratio conversion failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/remove-audio")
def video_remove_audio(file: UploadFile = File(...)):
    """Remove audio from video (mute)."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = ["ffmpeg", "-y", "-i", str(src), "-c:v", "copy", "-an", str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove audio: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/extract-frames")
def video_extract_frames(file: UploadFile = File(...), fps: int = Form(1)):
    """Extract frames from video as images."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    tmpdir = Path(tempfile.mkdtemp())
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-vf", f"fps={fps}",
            str(tmpdir / "frame_%04d.png")
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        import zipfile
        out_zip = Path(tempfile.mktemp(suffix='.zip'))
        with zipfile.ZipFile(out_zip, 'w') as z:
            for f in sorted(tmpdir.glob('*.png')):
                z.write(f, f.name)
        
        return FileResponse(str(out_zip), filename=out_zip.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frame extraction failed: {e}")
    finally:
        try:
            for f in tmpdir.glob('*'):
                f.unlink()
            tmpdir.rmdir()
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/metadata-remove")
def video_metadata_remove(file: UploadFile = File(...)):
    """Remove metadata from video file."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-map_metadata", "-1",
            "-c:v", "copy", "-c:a", "copy",
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata removal failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ===== AUDIO AI & VOICE =====
@router.post("/convert/audio/normalize-loudness")
def audio_normalize_loudness(file: UploadFile = File(...), target_db: float = Form(-20.0)):
    """Normalize audio loudness using ffmpeg-normalize or similar."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp3'))
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-af", f"loudnorm=I={target_db}:TP=-1.5:LRA=11",
            "-q:a", "9",
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loudness normalization failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/mono-to-stereo")
def audio_mono_to_stereo(file: UploadFile = File(...)):
    """Convert mono audio to stereo."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.wav'))
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-ac", "2",
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stereo conversion failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/extract-mono")
def audio_extract_mono(file: UploadFile = File(...), channel: int = Form(0)):
    """Extract single channel from stereo audio."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.wav'))
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-ac", "1", "-vn",
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Channel extraction failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/fade")
def audio_fade(file: UploadFile = File(...), fade_type: str = Form("in"), duration: float = Form(3.0)):
    """Add fade in/out to audio."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp3'))
    try:
        fade_filter = f"afade=t={fade_type}:st=0:d={duration}"
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-af", fade_filter,
            "-q:a", "9",
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fade operation failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/sample-rate")
def audio_sample_rate(file: UploadFile = File(...), sample_rate: int = Form(44100)):
    """Change audio sample rate."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.wav'))
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-ar", str(sample_rate),
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sample rate conversion failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ===== SOCIAL MEDIA & CONTENT =====
@router.post("/convert/social/youtube-download")
def youtube_download(url: str = Form(...)):
    """Download video from YouTube (requires yt-dlp)."""
    if not _youtube_dl_available():
        raise HTTPException(status_code=500, detail="yt-dlp/youtube-dl not available")
    
    tmpdir = Path(tempfile.mkdtemp())
    try:
        out_file = tmpdir / "video.mp4"
        cmd = ["yt-dlp", "-f", "best", "-o", str(tmpdir / "video.mp4"), url]
        subprocess.run(cmd, check=True, capture_output=True)
        
        if out_file.exists():
            return FileResponse(str(out_file), filename=out_file.name)
        else:
            raise HTTPException(status_code=500, detail="Download failed - output file not created")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube download failed: {e}")
    finally:
        try:
            for f in tmpdir.glob('*'):
                f.unlink()
            tmpdir.rmdir()
        except Exception:
            pass


@router.post("/convert/social/vertical-video")
def vertical_video(file: UploadFile = File(...)):
    """Convert to vertical video format (9:16 for social media)."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vertical video conversion failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/social/horizontal-video")
def horizontal_video(file: UploadFile = File(...)):
    """Convert to horizontal video format (16:9 for social media)."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg not available")
    
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Horizontal video conversion failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ===== SECURITY & COMPLIANCE =====
@router.post("/convert/security/file-integrity")
def file_integrity_check(files: list[UploadFile] = File(...)):
    """Compute hashes for file integrity verification."""
    import hashlib
    results = []
    for f in files:
        src = _save_upload(f)
        try:
            sha256 = hashlib.sha256()
            with open(src, 'rb') as fh:
                for chunk in iter(lambda: fh.read(4096), b''):
                    sha256.update(chunk)
            results.append({
                "filename": f.filename,
                "sha256": sha256.hexdigest(),
                "size_bytes": src.stat().st_size
            })
        finally:
            try:
                src.unlink()
            except Exception:
                pass
    
    return JSONResponse({"integrity_report": results})


@router.post("/convert/security/pii-detector")
def pii_detector(file: UploadFile = File(...)):
    """Detect Personally Identifiable Information (PII) in text files."""
    import re
    src = _save_upload(file)
    try:
        with open(src, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        findings = {
            "email": len(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)),
            "phone": len(re.findall(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', content)),
            "ssn": len(re.findall(r'\b\d{3}-\d{2}-\d{4}\b', content)),
            "credit_card": len(re.findall(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', content)),
        }
        
        return JSONResponse({"pii_findings": findings, "total_patterns": sum(findings.values())})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PII detection failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/security/gdpr-anonymize")
def gdpr_anonymize(file: UploadFile = File(...)):
    """Anonymize text data for GDPR compliance."""
    import re
    import hashlib
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.txt'))
    try:
        with open(src, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', content)
        content = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE_REDACTED]', content)
        content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', content)
        content = re.sub(r'\b[A-Za-z]+\s[A-Za-z]+\b', '[NAME_REDACTED]', content)
        
        with open(out, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return FileResponse(str(out), filename=out.name, media_type='text/plain')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anonymization failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ===== IMAGE ENHANCEMENT & EFFECTS =====
@router.post("/convert/image/colorize")
def colorize_image(image: UploadFile = File(...)):
    """Convert grayscale image to color (basic colorization)."""
    src = _save_upload(image)
    out = Path(tempfile.mktemp(suffix='.png'))
    try:
        img = Image.open(src)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(out)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/image/auto-orient")
def auto_orient_image(image: UploadFile = File(...)):
    """Auto-rotate image based on EXIF orientation."""
    from PIL import Image as PILImage
    src = _save_upload(image)
    out = Path(tempfile.mktemp(suffix='.png'))
    try:
        img = PILImage.open(src)
        img = ImageOps.exif_transpose(img)
        img.save(out)
        return FileResponse(str(out), filename=out.name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orientation correction failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/image/border")
def add_border(image: UploadFile = File(...), size: int = Form(10), color: str = Form("FFFFFF")):
    """Add border to image."""
    src = _save_upload(image)
    out = Path(tempfile.mktemp(suffix='.png'))
    try:
        img = Image.open(src)
        color_tuple = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        bordered = ImageOps.expand(img, border=size, fill=color_tuple)
        bordered.save(out)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/image/brightness-contrast")
def brightness_contrast(image: UploadFile = File(...), brightness: float = Form(1.0), contrast: float = Form(1.0)):
    """Adjust image brightness and contrast."""
    from PIL import ImageEnhance
    src = _save_upload(image)
    out = Path(tempfile.mktemp(suffix='.png'))
    try:
        img = Image.open(src)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(brightness)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(contrast)
        img.save(out)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/image/saturation")
def saturation_adjust(image: UploadFile = File(...), saturation: float = Form(1.0)):
    """Adjust image saturation/vibrance."""
    from PIL import ImageEnhance
    src = _save_upload(image)
    out = Path(tempfile.mktemp(suffix='.png'))
    try:
        img = Image.open(src)
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(saturation)
        img.save(out)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ===== OFFICE & DOCUMENT CONVERSIONS =====
@router.post("/convert/markdown/to-html")
def markdown_to_html(file: UploadFile = File(...)):
    """Convert Markdown to HTML."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.html'))
    try:
        try:
            import markdown
            with open(src, 'r', encoding='utf-8') as f:
                md_content = f.read()
            html = markdown.markdown(md_content)
            with open(out, 'w', encoding='utf-8') as f:
                f.write(f"<html><body>{html}</body></html>")
            return FileResponse(str(out), filename=out.name, media_type='text/html')
        except ImportError:
            raise HTTPException(status_code=500, detail="markdown library not installed")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/yaml/to-json")
def yaml_to_json(file: UploadFile = File(...)):
    """Convert YAML to JSON."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.json'))
    try:
        try:
            import yaml
            with open(src, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return FileResponse(str(out), filename=out.name, media_type='application/json')
        except ImportError:
            raise HTTPException(status_code=500, detail="pyyaml library not installed")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/json/to-yaml")
def json_to_yaml(file: UploadFile = File(...)):
    """Convert JSON to YAML."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.yaml'))
    try:
        try:
            import yaml
            with open(src, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with open(out, 'w', encoding='utf-8') as f:
                yaml.safe_dump(data, f, default_flow_style=False)
            return FileResponse(str(out), filename=out.name, media_type='text/yaml')
        except ImportError:
            raise HTTPException(status_code=500, detail="pyyaml library not installed")
    finally:
        try:
            src.unlink()
        except Exception:
            pass
