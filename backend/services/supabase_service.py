import httpx
from const import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET, STORAGE_TIMEOUT_SECONDS
from exceptions import SupabaseUploadError


def is_storage_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY and SUPABASE_BUCKET)


async def upload_to_supabase(client: httpx.AsyncClient, file_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    if not is_storage_configured():
        raise SupabaseUploadError(status_code=0, detail="Supabase storage is not configured")

    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": content_type
    }
    resp = await client.post(url, content=file_bytes, headers=headers, timeout=STORAGE_TIMEOUT_SECONDS)
    if resp.status_code == 200:
        return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
    else:
        raise SupabaseUploadError(
            status_code=resp.status_code,
            detail=resp.text
        )
