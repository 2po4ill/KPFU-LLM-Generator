"""
Configuration settings for KPFU LLM Generator
"""

import os
from typing import Optional, List

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://kpfu_user:kpfu_password@localhost:5432/kpfu_generator"
    )
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # ChromaDB
    chromadb_url: str = os.getenv("CHROMADB_URL", "http://localhost:8000")
    
    # Ollama
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    
    # Model settings
    # Cloud via Ollama (ollama signin). Local fallback: llama3.1:8b
    llm_model: str = os.getenv("LLM_MODEL", "gpt-oss:120b-cloud")
    llm_num_ctx: int = int(os.getenv("LLM_NUM_CTX", "8192"))
    # First /generate in _load_llm_model can take a long time on cold start; skip for fast local runs.
    llm_skip_warmup: bool = os.getenv("LLM_SKIP_WARMUP", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    # 0 = no limit. Set e.g. 120 to abort warmup if Ollama hangs.
    llm_warmup_timeout_seconds: float = float(os.getenv("LLM_WARMUP_TIMEOUT_SECONDS", "0"))
    # Post-generation LLM pass for lab + self-check only (grounded on ConceptCards; lecture excluded).
    # Default off: human-in-loop + full claims in comments is often enough; set true for extra guardrails.
    package_artifact_llm_verify: bool = os.getenv(
        "PACKAGE_ARTIFACT_LLM_VERIFY", "false"
    ).lower() in ("1", "true", "yes")
    # Lecture is always generated; lab / self-check / Moodle / PPTX are optional.
    package_lab_enabled: bool = os.getenv(
        "PACKAGE_LAB_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    package_selfcheck_enabled: bool = os.getenv(
        "PACKAGE_SELFCHECK_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    # Optional Moodle questions XML from self-check (requires self-check content).
    package_moodle_xml_enabled: bool = os.getenv(
        "PACKAGE_MOODLE_XML_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    # Optional PPTX slides from lecture (figures from PDF; Mermaid only when explicitly requested).
    package_pptx_enabled: bool = os.getenv(
        "PACKAGE_PPTX_ENABLED", "false"
    ).lower() in ("1", "true", "yes")
    package_pptx_max_slides: int = int(os.getenv("PACKAGE_PPTX_MAX_SLIDES", "18"))
    package_pptx_attach_page_images: bool = os.getenv(
        "PACKAGE_PPTX_ATTACH_PAGE_IMAGES", "false"
    ).lower() in ("1", "true", "yes")
    # Optional .pptx with layouts: Титульный / Только текст / Текст с изображением.
    # Default: app/presentation/templates/simple_ru.pptx if present.
    package_pptx_template_path: str = os.getenv("PACKAGE_PPTX_TEMPLATE_PATH", "")
    package_pptx_layout_title: str = os.getenv("PACKAGE_PPTX_LAYOUT_TITLE", "TITLE")
    package_pptx_layout_content: str = os.getenv(
        "PACKAGE_PPTX_LAYOUT_CONTENT", "TITLE_AND_BODY"
    )
    package_pptx_layout_content_image: str = os.getenv(
        "PACKAGE_PPTX_LAYOUT_CONTENT_IMAGE", "Два объекта"
    )
    package_pptx_max_bullets: int = int(os.getenv("PACKAGE_PPTX_MAX_BULLETS", "4"))
    package_pptx_max_bullet_chars: int = int(os.getenv("PACKAGE_PPTX_MAX_BULLET_CHARS", "140"))
    package_pptx_title_max_chars: int = int(os.getenv("PACKAGE_PPTX_TITLE_MAX_CHARS", "72"))
    package_pptx_bullet_font_pt: int = int(os.getenv("PACKAGE_PPTX_BULLET_FONT_PT", "17"))
    package_pptx_content_title_font_pt: int = int(
        os.getenv("PACKAGE_PPTX_CONTENT_TITLE_FONT_PT", "24")
    )
    # Mermaid only when slide planner sets image.strategy=mermaid (no auto-fallback).
    package_pptx_mermaid_for_algorithms: bool = os.getenv(
        "PACKAGE_PPTX_MERMAID_FOR_ALGORITHMS", "false"
    ).lower() in ("1", "true", "yes")
    # Remove HTML comments (CONCEPT_ORIGIN) from lecture shown to students / PPTX source.
    lecture_strip_html_comments: bool = os.getenv(
        "LECTURE_STRIP_HTML_COMMENTS", "true"
    ).lower() in ("1", "true", "yes")
    # Russian-specific embedding model for better semantic matching
    # Options: cointegrated/rubert-tiny2 (111MB), ai-forever/sbert_large_nlu_ru (1.1GB)
    embedding_model: str = "cointegrated/rubert-tiny2"
    
    # Memory limits (in MB)
    max_llm_memory: int = 4700  # 4.7GB for Llama 3.1 8B
    max_embedding_memory: int = 118  # 118MB for sentence transformer
    max_context_tokens: int = 5000
    
    # Cache settings
    cache_ttl_seconds: int = 3600  # 1 hour
    max_cache_size_mb: int = 500
    
    # Performance settings
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 300  # 5 minutes
    
    # File upload settings
    max_file_size_mb: int = 50
    allowed_file_types: str = ".pdf,.docx,.xlsx"
    
    # Development settings
    debug: bool = False
    log_level: str = "INFO"
    
    # Telegram Bot
    telegram_bot_token: Optional[str] = None

    # Security / production hardening (optional)
    # If API_KEY is not set, endpoints are left open (useful for local diploma testing).
    api_key: Optional[str] = os.getenv("API_KEY")
    enable_rate_limit: bool = os.getenv("ENABLE_RATE_LIMIT", "false").lower() == "true"
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

    # RPD source download (direct PDF) — content-addressed storage under uploaded_books_dir
    uploaded_books_dir: str = os.getenv("UPLOADED_BOOKS_DIR", "uploaded_books")
    books_cache_dir: str = os.getenv("BOOKS_CACHE_DIR", "app/cache/books")
    source_download_max_bytes: int = int(os.getenv("SOURCE_DOWNLOAD_MAX_MB", "80")) * 1024 * 1024
    source_download_timeout_seconds: float = float(os.getenv("SOURCE_DOWNLOAD_TIMEOUT", "120"))
    source_download_user_agent: str = os.getenv(
        "SOURCE_DOWNLOAD_USER_AGENT",
        "KPFU-RPD-Generator/1.0",
    )
    
    # TOC-driven page selection controls
    # 0 means "no cap".
    toc_page_top_k_per_book: int = int(os.getenv("TOC_PAGE_TOP_K_PER_BOOK", "0"))
    
    # Semantic reranking of TOC-selected pages
    # If enabled, pages are reranked by embedding similarity to theme.
    semantic_page_rerank_enabled: bool = os.getenv(
        "SEMANTIC_PAGE_RERANK_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    # 0 means keep all pages after rerank ordering.
    semantic_page_rerank_top_k: int = int(os.getenv("SEMANTIC_PAGE_RERANK_TOP_K", "20"))
    
    # Step2 experiment mode:
    # - "claims": concept -> claim extraction -> elaboration (current default)
    # - "chunk_rag": concept -> chunk retrieval -> elaboration
    # - "chunk_rag_direct": theme -> chunk retrieval (no concept extraction) -> elaboration
    # - "facet_rag": facet extraction -> facet retrieval -> section elaboration
    pipeline_mode: str = os.getenv("PIPELINE_MODE", "claims")
    chunk_rag_chunk_size_chars: int = int(os.getenv("CHUNK_RAG_CHUNK_SIZE_CHARS", "900"))
    chunk_rag_overlap_chars: int = int(os.getenv("CHUNK_RAG_OVERLAP_CHARS", "120"))
    chunk_rag_top_k_chunks_per_concept: int = int(os.getenv("CHUNK_RAG_TOP_K_CHUNKS_PER_CONCEPT", "6"))
    # Optional similarity floor for chunk selection in chunk-rag modes.
    # -1 disables filtering. Typical retrieval band for MiniLM/rubert-tiny2: 0.28–0.38.
    chunk_rag_similarity_threshold: float = float(os.getenv("CHUNK_RAG_SIMILARITY_THRESHOLD", "0.30"))
    # Optional MMR diversity: 0 disables, values in (0,1] enable MMR reranking.
    # Typical: 0.5-0.8 where higher favors relevance over diversity.
    chunk_rag_mmr_lambda: float = float(os.getenv("CHUNK_RAG_MMR_LAMBDA", "0"))
    # Optional cap for number of ranked candidates retained in debug artifacts per concept.
    chunk_rag_debug_ranked_cap: int = int(os.getenv("CHUNK_RAG_DEBUG_RANKED_CAP", "30"))
    # Legacy fixed facets count fallback for direct/facet rag mode.
    chunk_rag_direct_facets_count: int = int(os.getenv("CHUNK_RAG_DIRECT_FACETS_COUNT", "4"))
    # Adaptive facet bounds (coverage-driven lower bound, budget-driven upper bound).
    chunk_rag_facet_min_count: int = int(os.getenv("CHUNK_RAG_FACET_MIN_COUNT", "3"))
    chunk_rag_facet_max_count: int = int(os.getenv("CHUNK_RAG_FACET_MAX_COUNT", "9"))
    # Facet-to-theme semantic relevance floor. If facets are below this score, they are dropped.
    # Negative values disable filtering.
    chunk_rag_facet_theme_threshold: float = float(os.getenv("CHUNK_RAG_FACET_THEME_THRESHOLD", "0.22"))
    # Drop facet titles that are mostly Latin (e.g. English headings from source noise).
    chunk_rag_facet_require_russian: bool = os.getenv(
        "CHUNK_RAG_FACET_REQUIRE_RUSSIAN", "true"
    ).lower() in ("1", "true", "yes")
    # Minimum words in facet section body (after ### heading); expand pass if shorter.
    chunk_rag_facet_section_min_words: int = int(
        os.getenv("CHUNK_RAG_FACET_SECTION_MIN_WORDS", "120")
    )
    # Cap facet min_words vs available claim text to reduce hallucinated padding.
    chunk_rag_facet_evidence_word_cap_ratio: float = float(
        os.getenv("CHUNK_RAG_FACET_EVIDENCE_WORD_CAP_RATIO", "1.35")
    )
    # Per-facet section: sentence-level hallucination rate vs retrieved claims.
    facet_section_hallucination_enabled: bool = os.getenv(
        "FACET_SECTION_HALLUCINATION_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    # Max share of unsupported sentences (1 - grounded_rate). Regenerate if exceeded.
    # RAG faithfulness targets often aim for >=75% grounded (~0.25 max unsupported).
    facet_section_hallucination_threshold: float = float(
        os.getenv("FACET_SECTION_HALLUCINATION_THRESHOLD", "0.25")
    )
    # Lexical (Jaccard) floor per sentence vs claim chunk.
    facet_section_hallucination_similarity_min: float = float(
        os.getenv("FACET_SECTION_HALLUCINATION_SIMILARITY_MIN", "0.07")
    )
    # Grounding scorer: jaccard | embedding | hybrid (supported if either passes).
    facet_section_hallucination_grounding_mode: str = os.getenv(
        "FACET_SECTION_HALLUCINATION_GROUNDING_MODE", "hybrid"
    ).strip().lower()
    # Cosine(sentence, claim) floor for embedding/hybrid (tune per EMBEDDING_MODEL).
    facet_section_hallucination_embedding_min: float = float(
        os.getenv("FACET_SECTION_HALLUCINATION_EMBEDDING_MIN", "0.52")
    )
    facet_section_hallucination_min_sentences: int = int(
        os.getenv("FACET_SECTION_HALLUCINATION_MIN_SENTENCES", "4")
    )
    facet_section_hallucination_max_regenerations: int = int(
        os.getenv("FACET_SECTION_HALLUCINATION_MAX_REGENERATIONS", "2")
    )
    # Regen: json (hints only) | evidence_locked | adaptive (locked when rate>0.5).
    facet_section_hallucination_regen_strategy: str = os.getenv(
        "FACET_SECTION_HALLUCINATION_REGEN_STRATEGY", "adaptive"
    ).strip().lower()
    # Step3 lecture validation: claim supported if cosine(claim, page) exceeds this.
    package_validation_claim_similarity: float = float(
        os.getenv("PACKAGE_VALIDATION_CLAIM_SIMILARITY", "0.45")
    )
    # Run facets one-by-one while hallucination regen is on (avoids Ollama queue stalls).
    facet_section_serial_when_hallucination_check: bool = os.getenv(
        "FACET_SECTION_SERIAL_WHEN_HALLUCINATION_CHECK", "true"
    ).lower() in ("1", "true", "yes")
    facet_section_llm_timeout_seconds: float = float(
        os.getenv("FACET_SECTION_LLM_TIMEOUT_SECONDS", "180")
    )
    # Body budget is controlled strictly in TOKENS.
    # Default derives from 2500 words converted to tokens with a 1.6 multiplier.
    chunk_rag_body_target_tokens: int = int(os.getenv("CHUNK_RAG_BODY_TARGET_TOKENS", "4000"))
    # Hard stop to prevent overgrowth even if coverage keeps increasing.
    chunk_rag_body_max_tokens: int = int(os.getenv("CHUNK_RAG_BODY_MAX_TOKENS", "4600"))
    # Estimated generation budget spent per accepted facet section.
    chunk_rag_estimated_tokens_per_facet: int = int(os.getenv("CHUNK_RAG_ESTIMATED_TOKENS_PER_FACET", "520"))
    # Coverage-driven controls based on unique evidence chunks.
    chunk_rag_facet_coverage_min: float = float(os.getenv("CHUNK_RAG_FACET_COVERAGE_MIN", "0.75"))
    chunk_rag_facet_min_gain: float = float(os.getenv("CHUNK_RAG_FACET_MIN_GAIN", "0.06"))

    # Elaboration batching for cloud LLM throughput.
    elaboration_batch_size: int = int(os.getenv("ELABORATION_BATCH_SIZE", "4"))
    elaboration_parallel_batches: int = int(os.getenv("ELABORATION_PARALLEL_BATCHES", "4"))
    # In facet_rag mode, generate one section per facet and concatenate.
    facet_rag_section_per_facet: bool = os.getenv(
        "FACET_RAG_SECTION_PER_FACET", "true"
    ).lower() in ("1", "true", "yes")
    # Use RPD §4.2 subtopics (N.M) as facet headings when theme matches.
    facet_rag_prefer_rpd_subtopics: bool = os.getenv(
        "FACET_RAG_PREFER_RPD_SUBTOPICS", "true"
    ).lower() in ("1", "true", "yes")
    # If RPD subtopics < facet min count, append LLM facets (deduped).
    facet_rag_rpd_hybrid_llm_fill: bool = os.getenv(
        "FACET_RAG_RPD_HYBRID_LLM_FILL", "true"
    ).lower() in ("1", "true", "yes")

    # User-attached sources (short texts, priority RAG, bypass TOC)
    user_source_max_count: int = int(os.getenv("USER_SOURCE_MAX_COUNT", "8"))
    user_source_max_chars: int = int(os.getenv("USER_SOURCE_MAX_CHARS", "32000"))
    user_source_similarity_boost: float = float(os.getenv("USER_SOURCE_SIMILARITY_BOOST", "0.22"))
    user_source_reserved_chunks_per_concept: int = int(
        os.getenv("USER_SOURCE_RESERVED_CHUNKS_PER_CONCEPT", "4")
    )
    user_source_chunk_size_chars: int = int(os.getenv("USER_SOURCE_CHUNK_SIZE_CHARS", "1200"))
    user_source_chunk_overlap_chars: int = int(os.getenv("USER_SOURCE_CHUNK_OVERLAP_CHARS", "80"))
    
    @property
    def allowed_file_types_list(self) -> List[str]:
        """Get allowed file types as a list"""
        return [ext.strip() for ext in self.allowed_file_types.split(",")]
    
    model_config = {"env_file": ".env"}


# Global settings instance
settings = Settings()