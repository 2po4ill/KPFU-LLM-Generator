# Archive - Development Artifacts

This folder contains all the experimental files, test scripts, and development artifacts created during the project development process.

## 📁 Folder Structure

### **test-files/**
All test scripts and experimental code used during development:
- `test_*.py` - Various testing scripts
- `generate_*.py` - Generation test scripts  
- `debug_*.py` - Debug and troubleshooting scripts
- `validate_*.py` - Validation testing scripts
- `extract_*.py` - Data extraction utilities
- `manual_*.py` - Manual analysis scripts
- `compare_*.py` - Comparison testing scripts

### **experimental-prompts/**
Prompt engineering experiments and iterations:
- `*PROMPT*.txt` - Various prompt experiments
- `CHUNKED_*.txt` - Chunking approach experiments (abandoned)
- `toc_*.txt` - TOC processing experiments
- `*_response.txt` - LLM response samples

### **old-generations/**
Previous lecture generation attempts and results:
- `generated_lectures/` - First generation attempt (failed)
- `generated_lectures_v2/` - Second generation attempt (partial success)

Note: Final successful generation is in root `generated_lectures_with_offset/`

### **debug-files/**
Debug outputs, temporary files, and development artifacts:
- `*_lecture_*.md` - Individual lecture test outputs
- `debug_*.md` - Debug analysis files
- `DEEPSEEK_*.md` - External API experiments (not used)
- `NEXT_STEPS.md` - Old planning documents
- `PROJECT_STATUS.md` - Outdated status files

## 🗑️ Safe to Delete

Most files in this archive are safe to delete if disk space is needed:

### **Keep for Reference**:
- `test-files/generate_full_course_v2.py` - Final working course generator
- `test-files/validate_content_accuracy.py` - Accuracy validation script
- `test-files/compare_multi_book_lectures.py` - Multi-book testing (in progress)

### **Can Delete**:
- All `experimental-prompts/` files (experiments completed)
- All `old-generations/` files (superseded by final version)
- Most `debug-files/` (temporary analysis)
- External API experiments (`DEEPSEEK_*`, etc.)

## 📊 Development Timeline

This archive represents approximately 3 weeks of intensive development:

1. **Week 1**: Initial architecture, chunking experiments (failed)
2. **Week 2**: TOC-based approach, prompt engineering
3. **Week 3**: Page offset fix (breakthrough), final system

## 🎯 Key Learnings Preserved

The archive preserves important development learnings:

1. **Why chunking failed** - See `experimental-prompts/CHUNKED_*.txt`
2. **Prompt engineering evolution** - See various `*PROMPT*.txt` files
3. **Model comparison process** - See `debug-files/DEEPSEEK_*.md`
4. **Validation methodology development** - See `test-files/validate_*.py`

## 🔄 Reusable Components

Some archived components may be useful for future development:

- **Multi-book testing framework** - `test-files/compare_multi_book_lectures.py`
- **Performance benchmarking** - `test-files/test_generation_timing.py`
- **Accuracy validation tools** - `test-files/validate_*.py`
- **PDF processing utilities** - `test-files/test_pdf_processing.py`

---

**Archive Created**: February 25, 2026  
**Total Files Archived**: ~50+ development artifacts  
**Disk Space**: ~15MB of experimental code and documentation