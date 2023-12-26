import logging
import tempfile
import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, status
from storeapi.libs.b2 import b2_upload_file

logger = logging.getLogger(__name__)
router  = APIRouter()

CHUNK_SIZE = 1024 * 1024

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile):
    file.read(CHUNK_SIZE)

    try:
        with tempfile.NamedTemporaryFile() as tempfile:
            filename = tempfile.name
            logger.info("Saving uploaded file temporarily to {filename}")

            async with aiofiles.open(filename, "wb") as f:
                while chunk := await file.read(CHUNK_SIZE):
                    await f.write(chunk)

            file_url = b2_upload_file(local_file=filename, file_name=filename)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There was an error uploading the file"
        )
    
    return {"detail": f"Successfully uploaded {file.filename}", "file_url": file_url}
