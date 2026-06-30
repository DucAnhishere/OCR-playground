# ADR 0002: Supabase Storage Is Best-Effort

## Status

Accepted

## Context

OCR can run entirely with uploaded bytes and base64 images, but the previous pipeline failed before OCR if Supabase upload failed. That made an optional persistence feature part of the critical recognition path.

## Decision

Supabase uploads are best-effort by default. If storage is disabled or upload fails, the BFF logs a warning, returns base64 fallback data, and includes `metadata.storage_status`.

`STORAGE_REQUIRED=true` is available for deployments that intentionally require persistence.

## Consequences

- Local development works without Supabase credentials.
- OCR availability is not tied to storage availability.
- Callers can inspect `metadata.storage_status` and `warnings` to detect degraded persistence.

