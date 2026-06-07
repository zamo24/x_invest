# Production Extension Configuration

The extension uses an expiring personal access token (PAT) to call the API directly. Production deployment requires
an HTTPS API origin and the published Chrome extension ID.

## Extension Behavior

- PAT and API base URL settings are stored in `chrome.storage.local`.
- Legacy settings found in `chrome.storage.sync` are migrated to local storage and removed from sync storage.
- Production API URLs must use HTTPS. HTTP is accepted only for `localhost`, `127.0.0.1`, and `[::1]`.
- The extension declares optional HTTPS host access and requests permission only for the exact configured API origin.
- Changing the configured production API origin removes the obsolete optional origin permission.
- The options page validates PAT shape and API URL before saving.
- **Test Connection** calls authenticated `GET /v1/me`, verifying the URL, origin permission, CORS policy, and PAT.
- Authentication, CORS, rate-limit, and network failures return actionable messages.

Chrome local storage is not an encrypted secrets vault. PAT expiry and revocation remain required controls. Use one PAT
per extension installation and rotate or revoke it when the installation is no longer trusted.

## API Production Environment

Find the published extension ID in the Chrome Web Store or `chrome://extensions`, then configure:

```dotenv
APP_ENV=production
CORS_ALLOW_ORIGINS=https://app.example.com
CORS_ALLOW_ORIGIN_REGEX=
CORS_EXTENSION_IDS=abcdefghijklmnopabcdefghijklmnop
```

Multiple published extension IDs can be comma-separated, for example during a controlled migration:

```dotenv
CORS_EXTENSION_IDS=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

Extension IDs must be exactly 32 lowercase letters from `a` through `z`.

In production, API startup rejects any non-empty `CORS_ALLOW_ORIGIN_REGEX`. This prevents accidentally allowing every
Chrome extension origin. Exact extension IDs are converted to origins such as:

```text
chrome-extension://abcdefghijklmnopabcdefghijklmnop
```

The compose files intentionally use `${CORS_ALLOW_ORIGIN_REGEX-default}` rather than `${...:-default}` so an explicitly
empty production value remains empty.

## Deployment Checklist

1. Deploy the API behind HTTPS.
2. Publish or package the Chrome extension and record its stable extension ID.
3. Configure exact `CORS_EXTENSION_IDS` and clear `CORS_ALLOW_ORIGIN_REGEX`.
4. Set `APP_ENV=production`; confirm the API starts successfully.
5. Create a dedicated expiring PAT from the dashboard.
6. Open extension options, enter the HTTPS API URL and PAT, then save.
7. Approve the exact API-origin permission prompt.
8. Run **Test Connection** and verify the authenticated identity.
9. Verify ingest, folder listing, and side-panel chat.
10. Revoke the PAT during uninstall, device loss, or suspected compromise.

## Local Development

Local development retains required access to:

```text
http://localhost:8000/*
http://127.0.0.1:8000/*
```

Development may retain:

```dotenv
APP_ENV=development
CORS_ALLOW_ORIGIN_REGEX=^chrome-extension://[a-z]{32}$
```

Do not use that broad extension-origin regex in production.
