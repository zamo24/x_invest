# ADR 001: Multi-Tenant Storage Strategy

- Status: Accepted
- Date: 2026-06-06

## Context

Investor Research Copilot currently stores all users in one PostgreSQL database using shared tables with a `user_id`
tenant key. PostgreSQL is also the vector store through pgvector.

The primary scaling concern is not shared PostgreSQL by itself. It is maintaining tenant isolation and efficient
tenant-filtered vector retrieval as the total number of chunks and users grows. A global approximate-nearest-neighbor
index can become less effective when each query needs only one user's small subset of the indexed rows.

## Decision

Keep the current shared PostgreSQL database and shared-table model for now.

Tenant-owned records must continue to include `user_id`, and all application queries must explicitly constrain access
by the authenticated user's ID. PostgreSQL remains the system of record and vector store until production measurements
show that this architecture is the limiting factor.

The expected scaling path is:

1. Shared PostgreSQL with exact vector retrieval.
2. Shared PostgreSQL with HNSW, tenant isolation safeguards, and retrieval monitoring.
3. Hash-partition high-volume tables by `user_id`, beginning with `chunks`.
4. Route users to multiple PostgreSQL shards when one database server approaches operational limits.
5. Use dedicated databases or a specialized vector store only for tenants or workloads that justify the complexity.

## Why This Model

The current model provides:

- Simple migrations, backups, transactions, and connection pooling.
- Low operational cost and infrastructure complexity.
- Normal foreign keys and joins across user-owned data.
- Straightforward deletion and data lifecycle management.
- A clear path to partitioning and sharding by the existing `user_id` tenant key.

Moving immediately to database-per-user, application-level sharding, or a separate vector store would add substantial
operational and consistency complexity without evidence that the current database is near its limits.

## Near-Term Safeguards

- Ensure every tenant-owned table contains `user_id`, including future high-volume tables.
- Keep explicit `user_id` predicates in every tenant-owned query.
- Add composite indexes beginning with `user_id` for common access patterns.
- Consider PostgreSQL Row-Level Security as defense in depth. Request-serving roles must not bypass RLS.
- Add per-user storage, chunk-count, ingestion-rate, retrieval-latency, and query-volume metrics.
- Build the retrieval evaluation harness documented in `FUTURE_WORK.md` before adding approximate vector indexes.
- Compare approximate retrieval against exact search regularly after HNSW is introduced.
- Avoid schema assumptions that would prevent moving one user's data to another shard.

## Scaling Triggers

Do not change architecture based only on total user count. Reevaluate when measurements show one or more of:

- Tenant-filtered vector recall or result counts degrade with a global HNSW index.
- p95 retrieval latency exceeds the product target after query and index tuning.
- HNSW index memory, rebuild time, write throughput, or vacuum behavior becomes operationally unacceptable.
- Database CPU, storage, I/O, or connection pressure approaches sustained capacity limits.
- A small number of large tenants materially affect other users.
- Enterprise requirements demand dedicated infrastructure or tenant-specific restore operations.

## Next Scaling Step

The preferred first structural change is hash partitioning `chunks` by `user_id` into a fixed number of partitions,
such as 16, 32, or 64. Each partition can have its own HNSW index, improving memory locality and reducing the number
of irrelevant tenants searched by each index.

Do not create one partition per user. A fixed number of hash buckets avoids excessive table and index management.

Additional high-volume tables can be partitioned later if measurements justify it. Smaller relational tables should
remain shared unless they independently become bottlenecks.

## Alternatives Considered

### Application-Level PostgreSQL Sharding

Map each user to a database shard and route every request accordingly. This provides horizontal scaling and stronger
isolation, but complicates migrations, backups, monitoring, cross-shard operations, and tenant movement. Adopt only
after partitioned PostgreSQL no longer meets measured requirements.

### Database Per Tenant

Provides strong isolation and tenant-specific restore operations, but is operationally inefficient for a large B2C
user base. Reserve for enterprise tenants with contractual isolation requirements.

### Separate Vector Database

Can provide specialized filtered ANN and independent scaling, but creates dual-write consistency, deletion, recovery,
and metadata duplication concerns. Adopt only if pgvector is demonstrated to be the bottleneck through evaluation and
load testing.

### Distributed PostgreSQL

Systems such as Citus can route tenant-scoped queries by tenant ID. This is a possible future implementation of the
sharding stage, but is unnecessary at the current scale.

## Consequences

- Shared PostgreSQL remains the production architecture.
- Engineering effort should focus on tenant isolation, observability, retrieval evaluation, and measured tuning.
- Future partitioning and sharding work should use `user_id` as the routing key.
- Infrastructure changes require benchmark evidence showing a meaningful benefit over the current model.
