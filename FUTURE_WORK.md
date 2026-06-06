# Future Work

## Retrieval Evaluations

Build a deterministic retrieval-only evaluation harness before making substantial retrieval or indexing changes.

Recommended first milestone:

- Add a version-controlled synthetic investor corpus with approximately 50-100 sources.
- Add approximately 30 manually reviewed queries with graded source relevance labels.
- Cover exact lookup, paraphrases, lexical distractors, folders, authors, dates, recency, thread scope, articles, and multi-source questions.
- Evaluate deduplicated source-level results rather than raw chunks.
- Report Hit Rate@1, MRR@10, nDCG@5, Recall@5, Recall@10, and Precision@5 globally and by query category.
- Add a CLI runner that uses the real `retrieve_chunks()` path and writes machine-readable results.
- Store a reviewed baseline and initially publish regressions as a non-blocking CI report.
- Make thresholds blocking after the dataset and baseline are trusted.

Suggested structure:

```text
apps/api/evals/retrieval/
  corpus.json
  queries.json
  baselines.json
  README.md
apps/api/app/evals/retrieval.py
apps/api/scripts/run_retrieval_eval.py
apps/api/tests/test_retrieval_eval.py
```

Keep retrieval evaluation separate from later end-to-end generation evaluation so failures can be attributed correctly.
Generation evaluation should eventually cover citation correctness, citation completeness, unsupported claims, answer relevance,
and appropriate refusal when evidence is insufficient.
