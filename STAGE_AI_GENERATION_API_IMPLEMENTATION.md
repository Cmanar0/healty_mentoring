# Stage AI Generation API Implementation Guide

**Status:** Implementation Guide  
**Last Updated:** 2025-01-19  
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Current Implementation](#current-implementation)
3. [Data Available for AI](#data-available-for-ai)
4. [Expected AI API Response Format](#expected-ai-api-response-format)
5. [Implementation Steps](#implementation-steps)
6. [AI Service Module](#ai-service-module)
7. [Django Settings Configuration](#django-settings-configuration)
8. [View Integration](#view-integration)
9. [AI Provider Examples](#ai-provider-examples)
10. [Error Handling & Fallbacks](#error-handling--fallbacks)
11. [Testing Guide](#testing-guide)
12. [Cost Optimization](#cost-optimization)

---

## Overview

This document provides a complete guide for implementing real AI-powered stage generation to replace the current mockup implementation. The system is designed to generate project stages based on:

- Project title and description
- Questionnaire answers
- Project template (if any)
- Existing project context

The AI-generated stages are created with `is_ai_generated=True` and `is_pending_confirmation=True`, requiring mentor review and confirmation before being saved permanently.

---

## Current Implementation

The current mockup implementation is located in:
- **File:** `dashboard_mentor/views.py`
- **Function:** `generate_stages_ai()` (lines ~4703-4783)
- **Status:** Creates 3 hardcoded sample stages

The mockup code includes TODO comments indicating where the real AI integration should be added:

```python
# AI Mockup: Generate 3 stages based on project context
# TODO: Replace with actual AI API call
# Expected API structure:
# response = ai_service.generate_stages(
#     project_title=project.title,
#     project_description=project.description,
#     questionnaire_answers=[{'question': a.question.question_text, 'answer': a.answer} for a in answers],
#     template=project.template.name if project.template else None
# )
# stages_data = response.get('stages', [])
```

---

## Data Available for AI

The following data is collected and prepared for the AI service:

### Project Information
```python
project_title = project.title
project_description = project.description
project_template = project.template.name if project.template else None
project_created_at = project.created_at
existing_stages_count = project.stages.count()
```

### Questionnaire Answers
```python
questionnaire_answers = [
    {
        'question': answer.question.question_text,
        'answer': answer.answer,
        'question_type': answer.question.question_type,  # 'textarea', 'text', 'date', etc.
        'order': answer.question.order
    }
    for answer in ProjectQuestionnaireAnswer.objects.filter(project=project)
    .select_related('question')
    .order_by('question__order')
]
```

### Example Data Structure
```python
{
    'project_title': 'Business Test Project',
    'project_description': 'ads asd fasdf asdf asdf',
    'template': 'Business Plan',
    'questionnaire_answers': [
        {
            'question': 'What is your main goal?',
            'answer': 'To launch a successful online business',
            'question_type': 'textarea',
            'order': 1
        },
        {
            'question': 'What is your target timeline?',
            'answer': '6 months',
            'question_type': 'text',
            'order': 2
        }
    ],
    'existing_stages_count': 0
}
```

---

## Expected AI API Response Format

The AI service must return a JSON response with the following structure:

### Required Format
```json
{
  "stages": [
    {
      "title": "Stage Title Here (max 200 characters)",
      "description": "Detailed description of what this stage involves and what needs to be accomplished...",
      "target_date_offset": 14,
      "order": 1,
      "confidence": 0.95
    },
    {
      "title": "Another Stage",
      "description": "Description of the second stage...",
      "target_date_offset": 30,
      "order": 2,
      "confidence": 0.88
    }
  ],
  "metadata": {
    "total_stages": 2,
    "reasoning": "Brief explanation of why these stages were chosen",
    "estimated_duration_days": 90
  }
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stages` | Array | Yes | List of stage objects |
| `stages[].title` | String | Yes | Stage title (max 200 chars) |
| `stages[].description` | String | Yes | Detailed stage description |
| `stages[].target_date_offset` | Integer | No | Days from project start date |
| `stages[].order` | Integer | No | Suggested order (auto-calculated if missing) |
| `stages[].confidence` | Float | No | AI confidence score (0-1) |
| `metadata.total_stages` | Integer | No | Total number of stages generated |
| `metadata.reasoning` | String | No | Explanation of stage selection |
| `metadata.estimated_duration_days` | Integer | No | Total project duration estimate |

---

## Implementation Steps

### Step 1: Create AI Service Module

Create a new file: `general/ai_service.py`

This module will handle all AI API communication and response parsing.

### Step 2: Update Django Settings

Add AI configuration to `healthy_mentoring/settings.py`:

```python
# AI Configuration
AI_API_KEY = os.environ.get('AI_API_KEY', '')
AI_API_URL = os.environ.get('AI_API_URL', '')  # If using custom endpoint
AI_MODEL = os.environ.get('AI_MODEL', 'gpt-4')
AI_MAX_STAGES = int(os.environ.get('AI_MAX_STAGES', 10))
AI_ENABLED = os.environ.get('AI_ENABLED', 'False').lower() == 'true'
```

### Step 3: Update Requirements

Add AI provider library to `requirements.txt`:

```txt
# For OpenAI
openai>=1.0.0

# OR for Anthropic
anthropic>=0.18.0

# OR for Google
google-generativeai>=0.3.0

# For retry logic
tenacity>=8.2.0
```

### Step 4: Update View

Replace the mockup code in `dashboard_mentor/views.py` with real AI integration.

### Step 5: Test Integration

Test with real projects and verify stages are created correctly.

---

## AI Service Module

### Complete Implementation: `general/ai_service.py`

```python
# general/ai_service.py

import json
import logging
from typing import List, Dict, Optional
from django.conf import settings
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class AIStageGenerationService:
    """
    Service for generating project stages using AI.
    
    This service handles communication with AI APIs (OpenAI, Anthropic, etc.)
    and formats the response for the project system.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'AI_API_KEY', None)
        self.api_url = getattr(settings, 'AI_API_URL', None)
        self.model = getattr(settings, 'AI_MODEL', 'gpt-4')
        self.max_stages = getattr(settings, 'AI_MAX_STAGES', 10)
        self.provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
        
        if not self.api_key:
            logger.warning('AI_API_KEY not configured. AI features will not work.')
        
    def generate_stages(
        self,
        project_title: str,
        project_description: str,
        questionnaire_answers: List[Dict],
        template: Optional[str] = None,
        existing_stages_count: int = 0
    ) -> Dict:
        """
        Generate project stages using AI.
        
        Args:
            project_title: Title of the project
            project_description: Description of the project
            questionnaire_answers: List of Q&A pairs from questionnaire
            template: Project template name (if any)
            existing_stages_count: Number of existing stages (to avoid duplicates)
            
        Returns:
            Dict with 'stages' list and optional 'metadata'
            
        Raises:
            AIServiceError: If AI API call fails
        """
        if not self.api_key:
            raise AIServiceError('AI API key not configured')
        
        try:
            # Build the prompt
            prompt = self._build_prompt(
                project_title=project_title,
                project_description=project_description,
                questionnaire_answers=questionnaire_answers,
                template=template
            )
            
            # Call AI API
            response = self._call_ai_api(prompt)
            
            # Parse and validate response
            parsed_response = self._parse_response(response)
            
            # Validate stages
            validated_stages = self._validate_stages(parsed_response.get('stages', []))
            
            if not validated_stages:
                raise AIServiceError('AI did not generate any valid stages')
            
            return {
                'stages': validated_stages,
                'metadata': parsed_response.get('metadata', {})
            }
            
        except AIServiceError:
            raise
        except Exception as e:
            logger.error(f'AI stage generation failed: {str(e)}', exc_info=True)
            raise AIServiceError(f'Failed to generate stages: {str(e)}')
    
    def _build_prompt(
        self,
        project_title: str,
        project_description: str,
        questionnaire_answers: List[Dict],
        template: Optional[str] = None
    ) -> str:
        """Build the prompt to send to AI"""
        
        prompt = f"""You are an expert project management consultant. Generate a detailed project plan with stages for the following project:

PROJECT TITLE: {project_title}

PROJECT DESCRIPTION:
{project_description}

"""
        
        if template:
            prompt += f"PROJECT TEMPLATE TYPE: {template}\n\n"
        
        if questionnaire_answers:
            prompt += "QUESTIONNAIRE ANSWERS:\n"
            for i, qa in enumerate(questionnaire_answers, 1):
                prompt += f"{i}. {qa['question']}\n   Answer: {qa['answer']}\n\n"
        
        prompt += """Based on this information, generate a comprehensive project plan with multiple stages. Each stage should:

1. Have a clear, actionable title (max 200 characters)
2. Include a detailed description explaining what needs to be accomplished
3. Suggest a realistic target date offset (days from project start)
4. Be ordered logically (earlier stages should be prerequisites for later ones)

Return your response as a JSON object with this exact structure:
{
  "stages": [
    {
      "title": "Stage title",
      "description": "Detailed description",
      "target_date_offset": 14,
      "order": 1
    }
  ],
  "metadata": {
    "total_stages": 3,
    "reasoning": "Brief explanation"
  }
}

Generate between 3-8 stages depending on project complexity. Focus on actionable, measurable stages."""
        
        return prompt
    
    def _call_ai_api(self, prompt: str) -> str:
        """
        Call the actual AI API based on configured provider.
        
        This method routes to the appropriate provider implementation.
        """
        if self.provider == 'openai':
            return self._call_openai_api(prompt)
        elif self.provider == 'anthropic':
            return self._call_anthropic_api(prompt)
        elif self.provider == 'google':
            return self._call_google_api(prompt)
        elif self.provider == 'custom':
            return self._call_custom_api(prompt)
        else:
            raise AIServiceError(f'Unknown AI provider: {self.provider}')
    
    def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API (GPT-4, GPT-3.5, etc.)"""
        try:
            import openai
            
            openai.api_key = self.api_key
            response = openai.ChatCompletion.create(
                model=self.model,  # 'gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert project management consultant. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}  # Forces JSON response
            )
            
            return response.choices[0].message.content
            
        except ImportError:
            raise AIServiceError('OpenAI library not installed. Install with: pip install openai')
        except Exception as e:
            logger.error(f'OpenAI API error: {str(e)}')
            raise AIServiceError(f'OpenAI API call failed: {str(e)}')
    
    def _call_anthropic_api(self, prompt: str) -> str:
        """Call Anthropic Claude API"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=self.api_key)
            message = client.messages.create(
                model=self.model,  # 'claude-3-opus-20240229', 'claude-3-sonnet-20240229'
                max_tokens=2000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nPlease respond with valid JSON only."
                    }
                ]
            )
            
            return message.content[0].text
            
        except ImportError:
            raise AIServiceError('Anthropic library not installed. Install with: pip install anthropic')
        except Exception as e:
            logger.error(f'Anthropic API error: {str(e)}')
            raise AIServiceError(f'Anthropic API call failed: {str(e)}')
    
    def _call_google_api(self, prompt: str) -> str:
        """Call Google Gemini API"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)  # 'gemini-pro'
            
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 2000,
                }
            )
            
            return response.text
            
        except ImportError:
            raise AIServiceError('Google Generative AI library not installed. Install with: pip install google-generativeai')
        except Exception as e:
            logger.error(f'Google API error: {str(e)}')
            raise AIServiceError(f'Google API call failed: {str(e)}')
    
    def _call_custom_api(self, prompt: str) -> str:
        """Call custom REST API endpoint"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'prompt': prompt,
                'model': self.model,
                'max_tokens': 2000,
                'temperature': 0.7
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract content from response (adjust based on your API structure)
            return result.get('content') or result.get('text') or str(result)
            
        except ImportError:
            raise AIServiceError('Requests library not installed. Install with: pip install requests')
        except Exception as e:
            logger.error(f'Custom API error: {str(e)}')
            raise AIServiceError(f'Custom API call failed: {str(e)}')
    
    def _parse_response(self, response: str) -> Dict:
        """Parse AI response and extract JSON"""
        try:
            # Try to extract JSON from response (AI might wrap it in markdown code blocks)
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith('```'):
                # Remove code block markers
                response = re.sub(r'^```(?:json)?\s*', '', response, flags=re.MULTILINE)
                response = re.sub(r'\s*```$', '', response, flags=re.MULTILINE)
            
            # Try to find JSON object in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                # Try parsing entire response
                return json.loads(response)
                
        except json.JSONDecodeError as e:
            logger.error(f'Failed to parse AI response. Response preview: {response[:500]}')
            raise AIServiceError(f'Invalid JSON response from AI: {str(e)}')
    
    def _validate_stages(self, stages: List[Dict]) -> List[Dict]:
        """Validate and clean stage data"""
        if not isinstance(stages, list):
            logger.warning('Stages data is not a list')
            return []
        
        validated = []
        
        for i, stage in enumerate(stages):
            if not isinstance(stage, dict):
                logger.warning(f'Stage {i} is not a dictionary, skipping')
                continue
            
            # Validate required fields
            title = stage.get('title', '').strip()
            if not title:
                logger.warning(f'Stage {i} missing title, skipping')
                continue
            
            if len(title) > 200:
                logger.warning(f'Stage {i} title too long ({len(title)} chars), truncating')
                title = title[:200]
            
            description = stage.get('description', '').strip()
            if not description:
                logger.warning(f'Stage {i} missing description, using default')
                description = f'Stage: {title}'
            
            # Validate target_date_offset
            target_date_offset = stage.get('target_date_offset')
            if target_date_offset is not None:
                try:
                    target_date_offset = int(target_date_offset)
                    if target_date_offset < 0:
                        target_date_offset = None
                except (ValueError, TypeError):
                    target_date_offset = None
            
            # Validate order
            order = stage.get('order')
            if order is not None:
                try:
                    order = int(order)
                except (ValueError, TypeError):
                    order = None
            
            # Validate confidence
            confidence = stage.get('confidence', 0.8)
            try:
                confidence = float(confidence)
                confidence = max(0.0, min(1.0, confidence))  # Clamp between 0-1
            except (ValueError, TypeError):
                confidence = 0.8
            
            validated.append({
                'title': title,
                'description': description,
                'target_date_offset': target_date_offset,
                'order': order,
                'confidence': confidence
            })
        
        # Limit number of stages
        if len(validated) > self.max_stages:
            logger.warning(f'Limiting stages from {len(validated)} to {self.max_stages}')
            validated = validated[:self.max_stages]
        
        return validated


class AIServiceError(Exception):
    """Custom exception for AI service errors"""
    pass
```

---

## Django Settings Configuration

Add the following to `healthy_mentoring/settings.py`:

```python
# AI Configuration
AI_API_KEY = os.environ.get('AI_API_KEY', '')
AI_API_URL = os.environ.get('AI_API_URL', '')  # Required for custom provider
AI_MODEL = os.environ.get('AI_MODEL', 'gpt-4')  # Model name for your provider
AI_PROVIDER = os.environ.get('AI_PROVIDER', 'openai')  # 'openai', 'anthropic', 'google', 'custom'
AI_MAX_STAGES = int(os.environ.get('AI_MAX_STAGES', 10))
AI_ENABLED = os.environ.get('AI_ENABLED', 'False').lower() == 'true'
```

### Environment Variables

Set these in your environment (`.env` file or system environment):

```bash
# Enable AI features
AI_ENABLED=true

# Your AI provider API key
AI_API_KEY=sk-your-api-key-here

# AI provider (openai, anthropic, google, custom)
AI_PROVIDER=openai

# Model name (depends on provider)
AI_MODEL=gpt-4

# Maximum number of stages to generate
AI_MAX_STAGES=10

# Custom API URL (only needed for custom provider)
AI_API_URL=https://api.example.com/v1/generate
```

---

## View Integration

Update `dashboard_mentor/views.py` in the `generate_stages_ai()` function:

### Replace Mockup Section

**Find this code (around lines 4726-4756):**
```python
# AI Mockup: Generate 3 stages based on project context
# TODO: Replace with actual AI API call
# Expected API structure:
# response = ai_service.generate_stages(
#     project_title=project.title,
#     project_description=project.description,
#     questionnaire_answers=[{'question': a.question.question_text, 'answer': a.answer} for a in answers],
#     template=project.template.name if project.template else None
# )
# stages_data = response.get('stages', [])

# Mockup: Generate 3 sample stages
base_date = project.created_at.date() if hasattr(project.created_at, 'date') else timezone.now().date()

mock_stages = [
    {
        'title': 'Initial Planning & Research',
        'description': 'Conduct thorough research and create a comprehensive plan based on your project goals and current situation.',
        'target_date_offset': 14,
    },
    {
        'title': 'Implementation & Execution',
        'description': 'Begin implementing your plan with focused action steps and regular progress tracking.',
        'target_date_offset': 30,
    },
    {
        'title': 'Review & Optimization',
        'description': 'Review progress, identify areas for improvement, and optimize your approach for better results.',
        'target_date_offset': 60,
    },
]

created_stages = []
for i, stage_data in enumerate(mock_stages):
    target_date = base_date + timedelta(days=stage_data['target_date_offset']) if stage_data.get('target_date_offset') else None
    
    stage = ProjectStage.objects.create(
        project=project,
        title=stage_data['title'],
        description=stage_data['description'],
        target_date=target_date,
        order=next_order + i,
        is_ai_generated=True,
        is_pending_confirmation=True,  # Require confirmation
    )
    created_stages.append(stage.id)
```

**Replace with:**
```python
from general.ai_service import AIStageGenerationService, AIServiceError
from django.conf import settings

# Check if AI is enabled
ai_enabled = getattr(settings, 'AI_ENABLED', False)

if not ai_enabled:
    # Fallback to mockup if AI is disabled
    base_date = project.created_at.date() if hasattr(project.created_at, 'date') else timezone.now().date()
    
    mock_stages = [
        {
            'title': 'Initial Planning & Research',
            'description': 'Conduct thorough research and create a comprehensive plan based on your project goals and current situation.',
            'target_date_offset': 14,
        },
        {
            'title': 'Implementation & Execution',
            'description': 'Begin implementing your plan with focused action steps and regular progress tracking.',
            'target_date_offset': 30,
        },
        {
            'title': 'Review & Optimization',
            'description': 'Review progress, identify areas for improvement, and optimize your approach for better results.',
            'target_date_offset': 60,
        },
    ]
    
    created_stages = []
    for i, stage_data in enumerate(mock_stages):
        target_date = base_date + timedelta(days=stage_data['target_date_offset']) if stage_data.get('target_date_offset') else None
        
        stage = ProjectStage.objects.create(
            project=project,
            title=stage_data['title'],
            description=stage_data['description'],
            target_date=target_date,
            order=next_order + i,
            is_ai_generated=True,
            is_pending_confirmation=True,
        )
        created_stages.append(stage.id)
    
    return JsonResponse({
        'success': True,
        'message': f'{len(created_stages)} stages generated successfully. Please review and confirm them.',
        'stages_count': len(created_stages),
        'stage_ids': created_stages
    })

# Use real AI
try:
    ai_service = AIStageGenerationService()
    
    # Prepare questionnaire answers
    questionnaire_answers = [
        {
            'question': answer.question.question_text,
            'answer': answer.answer,
            'question_type': answer.question.question_type,
            'order': answer.question.order
        }
        for answer in answers
    ]
    
    # Call AI service
    ai_response = ai_service.generate_stages(
        project_title=project.title,
        project_description=project.description or '',
        questionnaire_answers=questionnaire_answers,
        template=project.template.name if project.template else None,
        existing_stages_count=project.stages.count()
    )
    
    stages_data = ai_response.get('stages', [])
    
    if not stages_data:
        return JsonResponse({
            'success': False,
            'error': 'AI did not generate any stages. Please try again.'
        }, status=500)
    
    # Create stages from AI response
    base_date = project.created_at.date() if hasattr(project.created_at, 'date') else timezone.now().date()
    created_stages = []
    
    for i, stage_data in enumerate(stages_data):
        target_date = None
        if stage_data.get('target_date_offset') is not None:
            target_date = base_date + timedelta(days=stage_data['target_date_offset'])
        
        # Use provided order or calculate next order
        stage_order = stage_data.get('order')
        if stage_order is None:
            stage_order = next_order + i
        
        stage = ProjectStage.objects.create(
            project=project,
            title=stage_data['title'],
            description=stage_data['description'],
            target_date=target_date,
            order=stage_order,
            is_ai_generated=True,
            is_pending_confirmation=True,
        )
        created_stages.append(stage.id)
    
    return JsonResponse({
        'success': True,
        'message': f'{len(created_stages)} stages generated successfully. Please review and confirm them.',
        'stages_count': len(created_stages),
        'stage_ids': created_stages,
        'metadata': ai_response.get('metadata', {})
    })
    
except AIServiceError as e:
    logger.error(f'AI service error: {str(e)}')
    return JsonResponse({
        'success': False,
        'error': f'AI service error: {str(e)}'
    }, status=500)
except Exception as e:
    logger.error(f'Unexpected error in AI generation: {str(e)}', exc_info=True)
    return JsonResponse({
        'success': False,
        'error': 'An unexpected error occurred. Please try again.'
    }, status=500)
```

---

## AI Provider Examples

### OpenAI (GPT-4, GPT-3.5)

**Installation:**
```bash
pip install openai>=1.0.0
```

**Configuration:**
```bash
AI_ENABLED=true
AI_PROVIDER=openai
AI_MODEL=gpt-4  # or gpt-4-turbo, gpt-3.5-turbo
AI_API_KEY=sk-your-openai-api-key
```

**Cost:** ~$0.03-0.06 per request (GPT-4), ~$0.002 per request (GPT-3.5)

### Anthropic Claude

**Installation:**
```bash
pip install anthropic>=0.18.0
```

**Configuration:**
```bash
AI_ENABLED=true
AI_PROVIDER=anthropic
AI_MODEL=claude-3-opus-20240229  # or claude-3-sonnet-20240229
AI_API_KEY=sk-ant-your-anthropic-api-key
```

**Cost:** ~$0.015-0.03 per request (Sonnet), ~$0.045-0.09 per request (Opus)

### Google Gemini

**Installation:**
```bash
pip install google-generativeai>=0.3.0
```

**Configuration:**
```bash
AI_ENABLED=true
AI_PROVIDER=google
AI_MODEL=gemini-pro
AI_API_KEY=your-google-api-key
```

**Cost:** Free tier available, then pay-as-you-go

### Custom REST API

**Configuration:**
```bash
AI_ENABLED=true
AI_PROVIDER=custom
AI_API_URL=https://api.example.com/v1/generate
AI_MODEL=your-model-name
AI_API_KEY=your-api-key
```

**Expected API Format:**
```json
POST /v1/generate
Headers: {
  "Authorization": "Bearer your-api-key",
  "Content-Type": "application/json"
}
Body: {
  "prompt": "...",
  "model": "your-model-name",
  "max_tokens": 2000,
  "temperature": 0.7
}
Response: {
  "content": "{...JSON response...}"
}
```

---

## Error Handling & Fallbacks

### Retry Logic

Add retry logic using `tenacity`:

```python
# Add to requirements.txt
tenacity>=8.2.0

# In ai_service.py
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True
)
def _call_ai_api(self, prompt: str) -> str:
    # ... API call code
```

### Error Types to Handle

1. **API Failures**: Network errors, timeouts
2. **Invalid Responses**: Malformed JSON, missing fields
3. **Rate Limits**: Too many requests
4. **Authentication Errors**: Invalid API key
5. **Quota Exceeded**: API usage limits reached

### Fallback Strategy

The view includes a fallback to mockup stages if:
- `AI_ENABLED=False`
- AI service raises an exception
- AI returns no valid stages

---

## Testing Guide

### 1. Unit Tests

Create `general/tests/test_ai_service.py`:

```python
from django.test import TestCase
from general.ai_service import AIStageGenerationService, AIServiceError

class AIStageGenerationServiceTest(TestCase):
    def setUp(self):
        self.service = AIStageGenerationService()
    
    def test_build_prompt(self):
        prompt = self.service._build_prompt(
            project_title="Test Project",
            project_description="Test description",
            questionnaire_answers=[
                {'question': 'Q1', 'answer': 'A1', 'question_type': 'text', 'order': 1}
            ],
            template="Business Plan"
        )
        self.assertIn("Test Project", prompt)
        self.assertIn("Q1", prompt)
        self.assertIn("A1", prompt)
    
    def test_validate_stages(self):
        stages = [
            {
                'title': 'Valid Stage',
                'description': 'Description',
                'target_date_offset': 14
            },
            {
                'title': '',  # Invalid - missing title
                'description': 'Description'
            }
        ]
        validated = self.service._validate_stages(stages)
        self.assertEqual(len(validated), 1)
        self.assertEqual(validated[0]['title'], 'Valid Stage')
```

### 2. Integration Testing

1. **Set up test environment:**
   ```bash
   export AI_ENABLED=true
   export AI_API_KEY=test-key
   export AI_PROVIDER=openai
   export AI_MODEL=gpt-4
   ```

2. **Create a test project with questionnaire answers**

3. **Call the generate endpoint:**
   ```bash
   curl -X POST http://localhost:8000/dashboard/mentor/projects/1/stages/generate-ai/ \
     -H "Content-Type: application/json" \
     -H "X-CSRFToken: your-csrf-token" \
     --cookie "sessionid=your-session-id"
   ```

4. **Verify:**
   - Stages are created with `is_ai_generated=True`
   - Stages have `is_pending_confirmation=True`
   - Stages have valid titles and descriptions
   - Target dates are calculated correctly

### 3. Manual Testing Checklist

- [ ] AI generates stages when questionnaire is completed
- [ ] Generated stages appear with "Pending Confirmation" badge
- [ ] Edit button works for AI-generated stages
- [ ] Confirm button saves stages permanently
- [ ] Delete button removes stages
- [ ] Error messages display if AI fails
- [ ] Fallback to mockup works when AI is disabled
- [ ] Multiple projects can generate stages independently

---

## Cost Optimization

### 1. Caching

Cache AI responses for similar projects:

```python
from django.core.cache import cache

def generate_stages(self, ...):
    # Create cache key from project data
    cache_key = f'ai_stages_{hash(project_title + str(questionnaire_answers))}'
    
    # Check cache
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Generate stages
    result = self._call_ai_api(...)
    
    # Cache for 24 hours
    cache.set(cache_key, result, 86400)
    
    return result
```

### 2. Model Selection

- Use cheaper models (GPT-3.5) for simple projects
- Use expensive models (GPT-4) only for complex projects
- Consider project template complexity

### 3. Token Limits

- Set appropriate `max_tokens` (2000 is usually sufficient)
- Limit prompt length for questionnaire answers
- Truncate long descriptions

### 4. Batch Processing

If generating stages for multiple projects:
- Queue requests
- Process in batches
- Respect rate limits

### 5. Usage Tracking

Track AI usage for monitoring:

```python
# In ai_service.py
from general.models import AIUsageLog

def _call_ai_api(self, prompt: str) -> str:
    start_time = time.time()
    tokens_used = 0
    
    try:
        response = # ... API call
        tokens_used = response.usage.total_tokens  # OpenAI example
        
        # Log usage
        AIUsageLog.objects.create(
            provider=self.provider,
            model=self.model,
            tokens_used=tokens_used,
            duration_ms=int((time.time() - start_time) * 1000),
            success=True
        )
        
        return response
    except Exception as e:
        AIUsageLog.objects.create(
            provider=self.provider,
            model=self.model,
            success=False,
            error_message=str(e)
        )
        raise
```

---

## Summary

### What the Code Expects

**Input:**
- Project title and description
- Questionnaire answers (Q&A pairs)
- Project template name (optional)
- Existing stages count

**Output:**
- JSON with `stages` array
- Each stage: `title`, `description`, `target_date_offset`, optional `order` and `confidence`
- Optional `metadata` object

**Behavior:**
- Creates `ProjectStage` objects with `is_ai_generated=True`
- Sets `is_pending_confirmation=True` (requires mentor confirmation)
- Calculates target dates from offsets
- Handles errors gracefully with fallbacks

### Implementation Checklist

- [ ] Create `general/ai_service.py` with AI service class
- [ ] Add AI configuration to `settings.py`
- [ ] Install AI provider library (`openai`, `anthropic`, etc.)
- [ ] Update `requirements.txt`
- [ ] Replace mockup code in `generate_stages_ai()` view
- [ ] Set environment variables
- [ ] Test with real API key
- [ ] Add error handling and logging
- [ ] Implement caching (optional)
- [ ] Add usage tracking (optional)
- [ ] Update documentation

---

## Support & Troubleshooting

### Common Issues

1. **"AI_API_KEY not configured"**
   - Set `AI_API_KEY` environment variable
   - Check `AI_ENABLED=true`

2. **"Invalid JSON response from AI"**
   - Check AI provider response format
   - Verify prompt is generating JSON
   - Check logs for actual response

3. **"AI service error: API call failed"**
   - Verify API key is valid
   - Check network connectivity
   - Verify API quota/limits

4. **Stages not appearing**
   - Check `is_pending_confirmation=True` in database
   - Verify stages were created (check logs)
   - Check frontend JavaScript console

### Debug Mode

Enable detailed logging:

```python
# In settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'general.ai_service': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

---

**Last Updated:** 2025-01-19  
**Version:** 1.0
