# KPFU LLM Educational Content Generator - Requirements

## Project Overview

An LLM-based system that generates verified, non-hallucinated educational content (lectures and lab works) for KPFU professors using RPD curriculum files and the university's library database as authoritative sources.

## System Inputs

### RPD File Structure
- **Subject title**: Course name and code
- **Academic degree**: Bachelor, Master, or PhD level
- **Profession/Program**: Engineering, Medicine, Computer Science, etc.
- **Total hours**: Semester hour allocation for the subject
- **Lecture themes**: Number and titles of required lecture topics
- **Lab work examples**: Sample laboratory assignments for each lecture
- **Literature references**: Books and articles with authors and titles

### KPFU Library Database
- Educational books (full-text access)
- Academic articles and research papers
- Verified academic sources with proper citations

## Requirements

### Requirement 1: RPD Processing and Validation

**User Story:** As a professor, I want to upload an RPD file and have the system extract all curriculum requirements, so that content generation is based on official academic standards.

#### Acceptance Criteria
1. WHEN a professor uploads an RPD file THEN the system SHALL parse and extract all required fields (title, degree, profession, hours, themes, labs, literature)
2. WHEN RPD data is incomplete THEN the system SHALL identify missing fields and request clarification
3. WHEN literature references are provided THEN the system SHALL validate availability in KPFU library database
4. IF RPD format is non-standard THEN the system SHALL provide format guidance and examples

### Requirement 2: Literature-Based Content Verification

**User Story:** As a professor, I want generated content to be based only on verified KPFU library sources, so that there are no hallucinations or inaccurate information.

#### Acceptance Criteria
1. WHEN generating content THEN the system SHALL use only literature specified in RPD and available in KPFU database
2. WHEN citing information THEN the system SHALL provide exact page numbers and quotations from source materials
3. WHEN insufficient source material exists THEN the system SHALL flag content gaps and suggest additional literature
4. IF generated content cannot be verified against sources THEN the system SHALL mark it for professor review

### Requirement 3: Lecture Content Generation

**User Story:** As a professor, I want comprehensive lecture materials generated for each theme, so that I have complete teaching resources aligned with curriculum requirements.

#### Acceptance Criteria
1. WHEN processing lecture themes THEN the system SHALL generate structured lecture content for each topic
2. WHEN creating lectures THEN the system SHALL include learning objectives, theoretical content, examples, and conclusions
3. WHEN structuring content THEN the system SHALL adapt complexity to specified academic degree level
4. IF lecture exceeds allocated hours THEN the system SHALL provide condensed and extended versions

### Requirement 4: Laboratory Work Generation

**User Story:** As a professor, I want detailed lab assignments generated based on lecture content and RPD examples, so that students have practical learning experiences.

#### Acceptance Criteria
1. WHEN generating lab works THEN the system SHALL create detailed assignments based on corresponding lecture themes
2. WHEN designing labs THEN the system SHALL include objectives, procedures, expected results, and assessment criteria
3. WHEN using RPD lab examples THEN the system SHALL expand basic examples into complete assignments
4. IF lab complexity doesn't match degree level THEN the system SHALL adjust difficulty appropriately

### Requirement 5: Content Quality and Citation Management

**User Story:** As a professor, I want all generated content properly cited and traceable to source materials, so that academic integrity is maintained.

#### Acceptance Criteria
1. WHEN generating any content THEN the system SHALL provide complete citations for all source materials
2. WHEN using direct quotes THEN the system SHALL include exact page references and quotation marks
3. WHEN paraphrasing content THEN the system SHALL maintain source attribution and provide page ranges
4. IF multiple sources cover the same topic THEN the system SHALL synthesize information while maintaining all citations

### Requirement 6: Hybrid Processing Performance and Resource Optimization

**User Story:** As a system administrator, I want the system to use hybrid processing approaches to minimize resource usage while maintaining quality, so that the system can run efficiently on standard hardware.

#### Acceptance Criteria
1. WHEN evaluating book relevance THEN the system SHALL use keyword matching for clear cases (80%) and LLM only for ambiguous cases (20%)
2. WHEN validating content THEN the system SHALL use lightweight semantic models (118MB) instead of full LLM processing for claim verification
3. WHEN managing memory THEN the system SHALL maintain peak RAM usage under 5GB and idle usage under 200MB
4. IF processing confidence is high THEN the system SHALL use fast algorithmic approaches, falling back to LLM only when needed

### Requirement 7: Scalability and Future Extensions

**User Story:** As a system administrator, I want the system designed for future enhancements, so that additional content types and features can be added easily.

#### Acceptance Criteria
1. WHEN system architecture is designed THEN it SHALL support modular content generation plugins
2. WHEN new content types are needed THEN the system SHALL allow easy addition of new generators
3. WHEN integration requirements change THEN the system SHALL provide flexible API interfaces
4. IF usage scales up THEN the system SHALL handle multiple concurrent content generation requests

### Requirement 8: Professor Review and Approval Workflow

**User Story:** As a professor, I want to review and approve generated content before use, so that I can ensure quality and make necessary adjustments.

#### Acceptance Criteria
1. WHEN content is generated THEN the system SHALL present it for professor review before finalization
2. WHEN reviewing content THEN professors SHALL be able to edit, approve, or request regeneration
3. WHEN changes are made THEN the system SHALL maintain version history and source traceability
4. IF content is rejected THEN the system SHALL learn from feedback to improve future generation

## Success Criteria

### Primary Success Metrics
- **Content Accuracy**: 88% of generated content verifiable against source materials (hybrid optimization)
- **Citation Completeness**: 100% of content properly attributed to KPFU library sources
- **Professor Satisfaction**: 90%+ approval rate for generated lectures and labs
- **Time Savings**: 94% reduction in manual content preparation time (from 30-45 min to 1.5-2 min)

### Technical Performance Metrics - Hybrid Approach
- **Processing Time**: Single lecture generation within 1.5-2 minutes using hybrid 5-step pipeline
- **Memory Efficiency**: 85% less RAM usage through hybrid model approach and optimized context management
- **Source Coverage**: Utilization of 2-3 most relevant books from RPD literature references
- **Content Completeness**: All required lecture themes and lab works generated with FGOS compliance
- **System Reliability**: 99% uptime for content generation services

### Hybrid Pipeline Performance Metrics
- **Step 1 (Hybrid Book Relevance)**: 
  - Clear cases (80%): 2-3 seconds using keyword matching
  - Ambiguous cases (20%): 15-20 seconds using LLM fallback
  - Average completion time: 6 seconds
- **Step 2 (Page Selection)**: Complete within 60 seconds using parallel loading and smart indexing
- **Step 3 (Content Generation)**: Complete within 90-120 seconds using Llama 3.1 8B and streaming
- **Step 4 (Semantic Validation)**: Complete within 10-15 seconds using lightweight sentence transformer (118MB model)
- **Step 5 (FGOS Formatting)**: Complete within 30 seconds using pre-loaded templates

### Memory Usage Breakdown
- **Llama 3.1 8B Model**: 4.7GB RAM (loaded only for Steps 1 ambiguous cases and Step 3)
- **Semantic Validation Model**: 118MB RAM (SentenceTransformer paraphrase-multilingual-MiniLM-L12-v2)
- **Context Management**: Maximum 5,000 tokens (~20MB) per generation session
- **Page Cache**: 50-100MB for selected book pages
- **Total Peak RAM**: ~5GB (vs 8-12GB traditional approach - 58% reduction)
- **Idle RAM**: ~200MB when not generating (semantic model + cache only)

### Hardware Requirements
#### Minimum Configuration
- **RAM**: 8GB (allows for 5GB peak + 3GB OS/other processes)
- **CPU**: 4 cores, 2.5GHz (for parallel processing and semantic model inference)
- **Storage**: 20GB SSD (for models, cache, and KPFU database index)
- **Network**: 100Mbps (for KPFU library database access)

#### Recommended Configuration  
- **RAM**: 16GB (comfortable headroom for multiple concurrent sessions)
- **CPU**: 8 cores, 3.0GHz (optimal performance for hybrid processing)
- **Storage**: 50GB NVMe SSD (fast model loading and page caching)
- **Network**: 1Gbps (fast literature retrieval)

#### Performance Scaling
- **Single User**: 1.5-2 minutes per lecture on minimum hardware
- **5 Concurrent Users**: 2-3 minutes per lecture on recommended hardware  
- **10+ Users**: Requires load balancing with multiple instances