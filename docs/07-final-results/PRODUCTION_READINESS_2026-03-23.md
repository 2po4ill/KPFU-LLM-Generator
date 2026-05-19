# Production Readiness Snapshot (2026-03-23)

## Scope

This snapshot reflects the current state after iterative fixes in runtime stability, TOC parsing, concept filtering, and lecture quality tuning (with switch to cloud LLM model).

## Current Model Strategy

- Local model baseline (`llama3.1:8b`) was useful for speed but showed quality drift outside IT-heavy topics.
- System is now configured to use cloud model via Ollama tag:
  - `LLM_MODEL=deepseek-v3.1:671b-cloud`
- This change improved cross-domain lecture quality (especially physics) and reduced hallucinated/irrelevant concept blocks.

## Production Score (0-10)

- **Overall production score: 8.1 / 10**

Breakdown:

- **Content quality (cross-domain potential): 8.0**
  - Strong improvement after cloud model switch.
  - Better relevance and structure in non-IT topics.
- **Prompt/pipeline robustness: 7.4**
  - Added post-dedup theme filtering, anti-duplicate logic, sibling-concept collapsing, and "conspect" style constraints.
  - Residual risk: overfitting prompt heuristics to one discipline.
- **Runtime stability: 8.0**
  - FastAPI and bot startup are stable.
  - Telegram failures are primarily due to regional proxy/network blocking (external factor); service works reliably with VPN.
- **Observability/debuggability: 8.1**
  - Useful stage logs (concept counts, filtering, batch execution).
  - Easier to diagnose "too many pages" vs "too few core concepts".
- **Operational readiness: 7.6**
  - Restart/run workflows are reliable.
  - Remaining ops gaps: dependency variance (`asyncpg` absent for full non-mock startup).

## Key Progress Since Iteration Start

1. **Critical error fixes**
   - Fixed `OptimizedGenerationResult` handling (`errors` vs `error`) in Telegram bot.
   - Added fallback-safe mock embedding loading when `SentenceTransformer` is unavailable.
   - Made optional `GPUtil` import safe for newer Python environments.

2. **TOC/selection improvements**
   - Improved regex TOC parsing robustness (case-insensitive matching, Unicode ellipsis support, section-symbol support).
   - Preserved "no hard section count limit" while improving downstream filtering quality.

3. **Core concept pipeline hardening**
   - Added post-dedup LLM theme filter with minimum-keep safety fallback.
   - Added anti-duplicate instructions and sibling concept suppression (family-based collapse).
   - Reduced concept elaboration batch size to improve focus (`2` concepts per batch).
   - Switched generation style from "spoken lecture script" to "written conspect".

4. **Delivery quality uplift**
   - Physics lecture outputs moved from low-relevance/noisy structure toward compact, domain-relevant, technically coherent notes.
   - Reduced meta-chat artifacts and non-Russian spillover.

## Current Risks

- **Residual sibling duplication** can still appear if variants are semantically close but lexically different.
- **Domain portability risk**: further aggressive prompt specialization for one subject may degrade others.
- **External network dependency**: Telegram API availability depends on regional connectivity/policy constraints; VPN path is required in blocked regions.
- **Environment variance**: app can run in mock mode if full infra deps are not present.

## Recommendation (Near-term)

- Keep cloud model as default for production-like generation quality.
- Avoid heavy subject-specific prompt branching for now.
- Continue with "light constraints + post-filtering" architecture.
- Add one lightweight post-processing sanitizer for final text:
  - remove conversational artifacts,
  - remove duplicated headings,
  - normalize formula/notation formatting.

## Release Assessment

- **Recommendation:** proceed with controlled production usage (beta/prod-lite), not full hard-SLA production yet.
- **Exit criteria for 8.5+/10:**
  1. One cross-domain regression pass (IT + physics + medicine + literature).
  2. Final output sanitizer and duplicate-heading guard in pipeline.

