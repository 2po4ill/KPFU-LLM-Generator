# Retrieval Benchmark Phase 1 (Precision-First, Single Theme)

Theme: `RSA`  
Book: `mzi.pdf` (`mzi_linux_sec`)  
Pipeline mode used for retrieval benchmark: `chunk_rag_direct`

## Gold Intent (Phase 1)

- Must include: `rsa`, `открыт`, `закрыт`, `ключ`, `модул`, `шифр`, `теорема эйлера`, `ферма`
- Must exclude: `oop`, `наследован`, `инкапсуляц`, `полиморф`, `html`, `css`, `javascript`

## Variant Runs

- Baseline  
  - run dir: `generated_package_smoke/20260429_174812_chunk_rag_direct`  
  - settings: `top_k=6`, `threshold=-1`, `mmr=off`, `page_top_k=20`
- Variant A (strict threshold + lower top-k)  
  - run dir: `generated_package_smoke/20260429_175020_chunk_rag_direct`  
  - settings: `top_k=4`, `threshold=0.55`, `mmr=off`, `page_top_k=20`
- Variant B (threshold + MMR diversity)  
  - run dir: `generated_package_smoke/20260429_175224_chunk_rag_direct`  
  - settings: `top_k=6`, `threshold=0.45`, `mmr_lambda=0.65`, `page_top_k=20`
- Variant C (threshold + MMR + tighter page cap)  
  - run dir: `generated_package_smoke/20260429_175458_chunk_rag_direct`  
  - settings: `top_k=5`, `threshold=0.50`, `mmr_lambda=0.60`, `page_top_k=12`

## Retrieval Precision Diagnostics

- Baseline  
  - off-theme chunk rate: `0.1667`  
  - redundancy ratio: `0.0`  
  - effective evidence density: `0.8333`
- Variant A  
  - off-theme chunk rate: `0.0`  
  - redundancy ratio: `0.0`  
  - effective evidence density: `1.0`
- Variant B  
  - off-theme chunk rate: `0.1667`  
  - redundancy ratio: `0.0`  
  - effective evidence density: `0.8333`
- Variant C  
  - off-theme chunk rate: `0.2`  
  - redundancy ratio: `0.0`  
  - effective evidence density: `0.8`

## Cost/Latency Indicators

- Baseline: total tokens `15205`, elapsed `141.13s`
- Variant A: total tokens `11466`, elapsed `120.31s`
- Variant B: total tokens `11851`, elapsed `110.66s`
- Variant C: total tokens `12206`, elapsed `123.57s`

## Recommendation (Precision-First Default)

Choose **Variant A** as the precision-first default for phase 1:

- `CHUNK_RAG_TOP_K_CHUNKS_PER_CONCEPT=4`
- `CHUNK_RAG_SIMILARITY_THRESHOLD=0.55`
- `CHUNK_RAG_MMR_LAMBDA=0` (disabled in precision-first default)
- `SEMANTIC_PAGE_RERANK_TOP_K=20`

Reason:

- Best measured precision (`off_theme=0.0`, `evidence_density=1.0`)
- Lower token consumption than baseline
- No increase in redundancy

## Exported Retrieval Artifacts

Each run now includes:

- `retrieval_artifacts.json` (selected pages/chunks, ranks, similarities, text)
- `retrieval_diagnostics.json` (off-theme rate, redundancy ratio, evidence density, gold intent used)

## Phase 2 Next Step

After locking precision defaults, run a coverage-focused benchmark:

- add facet coverage metric and section diversity checks
- allow controlled increase to `top_k` and optional MMR only if precision remains within target
