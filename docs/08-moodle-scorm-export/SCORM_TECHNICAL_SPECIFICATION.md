# SCORM Technical Specification for KPFU Course Export

**Date**: February 26, 2026  
**SCORM Version**: 1.2 (Primary), 2004 (Future)  
**Target Platform**: Moodle 3.x / 4.x

---

## 🎯 Overview

This document specifies the technical implementation for exporting KPFU-generated courses to SCORM-compliant packages that can be imported into Moodle LMS.

## 📋 SCORM Standards

### SCORM 1.2 (Primary Target)
- **Reason**: Widest compatibility with Moodle versions
- **Features**: Basic tracking, simple sequencing
- **Limitations**: Limited data model, no advanced sequencing

### SCORM 2004 (Future Enhancement)
- **Reason**: Advanced features, better tracking
- **Features**: Rich data model, complex sequencing, objectives
- **Limitations**: Less universal support

---

## 🏗️ Package Structure

### Required Files

```
course_package.zip
├── imsmanifest.xml          # SCORM manifest (REQUIRED)
├── adlcp_rootv1p2.xsd       # SCORM schema
├── ims_xml.xsd              # IMS schema
├── index.html               # Course entry point
├── lectures/                # Lecture content
├── labs/                    # Lab manuals
├── assessments/             # Quizzes and tests
├── assets/                  # CSS, JS, images
└── api/                     # SCORM API wrapper
```

## 📄 Manifest Structure (imsmanifest.xml)

### Minimal SCORM 1.2 Manifest

```xml
<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="KPFU_PYTHON_COURSE" version="1.0"
          xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
          xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd
                              http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
    
    <metadata>
        <schema>ADL SCORM</schema>
        <schemaversion>1.2</schemaversion>
    </metadata>
    
    <organizations default="KPFU_ORG">
        <organization identifier="KPFU_ORG">
            <title>Основы программирования на Python</title>
            
            <!-- Lecture 1 -->
            <item identifier="ITEM_001" identifierref="RES_001">
                <title>Лекция 1: Введение в Python</title>
            </item>
            
            <!-- Lab 1 -->
            <item identifier="ITEM_002" identifierref="RES_002">
                <title>Лабораторная работа 1</title>
            </item>
            
            <!-- Quiz 1 -->
            <item identifier="ITEM_003" identifierref="RES_003">
                <title>Тест 1</title>
            </item>
            
            <!-- More items... -->
        </organization>
    </organizations>
    
    <resources>
        <resource identifier="RES_001" type="webcontent" 
                  adlcp:scormtype="sco" href="lectures/lecture_01.html">
            <file href="lectures/lecture_01.html"/>
            <file href="assets/css/style.css"/>
            <file href="api/scorm_api.js"/>
        </resource>
        
        <!-- More resources... -->
    </resources>
</manifest>
```

## 🔧 Python Implementation

### SCORM Exporter Class

```python
from pathlib import Path
from typing import List, Dict
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class SCORMMetadata:
    identifier: str
    title: str
    description: str
    version: str = "1.0"
    schema: str = "ADL SCORM"
    schema_version: str = "1.2"

class SCORMExporter:
    """Export course content to SCORM 1.2 package"""
    
    def __init__(self):
        self.namespaces = {
            '': 'http://www.imsproject.org/xsd/imscp_rootv1p1p2',
            'adlcp': 'http://www.adlnet.org/xsd/adlcp_rootv1p2',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }
    
    def export_course(self, course: CompleteCourse, output_path: Path) -> Path:
        """
        Export complete course to SCORM package
        
        Args:
            course: Complete course with all materials
            output_path: Path for output .zip file
            
        Returns:
            Path to created SCORM package
        """
        # Create temporary directory for package contents
        temp_dir = Path("temp_scorm_package")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Generate manifest
            manifest = self.create_manifest(course)
            self.save_manifest(manifest, temp_dir / "imsmanifest.xml")
            
            # Convert content to HTML
            self.export_lectures(course.lectures, temp_dir / "lectures")
            self.export_labs(course.lab_manuals, temp_dir / "labs")
            self.export_assessments(course.assessment_materials, temp_dir / "assessments")
            
            # Copy assets
            self.copy_assets(temp_dir / "assets")
            self.copy_scorm_api(temp_dir / "api")
            
            # Create index.html
            self.create_index(course, temp_dir / "index.html")
            
            # Package everything into .zip
            package_path = self.create_zip_package(temp_dir, output_path)
            
            return package_path
            
        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir)
```

## 📊 Moodle Integration

### Import Process
1. Login to Moodle as teacher/admin
2. Navigate to course
3. Turn editing on
4. Add activity → SCORM package
5. Upload .zip file
6. Configure settings
7. Save and display

### Moodle-Specific Considerations
- Maximum upload size (default 100MB)
- SCORM player settings
- Grade book integration
- Completion tracking
- Mobile app compatibility

---

**Document Version**: 1.0  
**Last Updated**: February 26, 2026
