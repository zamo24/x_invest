# X API Compliance Status

This document is a technical compliance-oriented design record, not a legal opinion or a guarantee
of compliance with X policies.

## Implemented Controls

- Official X API server-side retrieval and OAuth 2.0 PKCE.
- Minimum scopes: `tweet.read`, `users.read`, `bookmark.read`, `offline.access`.
- Encrypted access tokens, refresh tokens, and PKCE verifiers at rest.
- No X page DOM scraping, injected toolbar, reply automation, or article-body extraction.
- Per-user token use and tenant-scoped storage/retrieval.
- Usage accounting, configurable budgets, source verification metadata, and retry-safe revalidation.
- No model training or fine-tuning using X content.

## Explicitly Deferred Compliance Work

This phase preserves immutable historical X content. X content deletion and modification events are
not propagated through historical thread snapshots, historical embeddings, or persisted chat
citations. Disconnecting X deletes tokens but preserves the saved library and historical records.

The system must **not** be described as fully compliant with X policies until legal review and
written X approval confirm this retention model. A future lifecycle must evaluate deletion
propagation, modification propagation, compliance streams or equivalent mechanisms, embedding
deletion, citation treatment, backups, and retention periods.

## Approval Gates

Production launch requires:

1. X developer account, project, access tier, OAuth configuration, and endpoint access approval.
2. Written X confirmation that the product use case and historical retention model are permitted.
3. Legal review of X Developer Policy, Developer Agreement, privacy disclosures, terms, subprocessors,
   model-provider processing, and applicable privacy/consumer laws.
4. Security review of token encryption keys, secrets rotation, access controls, incident response,
   logs, backups, and production scheduling.
5. Billing and rate-limit review for bookmark sync, post lookup, and conversation search.

## Official References

- https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code
- https://docs.x.com/x-api/posts/lookup/introduction
- https://docs.x.com/x-api/posts/bookmarks/introduction
- https://docs.x.com/x-api/fundamentals/conversation-id
- https://docs.x.com/developer-terms/policy
- https://docs.x.com/x-api/fundamentals/post-cap
