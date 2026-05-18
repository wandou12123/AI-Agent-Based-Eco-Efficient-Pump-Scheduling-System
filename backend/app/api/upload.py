import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.models import User

router = APIRouter()
settings = get_settings()

ALLOWED_EXTENSIONS = {".docx", ".doc", ".pdf", ".txt", ".csv", ".json"}


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}")

    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "filename": filename,
        "original_name": file.filename,
        "url": f"/uploads/{filename}",
        "size": len(content),
    }
