from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, UploadFile, status

ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}
MAGIC = {"image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG\r\n\x1a\n",)}


async def read_valid_image(upload: UploadFile, max_bytes: int) -> tuple[bytes, str]:
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Yalnız JPEG və PNG qəbul edilir.")
    data = await upload.read(max_bytes + 1)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Şəkil boşdur.")
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"Şəkil maksimum {max_bytes // (1024 * 1024)} MB ola bilər.")
    if not any(data.startswith(signature) for signature in MAGIC[content_type]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fayl məzmunu şəkil formatına uyğun deyil.")
    return data, ALLOWED_TYPES[content_type]
