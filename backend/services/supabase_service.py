import httpx
from const import SUPABASE_URL, SUPABASE_KEY, SUPABASE_BUCKET
from exceptions import SupabaseUploadError


async def upload_to_supabase(client: httpx.AsyncClient, file_bytes: bytes, filename: str, content_type: str = "image/jpeg") -> str:
    url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
        "Content-Type": content_type
    }
    resp = await client.post(url, content=file_bytes, headers=headers)
    if resp.status_code == 200:
        return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
    else:
        raise SupabaseUploadError(
            status_code=resp.status_code,
            detail=resp.text
        )

