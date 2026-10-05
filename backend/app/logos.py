from base64 import b64encode
from io import BytesIO

from fastapi import APIRouter, HTTPException, Request
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.models import Professional
from app.profiles import TenantSession, User

router = APIRouter(prefix="/api/v1/me", tags=["logo"])


def normalize_logo(data: bytes) -> bytes:
    if not data or len(data) > 2 * 1024 * 1024:
        raise ValueError("Escolha uma imagem de até 2 MB")
    try:
        with Image.open(BytesIO(data), formats=["PNG", "JPEG", "WEBP"]) as source:
            if max(source.size) > 4096 or getattr(source, "n_frames", 1) != 1:
                raise ValueError("Use uma imagem estática de até 4096 × 4096 pixels")
            source.load()
            normalized = ImageOps.exif_transpose(source).convert("RGBA")
            normalized.thumbnail((256, 256), Image.Resampling.LANCZOS)
            # Fresh pixels discard EXIF, text chunks and other uploaded metadata.
            clean = Image.new("RGBA", normalized.size)
            clean.paste(normalized)
            output = BytesIO()
            clean.save(output, format="PNG")
            result = output.getvalue()
            if len(result) > 270000:
                raise ValueError("Imagem muito complexa")
            return result
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("Envie uma imagem PNG, JPG ou WebP válida") from exc


@router.put("/logo")
async def save_logo(request: Request, user: User, session: TenantSession):
    data = await request.body()
    try:
        normalized = await run_in_threadpool(normalize_logo, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return await run_in_threadpool(write_logo, session, user, normalized)


def write_logo(session, user, data):
    profile = session.scalar(
        select(Professional).where(Professional.owner_id == user).with_for_update()
    )
    if profile is None:
        raise HTTPException(404, "Salve seu perfil antes de adicionar a logo")
    profile.logo_png = data
    session.flush()
    return {"logo": "data:image/png;base64," + b64encode(data).decode() if data else None}


@router.delete("/logo")
def remove_logo(user: User, session: TenantSession):
    return write_logo(session, user, None)
