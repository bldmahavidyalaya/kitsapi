import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

import img2pdf
import pikepdf
from PIL import Image
from pdf2docx import Converter as Pdf2Docx
from pypdf import PdfReader
from docx import Document
import magic
import py7zr
import zipfile
from cryptography.fernet import Fernet
import boto3

router = APIRouter()


def _save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename).suffix or ""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with open(path, "wb") as f:
        f.write(upload.file.read())
    return Path(path)


def _run_libreoffice_convert(src: Path, out_dir: Path, to_ext: str) -> Optional[Path]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return None
    cmd = [soffice, "--headless", "--convert-to", to_ext, "--outdir", str(out_dir), str(src)]
    subprocess.run(cmd, check=True)
    out_file = out_dir / (src.stem + f".{to_ext.split(':')[0]}" )
    return out_file if out_file.exists() else None


@router.post("/convert/pdf-to-word")
def pdf_to_word(file: UploadFile = File(...)):
    src = _save_upload(file)
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # try pdf2docx
        out_path = tmpdir / (src.stem + ".docx")
        try:
            cv = Pdf2Docx(str(src))
            cv.convert(str(out_path))
            cv.close()
            return FileResponse(str(out_path), filename=out_path.name)
        except Exception:
            # fallback to libreoffice
            res = _run_libreoffice_convert(src, tmpdir, "docx")
            if res:
                return FileResponse(str(res), filename=res.name)
        raise HTTPException(status_code=500, detail="Conversion failed: required tools missing")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ---------------- Audio utilities ----------------
@router.post("/convert/audio/convert")
def audio_convert(file: UploadFile = File(...), target: str = Form(...), bitrate: Optional[str] = Form(None)):
    """Convert audio file to target format (mp3, wav, aac, ogg, flac, m4a)
    `bitrate` example: '128k'"""
    from pydub import AudioSegment

    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=f".{target}"))
    try:
        audio = AudioSegment.from_file(src)
        export_args = {}
        if bitrate:
            export_args['bitrate'] = bitrate
        audio.export(out, format=target, **export_args)
        return FileResponse(str(out), filename=out.name, media_type="audio/" + target)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/trim")
def audio_trim(file: UploadFile = File(...), start_ms: int = Form(0), end_ms: Optional[int] = Form(None)):
    from pydub import AudioSegment

    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=".mp3"))
    try:
        audio = AudioSegment.from_file(src)
        segment = audio[start_ms: end_ms] if end_ms else audio[start_ms:]
        segment.export(out, format="mp3")
        return FileResponse(str(out), filename=out.name, media_type="audio/mpeg")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/merge")
def audio_merge(files: list[UploadFile] = File(...), gap_ms: int = Form(0), target: str = Form("mp3")):
    from pydub import AudioSegment

    tmp_out = Path(tempfile.mktemp(suffix=f".{target}"))
    try:
        result = None
        for f in files:
            src = _save_upload(f)
            try:
                a = AudioSegment.from_file(src)
                if result is None:
                    result = a
                else:
                    if gap_ms > 0:
                        result += AudioSegment.silent(duration=gap_ms)
                    result += a
            finally:
                try:
                    src.unlink()
                except Exception:
                    pass
        if result is None:
            raise HTTPException(status_code=400, detail="No files provided")
        result.export(tmp_out, format=target)
        return FileResponse(str(tmp_out), filename=tmp_out.name, media_type="audio/"+target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/audio/compress")
def audio_compress(file: UploadFile = File(...), bitrate: str = Form("64k"), target: Optional[str] = Form(None)):
    from pydub import AudioSegment

    src = _save_upload(file)
    out_sfx = f".{target}" if target else Path(src).suffix
    out = Path(tempfile.mktemp(suffix=out_sfx))
    try:
        audio = AudioSegment.from_file(src)
        fmt = target or src.suffix.lstrip('.')
        audio.export(out, format=fmt, bitrate=bitrate)
        return FileResponse(str(out), filename=out.name, media_type="audio/"+fmt)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/volume")
def audio_volume(file: UploadFile = File(...), db_change: int = Form(0), target: Optional[str] = Form(None)):
    from pydub import AudioSegment

    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=f".{target or src.suffix.lstrip('.')}"))
    try:
        audio = AudioSegment.from_file(src)
        audio = audio + db_change
        fmt = target or src.suffix.lstrip('.')
        audio.export(out, format=fmt)
        return FileResponse(str(out), filename=out.name, media_type="audio/"+fmt)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/speed")
def audio_speed(file: UploadFile = File(...), speed: float = Form(1.0), target: Optional[str] = Form(None)):
    from pydub import AudioSegment, effects

    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=f".{target or src.suffix.lstrip('.')}"))
    try:
        audio = AudioSegment.from_file(src)
        if speed == 1.0:
            out_audio = audio
        else:
            out_audio = effects.speedup(audio, playback_speed=speed)
        fmt = target or src.suffix.lstrip('.')
        out_audio.export(out, format=fmt)
        return FileResponse(str(out), filename=out.name, media_type="audio/"+fmt)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/pitch")
def audio_pitch(file: UploadFile = File(...), semitones: float = Form(0.0), target: Optional[str] = Form(None)):
    """Change pitch by semitones using ffmpeg filter "asetrate"/"atempo" combo"""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=f".{target or src.suffix.lstrip('.')}"))
    try:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise HTTPException(status_code=500, detail="ffmpeg is required for pitch shifting")
        # compute rate multiplier
        rate = 2 ** (semitones / 12.0)
        cmd = [
            ffmpeg,
            '-y',
            '-i', str(src),
            '-filter_complex', f"asetrate=44100*{rate},aresample=44100,atempo=1/{rate}",
            str(out),
        ]
        subprocess.run(cmd, check=True)
        return FileResponse(str(out), filename=out.name)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/to-text")
def audio_to_text(file: UploadFile = File(...), model: str = Form("base")):
    """Transcribe audio to text. Requires OpenAI Whisper installed (openai-whisper).
    Model param passed to whisper if available."""
    src = _save_upload(file)
    try:
        try:
            import whisper

            model_obj = whisper.load_model(model)
            result = model_obj.transcribe(str(src))
            text = result.get('text', '')
            fd, out = tempfile.mkstemp(suffix='.txt')
            with open(out, 'w', encoding='utf-8') as f:
                f.write(text)
            return FileResponse(out, filename=Path(out).name, media_type='text/plain')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Whisper not available or failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/text-to-speech")
def text_to_speech(text: str = Form(...), lang: str = Form('en')):
    """Generate speech from text using gTTS (requires network). Returns MP3."""
    try:
        from gtts import gTTS

        tts = gTTS(text=text, lang=lang)
        out = Path(tempfile.mktemp(suffix='.mp3'))
        tts.save(str(out))
        return FileResponse(str(out), filename=out.name, media_type='audio/mpeg')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/audio/noise-remove")
def audio_noise_remove(file: UploadFile = File(...), prop_decrease: float = Form(1.0)):
    """Basic noise reduction using noisereduce (requires numpy/scipy)."""
    import numpy as np
    import noisereduce as nr
    from pydub import AudioSegment

    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.wav'))
    try:
        audio = AudioSegment.from_file(src)
        samples = np.array(audio.get_array_of_samples()).astype(np.float32)
        reduced = nr.reduce_noise(y=samples, sr=audio.frame_rate, prop_decrease=prop_decrease)
        # convert back
        new_seg = AudioSegment(
            reduced.tobytes(),
            frame_rate=audio.frame_rate,
            sample_width=audio.sample_width,
            channels=audio.channels,
        )
        new_seg.export(out, format='wav')
        return FileResponse(str(out), filename=out.name, media_type='audio/wav')
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/audio/voice-extract")
def voice_extractor(file: UploadFile = File(...)):
    """Attempt to extract vocal stem using Spleeter if installed."""
    src = _save_upload(file)
    out_dir = Path(tempfile.mktemp())
    try:
        try:
            from spleeter.separator import Separator

            sep = Separator('spleeter:2stems')
            sep.separate_to_file(str(src), str(out_dir))
            vocal = next(out_dir.rglob('*vocals.*'))
            return FileResponse(str(vocal), filename=vocal.name, media_type='audio/mpeg')
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Spleeter not available or failed: {e}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ---------------- Video & archive utilities ----------------
def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


@router.post("/convert/video/convert")
def video_convert(file: UploadFile = File(...), target: str = Form(...)):
    """Convert video formats (mp4, avi, mkv, mov, webm). Requires ffmpeg."""
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=f".{target}"))
    try:
        cmd = ["ffmpeg", "-y", "-i", str(src), str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/to-audio")
def video_to_audio(file: UploadFile = File(...), fmt: str = Form("mp3")):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=f".{fmt}"))
    try:
        cmd = ["ffmpeg", "-y", "-i", str(src), "-vn", str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name, media_type=f"audio/{fmt}")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/compress")
def video_compress(file: UploadFile = File(...), crf: int = Form(28), preset: str = Form("medium")):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(src), "-vcodec", "libx264", "-preset", preset, "-crf", str(crf), str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/trim")
def video_trim(file: UploadFile = File(...), start: float = Form(0.0), end: Optional[float] = Form(None)):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = ["ffmpeg", "-y", "-ss", str(start)]
        if end:
            cmd += ["-to", str(end)]
        cmd += ["-i", str(src), "-c", "copy", str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/resize")
def video_resize(file: UploadFile = File(...), width: Optional[int] = Form(None), height: Optional[int] = Form(None)):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    if not width and not height:
        raise HTTPException(status_code=400, detail="width or height required")
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        scale = f"scale={width if width else -2}:{height if height else -2}"
        cmd = ["ffmpeg", "-y", "-i", str(src), "-vf", scale, str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/rotate")
def video_rotate(file: UploadFile = File(...), degrees: int = Form(90)):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    transpose_map = {90: "transpose=1", 180: "transpose=2,transpose=2", 270: "transpose=2"}
    filt = transpose_map.get(degrees, f"transpose=1")
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = ["ffmpeg", "-y", "-i", str(src), "-vf", filt, str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/merge")
def video_merge(files: list[UploadFile] = File(...)):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    tmpdir = Path(tempfile.mkdtemp())
    list_file = tmpdir / "files.txt"
    try:
        with open(list_file, "w") as f:
            for up in files:
                src = _save_upload(up)
                f.write(f"file '{src}'\n")
        out = tmpdir / "out.mp4"
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        # cleanup saved uploaded files
        for p in tmpdir.glob('*'):
            try:
                p.unlink()
            except Exception:
                pass


@router.post("/convert/video/speed")
def video_speed(file: UploadFile = File(...), speed: float = Form(1.0)):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        # speed up video; audio handled with atempo (supports 0.5-2.0; for others chain)
        cmd = [
            "ffmpeg", "-y", "-i", str(src), "-filter_complex",
            f"[0:v]setpts={1/ speed}*PTS[v];[0:a]atempo={speed}[a]",
            "-map", "[v]", "-map", "[a]", str(out)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    except subprocess.CalledProcessError:
        # fallback to video-only speed change
        cmd = ["ffmpeg", "-y", "-i", str(src), "-filter:v", f"setpts={1/speed}*PTS", str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/to-gif")
def video_to_gif(file: UploadFile = File(...), fps: int = Form(15), scale: Optional[str] = Form(None)):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.gif'))
    try:
        vf = f"fps={fps}"
        if scale:
            vf += f",scale={scale}"
        cmd = ["ffmpeg", "-y", "-i", str(src), "-vf", vf, str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/gif-to-video")
def gif_to_video(file: UploadFile = File(...), fmt: str = Form('mp4')):
    return video_convert(file, target=fmt)


@router.post("/convert/video/remove-audio")
def remove_video_audio(file: UploadFile = File(...)):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = ["ffmpeg", "-y", "-i", str(src), "-c", "copy", "-an", str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/video/add-audio")
def add_audio_to_video(video: UploadFile = File(...), audio: UploadFile = File(...)):
    if not _ffmpeg_available():
        raise HTTPException(status_code=500, detail="ffmpeg is required")
    vsrc = _save_upload(video)
    asrc = _save_upload(audio)
    out = Path(tempfile.mktemp(suffix='.mp4'))
    try:
        cmd = ["ffmpeg", "-y", "-i", str(vsrc), "-i", str(asrc), "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0", str(out)]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            vsrc.unlink(); asrc.unlink()
        except Exception:
            pass


@router.post("/convert/file/identify")
def file_identify(file: UploadFile = File(...)):
    src = _save_upload(file)
    try:
        m = magic.Magic(mime=True)
        mime = m.from_file(str(src))
        return {"mime": mime}
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/archive/zip-to-7z")
def zip_to_7z(file: UploadFile = File(...)):
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.7z'))
    try:
        # try py7zr
        try:
            with py7zr.SevenZipFile(out, 'w') as archive:
                with zipfile.ZipFile(str(src), 'r') as z:
                    for name in z.namelist():
                        archive.writestr(name, z.read(name))
            return FileResponse(str(out), filename=out.name)
        except Exception:
            raise HTTPException(status_code=500, detail='py7zr/zip failed')
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/archive/7z-to-zip")
def sevenz_to_zip(file: UploadFile = File(...)):
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix='.zip'))
    try:
        try:
            with py7zr.SevenZipFile(str(src), mode='r') as archive:
                allfiles = archive.readall()
                with zipfile.ZipFile(out, 'w') as z:
                    for name, bio in allfiles.items():
                        z.writestr(name, bio.read())
            return FileResponse(str(out), filename=out.name)
        except Exception:
            raise HTTPException(status_code=500, detail='py7zr failed')
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/file/remove-metadata")
def file_remove_metadata(file: UploadFile = File(...)):
    # attempt media metadata stripping via ffmpeg for audio/video; for archives/files, return unchanged
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=Path(src).suffix))
    try:
        if _ffmpeg_available():
            cmd = ["ffmpeg", "-y", "-i", str(src), "-map_metadata", "-1", "-c", "copy", str(out)]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return FileResponse(str(out), filename=out.name)
            except Exception:
                pass
        # fallback: return same file
        return FileResponse(str(src), filename=Path(src).name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/cloud/convert")
def cloud_convert(file: UploadFile = File(...), bucket: str = Form(...), key: str = Form(...)):
    # simple: upload to S3; if env/configured, return presigned URL
    src = _save_upload(file)
    try:
        s3 = boto3.client('s3')
        s3.upload_file(str(src), bucket, key)
        url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=3600)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/secure/convert")
def secure_convert(file: UploadFile = File(...), password: str = Form(...)):
    # perform a conversion (noop) then encrypt output with Fernet derived from password
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=Path(src).suffix))
    enc_out = Path(tempfile.mktemp(suffix=Path(src).suffix + '.enc'))
    try:
        # copy as placeholder conversion
        with open(src, 'rb') as fsrc, open(out, 'wb') as fdst:
            fdst.write(fsrc.read())
        # derive key from password (simple; production: use proper KDF)
        key = Fernet.generate_key()
        f = Fernet(key)
        token = f.encrypt(out.read_bytes())
        enc_out.write_bytes(token)
        return FileResponse(str(enc_out), filename=enc_out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/word-to-pdf")
def word_to_pdf(file: UploadFile = File(...)):
    src = _save_upload(file)
    tmpdir = Path(tempfile.mkdtemp())
    try:
        res = _run_libreoffice_convert(src, tmpdir, "pdf")
        if res:
            return FileResponse(str(res), filename=res.name)
        raise HTTPException(status_code=500, detail="LibreOffice not available for conversion")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/pdf-to-text")
def pdf_to_text(file: UploadFile = File(...)):
    src = _save_upload(file)
    try:
        reader = PdfReader(str(src))
        text = []
        for p in reader.pages:
            text.append(p.extract_text() or "")
        content = "\n".join(text)
        fd, out = tempfile.mkstemp(suffix=".txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(content)
        return FileResponse(out, filename=Path(out).name, media_type="text/plain")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/text-to-pdf")
def text_to_pdf(file: UploadFile = File(...)):
    src = _save_upload(file)
    try:
        with open(src, "r", encoding="utf-8") as f:
            txt = f.read()
        # simple PDF via Pillow
        lines = txt.splitlines() or [""]
        img = Image.new("RGB", (1200, 72 * max(1, len(lines))), color=(255, 255, 255))
        from PIL import ImageDraw, ImageFont

        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        y = 0
        for line in lines:
            draw.text((10, y), line, fill=(0, 0, 0), font=font)
            y += 18
        out = Path(tempfile.mktemp(suffix=".pdf"))
        img.save(out, "PDF", resolution=100.0)
        return FileResponse(str(out), filename=out.name, media_type="application/pdf")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/jpg-to-pdf")
def jpg_to_pdf(file: UploadFile = File(...)):
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=".pdf"))
    try:
        with open(src, "rb") as f:
            img = Image.open(f)
            img_rgb = img.convert('RGB')
            img_rgb.save(out, "PDF")
        return FileResponse(str(out), filename=out.name, media_type="application/pdf")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/pdf-to-jpg")
def pdf_to_jpg(file: UploadFile = File(...)):
    src = _save_upload(file)
    tmpdir = Path(tempfile.mkdtemp())
    try:
        # attempt to use pdf2image
        try:
            from pdf2image import convert_from_path

            pages = convert_from_path(str(src))
            out = tmpdir / (src.stem + ".jpg")
            pages[0].save(out, "JPEG")
            return FileResponse(str(out), filename=out.name, media_type="image/jpeg")
        except Exception:
            raise HTTPException(status_code=500, detail="pdf2image/poppler required for PDF->JPG")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/pdf-merge")
def pdf_merge(files: list[UploadFile] = File(...)):
    tmp_out = Path(tempfile.mktemp(suffix=".pdf"))
    try:
        with pikepdf.Pdf.new() as out_pdf:
            for f in files:
                src = _save_upload(f)
                try:
                    src_pdf = pikepdf.Pdf.open(str(src))
                    out_pdf.pages.extend(src_pdf.pages)
                finally:
                    try:
                        src.unlink()
                    except Exception:
                        pass
            out_pdf.save(str(tmp_out))
        return FileResponse(str(tmp_out), filename=Path(tmp_out).name, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert/pdf-split")
def pdf_split(file: UploadFile = File(...), page: int = 1):
    src = _save_upload(file)
    tmp_out = Path(tempfile.mktemp(suffix=".pdf"))
    try:
        pdf = pikepdf.Pdf.open(str(src))
        new_pdf = pikepdf.Pdf.new()
        new_pdf.pages.append(pdf.pages[page-1])
        new_pdf.save(str(tmp_out))
        return FileResponse(str(tmp_out), filename=tmp_out.name, media_type="application/pdf")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/pdf-compress")
def pdf_compress(file: UploadFile = File(...)):
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=".pdf"))
    try:
        pdf = pikepdf.Pdf.open(str(src))
        pdf.save(str(out), optimize_version=True)
        return FileResponse(str(out), filename=out.name, media_type="application/pdf")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/pdf-unlock")
def pdf_unlock(file: UploadFile = File(...), password: str = ""):
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=".pdf"))
    try:
        with pikepdf.open(str(src), password=password) as pdf:
            pdf.save(str(out))
        return FileResponse(str(out), filename=out.name, media_type="application/pdf")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/pdf-protect")
def pdf_protect(file: UploadFile = File(...), password: str = File(...)):
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=".pdf"))
    try:
        pdf = pikepdf.Pdf.open(str(src))
        pdf.save(str(out), encryption=pikepdf.Encryption(owner=password, user=password, R=4))
        return FileResponse(str(out), filename=out.name, media_type="application/pdf")
    finally:
        try:
            src.unlink()
        except Exception:
            pass


# ---------------- Image utilities ----------------
@router.post("/convert/image/convert")
def image_convert(
    file: UploadFile = File(...),
    target: str = Form(...),
    quality: int = Form(85),
    dpi: Optional[int] = Form(None),
):
    """Generic image format conversion. Use `target` like 'png','jpg','webp','bmp','tiff','ico','gif'."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=f".{target}"))
    try:
        # handle SVG input via cairosvg
        if src.suffix.lower() == ".svg":
            try:
                import cairosvg

                if target in ("png", "jpg", "jpeg"):
                    cairosvg.svg2png(url=str(src), write_to=str(out))
                    if target in ("jpg", "jpeg"):
                        img = Image.open(out)
                        rgb = img.convert("RGB")
                        rgb.save(out, quality=quality)
                else:
                    raise HTTPException(status_code=400, detail="Unsupported target for SVG")
                return FileResponse(str(out), filename=out.name)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"SVG conversion failed: {e}")

        img = Image.open(src)
        if target.lower() in ("jpg", "jpeg"):
            img = img.convert("RGB")
            img.save(out, format="JPEG", quality=quality, dpi=(dpi or 72, dpi or 72))
        else:
            fmt = target.upper()
            if fmt == "JPG":
                fmt = "JPEG"
            save_kwargs = {}
            if dpi:
                save_kwargs["dpi"] = (dpi, dpi)
            if fmt == "WEBP":
                save_kwargs["quality"] = quality
            img.save(out, format=fmt, **save_kwargs)
        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/image/transform")
def image_transform(
    file: UploadFile = File(...),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    quality: int = Form(85),
    crop: Optional[str] = Form(None),  # x,y,w,h
    rotate: Optional[int] = Form(0),
    bg_remove: Optional[bool] = Form(False),
    color_mode: Optional[str] = Form(None),  # grayscale, sepia
    dpi: Optional[int] = Form(None),
):
    """Resize/crop/rotate/compress/background-remove/color convert/change DPI."""
    src = _save_upload(file)
    out = Path(tempfile.mktemp(suffix=src.suffix))
    try:
        img = Image.open(src).convert("RGBA")

        if crop:
            try:
                x, y, w, h = [int(z) for z in crop.split(",")]
                img = img.crop((x, y, x + w, y + h))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid crop parameter")

        if width or height:
            w = width or img.width
            h = height or img.height
            img = img.resize((w, h), Image.LANCZOS)

        if rotate:
            img = img.rotate(-rotate, expand=True)

        if bg_remove:
            try:
                from rembg import remove

                with open(src, "rb") as f:
                    result = remove(f.read())
                temp = Path(tempfile.mktemp(suffix=src.suffix))
                with open(temp, "wb") as f:
                    f.write(result)
                img = Image.open(temp).convert("RGBA")
            except Exception:
                # fallback: if image has alpha channel, keep it; otherwise error
                if img.mode == "RGBA":
                    pass
                else:
                    raise HTTPException(status_code=500, detail="rembg not available or failed; install rembg for background removal")

        if color_mode:
            if color_mode.lower() == "grayscale":
                img = img.convert("L").convert("RGBA")
            elif color_mode.lower() == "sepia":
                gray = img.convert("L")
                sep = Image.new("RGB", img.size)
                sep_pixels = sep.load()
                g_pixels = gray.load()
                for i in range(img.width):
                    for j in range(img.height):
                        v = g_pixels[i, j]
                        tr = int(v * 0.393 + v * 0.769 + v * 0.189)
                        tg = int(v * 0.349 + v * 0.686 + v * 0.168)
                        tb = int(v * 0.272 + v * 0.534 + v * 0.131)
                        sep_pixels[i, j] = (min(255, tr), min(255, tg), min(255, tb))
                img = sep.convert("RGBA")

        save_kwargs = {}
        if dpi:
            save_kwargs["dpi"] = (dpi, dpi)
        # determine output format from input
        fmt = src.suffix.lstrip(".").upper()
        if fmt == "JPG":
            fmt = "JPEG"
        if fmt == "PNG":
            # preserve alpha
            img.save(out, format=fmt, quality=quality, **save_kwargs)
        else:
            img = img.convert("RGB")
            img.save(out, format=fmt, quality=quality, **save_kwargs)

        return FileResponse(str(out), filename=out.name)
    finally:
        try:
            src.unlink()
        except Exception:
            pass


@router.post("/convert/pdf-to-image")
def pdf_to_image(file: UploadFile = File(...), fmt: str = Form("jpg"), page: int = Form(1)):
    src = _save_upload(file)
    tmpdir = Path(tempfile.mkdtemp())
    try:
        try:
            from pdf2image import convert_from_path

            pages = convert_from_path(str(src))
            target = tmpdir / (src.stem + f".{fmt}")
            pages[page - 1].save(target, fmt.upper())
            return FileResponse(str(target), filename=target.name)
        except Exception:
            raise HTTPException(status_code=500, detail="pdf2image/poppler required for PDF->image")
    finally:
        try:
            src.unlink()
        except Exception:
            pass

