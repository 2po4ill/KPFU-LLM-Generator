 # Implementation Guide - Milestones 2-5

**Date**: February 26, 2026  
**Purpose**: Practical step-by-step guide for implementing each milestone  
**Audience**: Developers

---

## 🎯 Overview

This guide provides concrete, actionable steps to implement Milestones 2-5. Each milestone builds on the existing lecture generation system (Milestone 1 ✅).

**Key Principle**: Reuse the proven architecture from generator_v3.py:
- Same LLM model (llama3.1:8b)
- Same batched processing approach
- Same prompt engineering patterns
- Same validation methodology

---

## 📋 Milestone 2: Lab Manual Generation

**Goal**: Generate 12 lab manuals with practical exercises based on lecture content  
**Timeline**: 4-6 weeks  
**Estimated Effort**: 80-100 hours

### Step 1: Analyze Existing Lecture Structure (Week 1)

**What to do**:
1. Read all 12 generated lectures
2. Identify practical concepts in each lecture
3. Document patterns of code examples
4. List what makes a good lab exercise

**Deliverable**: Analysis document with:
- List of practical concepts per lecture
- Code example patterns
- Lab exercise structure template

**Files to examine**:
```python
# Read generated lectures
lectures = [
    "lecture_Работа_со_строками_batched.md",
    # ... other 11 lectures
]

# Extract patterns
for lecture in lectures:
    - What code examples exist?
    - What concepts need practice?
    - What exercises would reinforce learning?
```

---

### Step 2: Design Lab Manual Structure (Week 1)

**What to do**:
1. Define lab manual template
2. Create exercise format
3. Design assessment criteria structure

**Deliverable**: Template structure

```python
@dataclass
class LabManual:
    """Lab manual structure"""
    theme: str                          # Same as lecture theme
    learning_objectives: List[str]      # 3-5 objectives
    exercises: List[Exercise]           # 3-5 exercises
    assessment_criteria: AssessmentCriteria
    estimated_hours: int                # 2-4 hours
    
@dataclass
class Exercise:
    """Individual exercise"""
    number: int                         # Exercise 1, 2, 3...
    title: str                          # "Работа с индексацией строк"
    description: str                    # What to do
    starter_code: Optional[str]         # Template code
    instructions: List[str]             # Step-by-step
    expected_output: str                # What result should look like
    solution_code: str                  # Complete solution
    common_mistakes: List[str]          # What students often get wrong
    hints: List[str]                    # Help if stuck

@dataclass
class AssessmentCriteria:
    """How to grade the lab"""
    criteria: List[Criterion]
    total_points: int
    
@dataclass
class Criterion:
    name: str                           # "Правильность кода"
    points: int                         # 10 points
    description: str                    # What to check
```

---

### Step 3: Create Lab Manual Generator (Week 2-3)

**What to do**:
1. Create new file: `app/generation/lab_generator.py`
2. Implement extraction logic
3. Implement generation logic
4. Add validation

**Implementation**:

```python
# app/generation/lab_generator.py

import asyncio
from typing import List, Dict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class LabManualGenerator:
    """Generate lab manuals from lecture content"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
    
    async def generate_lab_manual(
        self, 
        lecture_content: str, 
        theme: str
    ) -> LabManual:
        """
        Generate complete lab manual from lecture
        
        Args:
            lecture_content: Generated lecture content
            theme: Lecture theme
            
        Returns:
            Complete lab manual with exercises
        """
        logger.info(f"Generating lab manual for: {theme}")
        
        # Step 1: Extract practical concepts from lecture
        practical_concepts = await self._extract_practical_concepts(
            lecture_content, theme
        )
        logger.info(f"Extracted {len(practical_concepts)} practical concepts")
        
        # Step 2: Generate learning objectives
        objectives = await self._generate_objectives(
            practical_concepts, theme
        )
        
        # Step 3: Generate exercises (3-5 per lab)
        exercises = []
        for i, concept in enumerate(practical_concepts[:5], 1):
            exercise = await self._generate_exercise(
                concept, theme, i
            )
            exercises.append(exercise)
        
        logger.info(f"Generated {len(exercises)} exercises")
        
        # Step 4: Generate assessment criteria
        criteria = await self._generate_assessment_criteria(exercises)
        
        return LabManual(
            theme=theme,
            learning_objectives=objectives,
            exercises=exercises,
            assessment_criteria=criteria,
            estimated_hours=len(exercises)  # ~1 hour per exercise
        )
    
    async def _extract_practical_concepts(
        self, 
        lecture_content: str, 
        theme: str
    ) -> List[str]:
        """Extract concepts that need hands-on practice"""
        
        prompt = f"""Проанализируй лекцию и определи 5 практических концепций, 
которые студенты должны отработать в лабораторной работе.

ЛЕКЦИЯ: {theme}

СОДЕРЖАНИЕ ЛЕКЦИИ:
{lecture_content[:3000]}  # First 3000 chars

ТРЕБОВАНИЯ:
- Выбери концепции, которые требуют практики
- Концепции должны иметь примеры кода
- Концепции должны быть выполнимы за 30-60 минут каждая
- Верни ТОЛЬКО список концепций через запятую

Практические концепции:"""
        
        llm_model = await self.model_manager.get_llm_model()
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt=prompt,
            options={"temperature": 0.2, "num_predict": 200}
        )
        
        concepts_text = response.get('response', '').strip()
        concepts = [c.strip() for c in concepts_text.split(',') if c.strip()]
        
        return concepts[:5]  # Max 5 concepts
    
    async def _generate_objectives(
        self, 
        concepts: List[str], 
        theme: str
    ) -> List[str]:
        """Generate learning objectives for the lab"""
        
        concepts_list = "\n".join([f"- {c}" for c in concepts])
        
        prompt = f"""Создай 3-5 учебных целей для лабораторной работы по теме "{theme}".

ПРАКТИЧЕСКИЕ КОНЦЕПЦИИ:
{concepts_list}

ТРЕБОВАНИЯ:
- Цели должны быть измеримыми
- Используй глаголы действия (создать, реализовать, применить)
- Каждая цель на отдельной строке
- Формат: "- Цель"

Учебные цели:"""
        
        llm_model = await self.model_manager.get_llm_model()
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt=prompt,
            options={"temperature": 0.2, "num_predict": 300}
        )
        
        objectives_text = response.get('response', '').strip()
        objectives = [
            line.strip('- ').strip() 
            for line in objectives_text.split('\n') 
            if line.strip().startswith('-')
        ]
        
        return objectives
    
    async def _generate_exercise(
        self, 
        concept: str, 
        theme: str, 
        number: int
    ) -> Exercise:
        """Generate a single exercise for a concept"""
        
        logger.info(f"Generating exercise {number}: {concept}")
        
        prompt = f"""Создай практическое упражнение для концепции "{concept}" 
в рамках темы "{theme}".

СТРУКТУРА УПРАЖНЕНИЯ:
1. Название упражнения
2. Описание задачи (2-3 предложения)
3. Пошаговые инструкции (3-5 шагов)
4. Стартовый код (если нужен)
5. Ожидаемый результат
6. Полное решение
7. Частые ошибки (2-3)
8. Подсказки (2-3)

ТРЕБОВАНИЯ:
- Упражнение должно быть выполнимо за 30-60 минут
- Код должен быть рабочим
- Инструкции должны быть четкими
- Решение должно быть полным

Упражнение:"""
        
        llm_model = await self.model_manager.get_llm_model()
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt=prompt,
            options={"temperature": 0.3, "num_predict": 2000}
        )
        
        # Parse response into Exercise structure
        exercise_text = response.get('response', '').strip()
        
        # TODO: Parse the response into structured Exercise object
        # For now, return basic structure
        return Exercise(
            number=number,
            title=f"Упражнение {number}: {concept}",
            description=exercise_text[:200],  # First 200 chars
            starter_code=None,
            instructions=[],
            expected_output="",
            solution_code="",
            common_mistakes=[],
            hints=[]
        )
    
    async def _generate_assessment_criteria(
        self, 
        exercises: List[Exercise]
    ) -> AssessmentCriteria:
        """Generate grading criteria for the lab"""
        
        exercises_list = "\n".join([
            f"{i}. {ex.title}" 
            for i, ex in enumerate(exercises, 1)
        ])
        
        prompt = f"""Создай критерии оценивания для лабораторной работы.

УПРАЖНЕНИЯ:
{exercises_list}

ТРЕБОВАНИЯ:
- 5-7 критериев оценивания
- Каждый критерий имеет название и баллы
- Общая сумма: 100 баллов
- Критерии должны покрывать: правильность кода, стиль, документацию, тестирование

Формат:
- Критерий (баллы): Описание

Критерии оценивания:"""
        
        llm_model = await self.model_manager.get_llm_model()
        response = await llm_model.generate(
            model="llama3.1:8b",
            prompt=prompt,
            options={"temperature": 0.2, "num_predict": 500}
        )
        
        # Parse criteria
        criteria_text = response.get('response', '').strip()
        
        # TODO: Parse into Criterion objects
        return AssessmentCriteria(
            criteria=[],
            total_points=100
        )
```

---

### Step 4: Test with One Lecture (Week 3)

**What to do**:
1. Create test file: `test_lab_manual_generation.py`
2. Generate lab for one lecture
3. Manually review quality
4. Iterate on prompts

**Test code**:

```python
# test_lab_manual_generation.py

import asyncio
from app.core.model_manager import ModelManager
from app.generation.lab_generator import LabManualGenerator
from pathlib import Path

async def test_single_lab():
    """Test lab manual generation for one lecture"""
    
    # Initialize
    model_manager = ModelManager()
    await model_manager.initialize()
    
    lab_generator = LabManualGenerator(model_manager)
    
    # Read existing lecture
    lecture_path = Path("lecture_Работа_со_строками_batched.md")
    with open(lecture_path, 'r', encoding='utf-8') as f:
        lecture_content = f.read()
    
    # Generate lab manual
    lab_manual = await lab_generator.generate_lab_manual(
        lecture_content=lecture_content,
        theme="Работа со строками"
    )
    
    # Save result
    output_path = Path("lab_manual_strings_test.md")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(format_lab_manual(lab_manual))
    
    print(f"✓ Lab manual generated: {output_path}")
    print(f"  Objectives: {len(lab_manual.learning_objectives)}")
    print(f"  Exercises: {len(lab_manual.exercises)}")
    print(f"  Estimated hours: {lab_manual.estimated_hours}")

def format_lab_manual(lab: LabManual) -> str:
    """Format lab manual as markdown"""
    content = f"""# Лабораторная работа: {lab.theme}

## Учебные цели

{chr(10).join([f'- {obj}' for obj in lab.learning_objectives])}

## Расчетное время: {lab.estimated_hours} часа

---

"""
    
    for exercise in lab.exercises:
        content += f"""## Упражнение {exercise.number}: {exercise.title}

{exercise.description}

### Инструкции
{chr(10).join([f'{i}. {inst}' for i, inst in enumerate(exercise.instructions, 1)])}

### Ожидаемый результат
```
{exercise.expected_output}
```

---

"""
    
    return content

if __name__ == "__main__":
    asyncio.run(test_single_lab())
```

---

### Step 5: Generate All 12 Labs (Week 4)

**What to do**:
1. Create batch generation script
2. Generate all 12 lab manuals
3. Review and validate each one
4. Fix any issues

**Batch script**:

```python
# generate_all_labs.py

import asyncio
from pathlib import Path
from app.generation.lab_generator import LabManualGenerator

async def generate_all_labs():
    """Generate lab manuals for all 12 lectures"""
    
    lectures = [
        ("Введение в Python", "lecture_01.md"),
        ("Основы синтаксиса и переменные", "lecture_02.md"),
        # ... all 12 lectures
    ]
    
    lab_generator = LabManualGenerator(model_manager)
    
    for theme, lecture_file in lectures:
        print(f"\nGenerating lab for: {theme}")
        
        # Read lecture
        with open(lecture_file, 'r', encoding='utf-8') as f:
            lecture_content = f.read()
        
        # Generate lab
        lab_manual = await lab_generator.generate_lab_manual(
            lecture_content, theme
        )
        
        # Save
        output_file = f"lab_manual_{theme.replace(' ', '_')}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(format_lab_manual(lab_manual))
        
        print(f"✓ Saved: {output_file}")

if __name__ == "__main__":
    asyncio.run(generate_all_labs())
```

---

### Step 6: Add to API (Week 4)

**What to do**:
1. Add lab generation endpoint to FastAPI
2. Integrate with existing lecture generation
3. Test API

**API endpoint**:

```python
# app/api/routes.py

@router.post("/generate-lab-manual")
async def generate_lab_manual(
    theme: str,
    lecture_content: str
):
    """Generate lab manual from lecture content"""
    
    lab_generator = LabManualGenerator(model_manager)
    lab_manual = await lab_generator.generate_lab_manual(
        lecture_content, theme
    )
    
    return {
        "success": True,
        "lab_manual": lab_manual
    }
```

---

## 📋 Milestone 3: Self-Study Guide Generation

**Goal**: Generate 12 self-study guides with reading assignments and practice problems  
**Timeline**: 3-4 weeks  
**Estimated Effort**: 60-80 hours

### Implementation Approach

**Key Insight**: Self-study guides are SIMPLER than lab manuals because:
- No code solutions needed
- Mostly text-based
- Can reuse lecture content directly

### Step 1: Design Structure (Week 1)

```python
@dataclass
class SelfStudyGuide:
    """Self-study guide structure"""
    theme: str
    reading_assignments: List[ReadingAssignment]  # 5-10 assignments
    practice_problems: List[Problem]              # 10-15 problems
    self_assessment: List[Question]               # 20-30 questions
    estimated_hours: int                          # 3-5 hours

@dataclass
class ReadingAssignment:
    """Reading from source book"""
    book_title: str
    pages: str                  # "стр. 45-52"
    topic: str                  # What to focus on
    key_points: List[str]       # 3-5 key takeaways
    comprehension_questions: List[str]  # 2-3 questions

@dataclass
class Problem:
    """Practice problem"""
    number: int
    difficulty: str             # "легкая", "средняя", "сложная"
    description: str
    hint: Optional[str]
    solution: str

@dataclass
class Question:
    """Self-assessment question"""
    number: int
    type: str                   # "multiple_choice", "true_false", "short_answer"
    question: str
    options: Optional[List[str]]  # For multiple choice
    correct_answer: str
    explanation: str
```

### Step 2: Create Generator (Week 2)

```python
# app/generation/self_study_generator.py

class SelfStudyGuideGenerator:
    """Generate self-study guides from lectures"""
    
    async def generate_guide(
        self,
        lecture_content: str,
        theme: str,
        source_pages: List[Dict]  # Pages used in lecture
    ) -> SelfStudyGuide:
        """Generate complete self-study guide"""
        
        # Step 1: Generate reading assignments from source pages
        readings = await self._generate_reading_assignments(
            source_pages, theme
        )
        
        # Step 2: Generate practice problems
        problems = await self._generate_practice_problems(
            lecture_content, theme
        )
        
        # Step 3: Generate self-assessment questions
        questions = await self._generate_self_assessment(
            lecture_content, theme
        )
        
        return SelfStudyGuide(
            theme=theme,
            reading_assignments=readings,
            practice_problems=problems,
            self_assessment=questions,
            estimated_hours=3 + len(readings) * 0.5
        )
```

**Key difference from labs**: Self-study guides pull MORE from source books, LESS generation needed.

---

## 📋 Milestone 4: Assessment Materials

**Goal**: Generate quizzes, test banks, and exams  
**Timeline**: 4-5 weeks  
**Estimated Effort**: 80-100 hours

### Implementation Approach

**Key Insight**: Assessment generation is HIGHLY STRUCTURED:
- Fixed question formats
- Clear correct/incorrect answers
- Can be validated automatically

### Step 1: Design Question Types (Week 1)

```python
@dataclass
class MultipleChoiceQuestion:
    """Multiple choice question"""
    question: str
    options: List[str]          # 4 options
    correct_index: int          # 0-3
    explanation: str
    difficulty: str             # "easy", "medium", "hard"
    concept: str                # Which concept it tests

@dataclass
class TrueFalseQuestion:
    """True/false question"""
    statement: str
    correct_answer: bool
    explanation: str
    difficulty: str
    concept: str

@dataclass
class FillInBlankQuestion:
    """Fill in the blank"""
    question: str               # "Строка в Python является ___ типом"
    correct_answer: str         # "неизменяемым"
    alternatives: List[str]     # ["immutable", "неизменяемым"]
    explanation: str
    difficulty: str
    concept: str

@dataclass
class CodingQuestion:
    """Coding problem"""
    description: str
    starter_code: str
    test_cases: List[TestCase]
    solution: str
    difficulty: str
    concept: str

@dataclass
class TestCase:
    """Test case for coding question"""
    input: str
    expected_output: str
    description: str
```

### Step 2: Create Question Generator (Week 2-3)

```python
# app/generation/assessment_generator.py

class AssessmentGenerator:
    """Generate assessment materials"""
    
    async def generate_quiz(
        self,
        lecture_content: str,
        theme: str,
        question_count: int = 10
    ) -> Quiz:
        """Generate quiz for a lecture"""
        
        # Extract key concepts
        concepts = await self._extract_concepts(lecture_content)
        
        # Generate mix of question types
        questions = []
        
        # 50% multiple choice
        mc_questions = await self._generate_multiple_choice(
            concepts, count=question_count // 2
        )
        questions.extend(mc_questions)
        
        # 30% true/false
        tf_questions = await self._generate_true_false(
            concepts, count=question_count // 3
        )
        questions.extend(tf_questions)
        
        # 20% fill in blank
        fib_questions = await self._generate_fill_in_blank(
            concepts, count=question_count // 5
        )
        questions.extend(fib_questions)
        
        return Quiz(
            theme=theme,
            questions=questions[:question_count],
            total_points=question_count * 10
        )
    
    async def _generate_multiple_choice(
        self,
        concepts: List[str],
        count: int
    ) -> List[MultipleChoiceQuestion]:
        """Generate multiple choice questions"""
        
        questions = []
        
        for concept in concepts[:count]:
            prompt = f"""Создай вопрос с множественным выбором для концепции "{concept}".

ТРЕБОВАНИЯ:
- Вопрос должен проверять понимание концепции
- 4 варианта ответа (A, B, C, D)
- Только 1 правильный ответ
- 3 правдоподобных неправильных ответа
- Объяснение правильного ответа

Формат:
Вопрос: [текст вопроса]
A) [вариант 1]
B) [вариант 2]
C) [вариант 3]
D) [вариант 4]
Правильный ответ: [A/B/C/D]
Объяснение: [почему это правильно]

Вопрос:"""
            
            llm_model = await self.model_manager.get_llm_model()
            response = await llm_model.generate(
                model="llama3.1:8b",
                prompt=prompt,
                options={"temperature": 0.3, "num_predict": 500}
            )
            
            # Parse response into MultipleChoiceQuestion
            # TODO: Implement parsing logic
            
        return questions
```

### Step 3: Export to Moodle XML (Week 4)

**Critical**: Moodle has specific XML format for questions

```python
# app/generation/moodle_exporter.py

class MoodleXMLExporter:
    """Export questions to Moodle XML format"""
    
    def export_quiz(self, quiz: Quiz) -> str:
        """Export quiz to Moodle XML"""
        
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<quiz>
"""
        
        for question in quiz.questions:
            if isinstance(question, MultipleChoiceQuestion):
                xml += self._export_multiple_choice(question)
            elif isinstance(question, TrueFalseQuestion):
                xml += self._export_true_false(question)
            # ... other types
        
        xml += "</quiz>"
        return xml
    
    def _export_multiple_choice(self, q: MultipleChoiceQuestion) -> str:
        """Export MC question to Moodle XML"""
        return f"""
  <question type="multichoice">
    <name>
      <text>{q.concept}</text>
    </name>
    <questiontext format="html">
      <text><![CDATA[{q.question}]]></text>
    </questiontext>
    <answer fraction="{'100' if i == q.correct_index else '0'}" format="html">
      <text><![CDATA[{option}]]></text>
    </answer>
    <!-- ... more answers -->
  </question>
"""
```

---

## 📋 Milestone 5: Course Project Generation

**Goal**: Generate 1 comprehensive course project  
**Timeline**: 2-3 weeks  
**Estimated Effort**: 40-60 hours

### Implementation Approach

**Key Insight**: Course project SYNTHESIZES all 12 lectures:
- Combines concepts from all lectures
- Requires integration of multiple topics
- More complex than individual exercises

### Step 1: Analyze All Lectures (Week 1)

```python
# analyze_course_concepts.py

async def analyze_all_lectures():
    """Extract all concepts from 12 lectures"""
    
    all_concepts = []
    
    for lecture_file in lecture_files:
        with open(lecture_file, 'r') as f:
            content = f.read()
        
        concepts = extract_concepts(content)
        all_concepts.extend(concepts)
    
    # Group by category
    categorized = categorize_concepts(all_concepts)
    
    return categorized
```

### Step 2: Generate Project Requirements (Week 1-2)

```python
# app/generation/project_generator.py

class CourseProjectGenerator:
    """Generate course project"""
    
    async def generate_project(
        self,
        all_lectures: List[Lecture]
    ) -> CourseProject:
        """Generate comprehensive course project"""
        
        # Step 1: Synthesize all concepts
        all_concepts = self._synthesize_concepts(all_lectures)
        
        # Step 2: Generate project idea
        project_idea = await self._generate_project_idea(all_concepts)
        
        # Step 3: Generate requirements
        requirements = await self._generate_requirements(
            project_idea, all_concepts
        )
        
        # Step 4: Generate starter template
        template = await self._generate_template(requirements)
        
        # Step 5: Generate rubric
        rubric = await self._generate_rubric(requirements)
        
        return CourseProject(
            title=project_idea.title,
            description=project_idea.description,
            requirements=requirements,
            template=template,
            rubric=rubric,
            estimated_hours=40
        )
```

---

## 🔑 Key Success Factors

### 1. Reuse Proven Patterns
- Copy architecture from `generator_v3.py`
- Use same batched processing
- Apply same prompt engineering
- Maintain same quality standards

### 2. Start Small, Iterate
- Test with ONE lecture first
- Get feedback
- Refine prompts
- Then scale to all 12

### 3. Validate Quality
- Manual review of first outputs
- Check against real educational standards
- Get professor feedback early
- Iterate based on feedback

### 4. Leverage Existing Content
- Lab manuals: Extract from lectures
- Self-study: Reuse source pages
- Assessments: Test lecture concepts
- Projects: Synthesize all lectures

---

## 📊 Effort Estimation Summary

| Milestone | Weeks | Hours | Complexity |
|-----------|-------|-------|------------|
| M2: Lab Manuals | 4-6 | 80-100 | HIGH |
| M3: Self-Study | 3-4 | 60-80 | MEDIUM |
| M4: Assessments | 4-5 | 80-100 | HIGH |
| M5: Projects | 2-3 | 40-60 | MEDIUM |
| **TOTAL** | **13-18** | **260-340** | - |

**Timeline**: 3-4.5 months of development

---

## 🚀 Getting Started Checklist

### Before Starting M2
- [ ] Review all 12 generated lectures
- [ ] Understand generator_v3.py architecture
- [ ] Set up development environment
- [ ] Create test data structure
- [ ] Get professor feedback on lab manual template

### Week 1 Actions
- [ ] Create `app/generation/lab_generator.py`
- [ ] Define data structures
- [ ] Write extraction logic
- [ ] Create test file
- [ ] Generate first lab manual

### Success Criteria
- [ ] First lab manual looks good
- [ ] Professor approves structure
- [ ] Generation time < 5 minutes
- [ ] Code examples are correct
- [ ] Ready to scale to all 12

---

**Next Step**: Start with Milestone 2, Exercise 1 - Analyze existing lectures and create lab manual template.

---

**Document Version**: 1.0  
**Last Updated**: February 26, 2026  
**Status**: Ready for Implementation
