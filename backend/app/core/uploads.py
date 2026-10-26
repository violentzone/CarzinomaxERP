"""
Chat attachments: validate and store the files a user attaches in the chatbox, load them back for the orchestrator
Files live under <UPLOAD_DIR>/<user_id>/<uuid>.<ext>; the uuid is the attachment id and the directory proves ownership to the router (the chat tools resolve by uuid alone). No table, no retention.
"""
import asyncio
import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from PIL import Image, ImageOps
from pydantic import BaseModel
from pypdf import PdfReader

from app.core.config import settings

UPLOAD_ROOT = Path(settings.UPLOAD_DIR) if Path(settings.UPLOAD_DIR).is_absolute() else Path(__file__).resolve().parent.parent.parent / settings.UPLOAD_DIR  # backend/uploads by default, anchored like LOGS_DIR
EXTENSIONS = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'application/pdf': 'pdf'}  # allowed types and the extension they are stored with
MIME_BY_EXTENSION = {extension: mime for mime, extension in EXTENSIONS.items()}  # stored extension back to its type
IMAGE_TYPES = ('image/png', 'image/jpeg', 'image/webp')  # types sent to the model as image blocks
CHUNK_BYTES = 1024 * 1024  # copy granularity when an upload is written to disk
MAX_IMAGE_PIXELS = 1_003_520  # width x height after downscaling (1280 x 784), what a small GPU accepts per image
JPEG_QUALITY = 80  # re-encode quality of stored images
PDF_TEXT_MAX_CHARS = 60_000  # roughly 15k tokens, stops a long PDF from filling the context
ATTACHMENT_ID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')  # uuid4 as produced by str(uuid4()), rejects path tricks


class Attachment(BaseModel):
    id: str
    name: str  # original file name, display only
    content_type: str  # sniffed type of the stored file
    size: int  # bytes on disk after processing


class LoadedAttachment(BaseModel):
    id: str
    content_type: str
    data: bytes


def sniff_content_type(head: bytes) -> str | None:
    """
    Detect the file type from its first bytes, the declared content type is never trusted
    Args:
        head: At least the first 12 bytes of the file

    Returns:
        One of the keys of `EXTENSIONS`, None for anything else
    """
    if head.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if head.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return 'image/webp'
    if head.startswith(b'%PDF-'):
        return 'application/pdf'
    return None


def downscale_image(path: Path) -> Path:
    """
    Re-encode a stored image as JPEG, rotated by its EXIF orientation, flattened to RGB and scaled down to at most `MAX_IMAGE_PIXELS` pixels
    Args:
        path: Stored image, removed when the JPEG gets a different name

    Returns:
        Path of the JPEG

    Raises:
        ValueError: The bytes are not a decodable image
    """
    jpeg_path = path.with_suffix('.jpg')
    try:
        with Image.open(path) as image:
            converted = ImageOps.exif_transpose(image).convert('RGB')
    except Exception:
        path.unlink(missing_ok=True)
        raise ValueError('Image could not be decoded')
    width, height = converted.size
    if width * height > MAX_IMAGE_PIXELS:
        scale = (MAX_IMAGE_PIXELS / (width * height)) ** 0.5
        converted = converted.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.LANCZOS)
    converted.save(jpeg_path, 'JPEG', quality=JPEG_QUALITY, optimize=True)
    if jpeg_path != path:
        path.unlink(missing_ok=True)
    return jpeg_path


async def save_attachment(user_id: int, upload: UploadFile) -> Attachment:
    """
    Validate one uploaded file and store it under the caller's directory; images are re-encoded as JPEG by `downscale_image`
    Args:
        user_id: Owner, the file goes into `<UPLOAD_ROOT>/<user_id>/`
        upload: Multipart file from `POST /chatbot/upload`

    Returns:
        `Attachment` with the id the chatbox refers to

    Raises:
        ValueError: Over `UPLOAD_MAX_BYTES`, not a PNG / JPEG / WebP / PDF, or an undecodable image
    """
    size_limit_mb = settings.UPLOAD_MAX_BYTES // (1024 * 1024)
    if upload.size is not None and upload.size > settings.UPLOAD_MAX_BYTES:
        raise ValueError(f'File exceeds the {size_limit_mb} MB limit')
    head = await upload.read(16)
    await upload.seek(0)
    content_type = sniff_content_type(head)
    if content_type is None:
        raise ValueError('Unsupported file type, allowed: PNG, JPEG, WebP, PDF')

    attachment_id = str(uuid4())
    user_dir = UPLOAD_ROOT / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f'{attachment_id}.{EXTENSIONS[content_type]}'
    written = 0
    with path.open('wb') as target:
        while chunk := await upload.read(CHUNK_BYTES):
            written += len(chunk)
            if written > settings.UPLOAD_MAX_BYTES:
                break
            target.write(chunk)
    if written > settings.UPLOAD_MAX_BYTES:
        path.unlink(missing_ok=True)
        raise ValueError(f'File exceeds the {size_limit_mb} MB limit')
    if content_type in IMAGE_TYPES:
        path = await asyncio.to_thread(downscale_image, path)
        content_type = 'image/jpeg'
    attachment = Attachment(id=attachment_id, name=Path(upload.filename or 'file').name[:120], content_type=content_type, size=path.stat().st_size)
    return attachment


def attachment_path(user_id: int | None, attachment_id: str) -> Path:
    """
    Resolve an attachment id to its file, inside the caller's directory only or, for the chat tools that do not know the caller, whoever uploaded it
    Args:
        user_id: Caller, another user's attachment resolves to nothing; None searches every user's directory (the uuid4 is known only to its uploader)
        attachment_id: Id returned by `POST /chatbot/upload`

    Returns:
        Path of the stored file

    Raises:
        ValueError: Malformed id, unknown id or an id that belongs to another user, all with the same message
    """
    if not ATTACHMENT_ID_RE.fullmatch(attachment_id):
        raise ValueError(f'Unknown attachment {attachment_id}')
    owner_dir = str(user_id) if user_id is not None else '*'
    matches = list(UPLOAD_ROOT.glob(f'{owner_dir}/{attachment_id}.*'))
    if not matches:
        raise ValueError(f'Unknown attachment {attachment_id}')
    return matches[0]


def load_attachment(user_id: int, attachment_id: str) -> LoadedAttachment:
    """
    Read a stored attachment of the caller
    Args:
        user_id: Caller
        attachment_id: Id returned by `POST /chatbot/upload`

    Returns:
        `LoadedAttachment` with the bytes and the type derived from the stored extension

    Raises:
        ValueError: See `attachment_path`
    """
    path = attachment_path(user_id, attachment_id)
    attachment = LoadedAttachment(id=attachment_id, content_type=MIME_BY_EXTENSION[path.suffix.lstrip('.')], data=path.read_bytes())
    return attachment


def extract_pdf_text(data: bytes) -> str:
    """
    Extract the text layer of a PDF for the model
    Args:
        data: PDF bytes

    Returns:
        Text of every page joined by blank lines, empty when the PDF has no text layer (a scan), cut at `PDF_TEXT_MAX_CHARS`

    Raises:
        ValueError: pypdf could not parse the file
    """
    try:
        reader = PdfReader(BytesIO(data))
        text = '\n\n'.join((page.extract_text() or '') for page in reader.pages).strip()
    except Exception:
        raise ValueError('PDF could not be parsed')
    if len(text) > PDF_TEXT_MAX_CHARS:
        text = f'{text[:PDF_TEXT_MAX_CHARS]}\n[truncated after {PDF_TEXT_MAX_CHARS} characters]'
    return text
