# X API Operations

## Developer Console

Create a confidential Web App in the X Developer Console, enable OAuth 2.0 Authorization Code Flow
with PKCE, and configure an exact callback match for `X_REDIRECT_URI`.

Request only:

- `tweet.read`
- `users.read`
- `bookmark.read`
- `offline.access`

Do not enable bookmark-write or post-write permissions.

## Configuration

Required in production:

- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_REDIRECT_URI`
- `X_TOKEN_ENCRYPTION_KEY`

Controls:

- `X_API_BASE_URL=https://api.x.com`
- `X_CONTENT_REVALIDATE_HOURS=24`
- `X_MONTHLY_POST_READ_BUDGET`
- `X_BOOKMARK_SYNC_POST_LIMIT`
- `X_INTEGRATION_SETTINGS_URL`

## Routine Operations

Bookmark sync is the primary ingestion workflow. It paginates bookmarks, upserts through shared
normalization, conservatively retains locally saved posts removed from X, and maps X bookmark folders
to separately named local folders without overwriting user-authored folders.

Run source revalidation with:

```bash
python -m app.cli.revalidate_x
```

Schedule it according to `X_CONTENT_REVALIDATE_HOURS`. It batches up to 100 post IDs, updates current
content and embeddings, marks unavailable current sources, and preserves immutable snapshots and
persisted citations. The command is safe to retry.

Monitor `x_api_usage`, X rate-limit responses, and monthly budget errors. Bookmark folder endpoints
and conversation search availability may depend on the approved X access tier. Tests mock all X API
calls and do not require live credentials.
