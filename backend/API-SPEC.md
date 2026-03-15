# BPM Backend API Spec

Base path: `/api/v1`. Auth: Bearer token (JWT) for protected routes. All error responses include `request_id` when available.

---

## Auth (`/api/v1/auth`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register` | No | Register: body `SUserRegister` (username, email, password). Returns `SUserResponse`. |
| POST | `/login` | No | Login: body `SUserLogin` (email, password). Returns `STokenResponse` (access_token, refresh_token, token_type). |
| POST | `/refresh` | No | Refresh: body `SRefreshTokenRequest` (refresh_token). Returns new `STokenResponse`; old refresh token revoked. |
| POST | `/logout` | No | Logout: body `SRefreshTokenRequest`. Revokes the given refresh token. 204. |
| POST | `/logout_all` | Yes | Logout all devices: bumps user token_version and revokes all refresh tokens for user. 204. |

---

## Tracks (`/api/v1/tracks`)

All track routes except file-detail by ID require ownership (current user = track owner). File access for non-owners: only if track is PUBLIC and file_type is preview or image.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/draft` | Yes | Create draft track. Returns `STrackID` (track_id). |
| POST | `/{track_id}/submit` | Yes | Submit metadata for draft. Body `STrackUpload`: title, bpm, root_note, scale_type, tags[], genres[], moods[], instruments[], visibility, description?. Validators: root_note in ROOT_NOTES, scale_type in {major,minor}, 1–2 genres, ≥1 mood, ≥1 instrument, visibility in TrackVisibility. Returns `{ "message": "ok" }`. |
| GET | `` | Yes | List current user's tracks. Query: `STrackListFilters` — status[], bpm_min, bpm_max, root_note[], scale_type[], visibility[], limit (1–100, default 20), cursor. Returns `STrackListResponse` (items[], next_cursor). |
| GET | `/{track_id}` | Yes | Get full track for owner. Returns `STrackOwnerResponse` (metadata + files[] + tags, genres, moods, instruments). |
| POST | `/{track_id}/files/{file_type}` | Yes | Get presigned PUT URL for upload. file_type: preview \| main \| stems \| image. Body `STrackFileUploadRequest` (filename, size, mime). Validates mime/size per type. Returns `STrackFileUploadResponse` (uploadUrl). Client uploads to uploadUrl; MinIO emits event → worker processes. |
| GET | `/files/{track_file_id}` | Yes | Get track file metadata + presigned GET URL. Ownership: any file type. Non-owner: only if track PUBLIC and file_type preview or image. Returns `STrackFileDetailResponse` (id, track_id, file_type, status, storage_key, file_name, file_size?, duration_seconds?, mime_type?, created_at, url). |

**Track file types**: preview, main, stems, image. Required for track to become READY.

**Track status**: DRAFT → (submit + files) → PROCESSING (worker) → READY or FAILED.

**Pagination**: Cursor-based; pass `next_cursor` from previous response as `cursor` query param.

---

## Error responses

All error bodies use the key `"error"` for the code. Possible values: `auth_failed` (401), `email_taken` (400), `not_found` (404), `bad_request` (400), `validation_error` (422), `server_error` (500/503).

- **Domain (AppBaseException)**: `status_code` from exception, body `{ "error": "<error_code>", "message": "<message>", "request_id": "..." }`.
- **Validation (422)**: `{ "error": "validation_error", "message": "Validation failed", "details": [ { "field", "message", "type" } ], "request_id": "..." }`.
- **SQLAlchemy/Unhandled (500)**: `{ "error": "server_error", "message": "Internal server error", "request_id": "..." }`.
- **DB/Redis connection (503)**: `{ "error": "server_error", "message": "Service temporarily unavailable...", "request_id": "..." }`.

---

## Schemas (reference)

- **STrackUpload**: title, bpm, root_note, scale_type, tags, genres, moods, instruments, visibility, description?
- **STrackListFilters**: status, bpm_min, bpm_max, root_note, scale_type, visibility, limit, cursor
- **STrackListItem**: id, title, description, bpm, root_note, scale_type, status, visibility, created_at, updated_at
- **STrackOwnerResponse**: id, title, description, bpm, root_note, scale_type, status, visibility, files, created_at, updated_at, tags, genres, moods, instruments
- **STrackFileDetailResponse**: id, track_id, file_type, status, storage_key, file_name, file_size?, duration_seconds?, mime_type?, created_at, url

Dictionaries (Genre, Mood, Instrument) are referenced by **slug** in request body; backend resolves slugs via Redis to IDs.
