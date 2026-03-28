"""
AI Service - Business logic for AI recipe generation.

This service encapsulates all AI-related operations including:
- Recipe generation from prompts
- Surprise recipe generation
- AI response parsing
- API validation and error handling
"""

import re
from typing import Tuple, Optional
from django.conf import settings
import openai


class AIServiceException(Exception):
    """Base exception for AI service errors."""
    pass


class AIConfigurationError(AIServiceException):
    """Raised when AI service is not properly configured."""
    pass


class AIValidationError(AIServiceException):
    """Raised when input validation fails."""
    pass


class AIAPIError(AIServiceException):
    """Raised when AI API call fails."""
    pass


class AIService:
    """Service for AI recipe generation operations."""

    MAX_PROMPT_LENGTH = 500
    GPT_MODEL = "gpt-4"
    TEMPERATURE = 0.7

    @staticmethod
    def validate_api_key() -> None:
        """
        Validate that OpenAI API key is configured.

        Raises:
            AIConfigurationError: If API key is not configured
        """
        if not settings.OPENAI_API_KEY or not settings.OPENAI_API_KEY.strip():
            raise AIConfigurationError(
                "AI recipe generation is not currently available. "
                "Please configure the OpenAI API key."
            )

    @staticmethod
    def validate_prompt(prompt: str) -> str:
        """
        Validate and clean a user prompt.

        Args:
            prompt: The user's input prompt

        Returns:
            Cleaned prompt string

        Raises:
            AIValidationError: If prompt is invalid
        """
        if not prompt or not prompt.strip():
            raise AIValidationError("Please provide ingredients or an idea for the recipe.")

        cleaned_prompt = prompt.strip()

        if len(cleaned_prompt) > AIService.MAX_PROMPT_LENGTH:
            raise AIValidationError(
                f"Prompt is too long. Please limit to {AIService.MAX_PROMPT_LENGTH} characters."
            )

        return cleaned_prompt

    @staticmethod
    def generate_recipe_from_prompt(prompt: str) -> str:
        """
        Generate a recipe using AI based on a user prompt.

        Args:
            prompt: User's input describing ingredients or recipe idea

        Returns:
            Generated recipe text

        Raises:
            AIConfigurationError: If API key is not configured
            AIValidationError: If prompt is invalid
            AIAPIError: If API call fails
        """
        # Validate configuration
        AIService.validate_api_key()

        # Validate and clean prompt
        cleaned_prompt = AIService.validate_prompt(prompt)

        # Build the full prompt
        full_prompt = (
            f"Create a family-friendly recipe using: {cleaned_prompt}. "
            f"Include a title, ingredients, and clear steps. Format as:\n"
            f"Title:\nIngredients:\nSteps:"
        )

        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=AIService.GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You're a helpful chef assistant."},
                    {"role": "user", "content": full_prompt},
                ],
                temperature=AIService.TEMPERATURE
            )

            content = response.choices[0].message.content
            if not content or not content.strip():
                raise AIAPIError("AI service returned empty response.")

            return content.strip()

        except openai.AuthenticationError:
            raise AIAPIError(
                "AI service authentication failed. Please check the API configuration."
            )
        except openai.RateLimitError:
            raise AIAPIError(
                "AI service is currently busy. Please try again in a few minutes."
            )
        except openai.APIError:
            raise AIAPIError(
                "AI service is temporarily unavailable. Please try again later."
            )
        except AIServiceException:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            raise AIAPIError("An unexpected error occurred. Please try again.")

    @staticmethod
    def generate_surprise_recipe() -> str:
        """
        Generate a random surprise recipe using AI.

        Returns:
            Generated recipe text

        Raises:
            AIConfigurationError: If API key is not configured
            AIAPIError: If API call fails
        """
        # Validate configuration
        AIService.validate_api_key()

        prompt = (
            "Create a fun, family-friendly surprise recipe. "
            "Include a title, ingredients, and clear steps. Format as:\n"
            "Title:\nIngredients:\nSteps:"
        )

        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=AIService.GPT_MODEL,
                messages=[
                    {"role": "system", "content": "You're a helpful chef assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=AIService.TEMPERATURE
            )

            content = response.choices[0].message.content
            if not content or not content.strip():
                raise AIAPIError("AI service returned empty response.")

            return content.strip()

        except openai.AuthenticationError:
            raise AIAPIError(
                "AI service authentication failed. Please check the API configuration."
            )
        except openai.RateLimitError:
            raise AIAPIError(
                "AI service is currently busy. Please try again in a few minutes."
            )
        except openai.APIError:
            raise AIAPIError(
                "AI service is temporarily unavailable. Please try again later."
            )
        except AIServiceException:
            # Re-raise our own exceptions
            raise
        except Exception:
            raise AIAPIError("An unexpected error occurred. Please try again.")

    @staticmethod
    def generate_structured_recipe(prompt):
        """Generate a recipe with structured ingredients from AI."""
        AIService.validate_api_key()
        clean_prompt = AIService.validate_prompt(prompt)

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model=AIService.GPT_MODEL,
            temperature=AIService.TEMPERATURE,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful chef. Return recipes as JSON with this exact structure: "
                        '{"title": "...", "description": "...", "prep_time": 10, "cook_time": 30, '
                        '"servings": 4, "difficulty": "easy|medium|hard", '
                        '"ingredients": [{"name": "chicken breast", "quantity": 500, "unit": "g", '
                        '"category": "meat", "preparation_notes": "diced"}], '
                        '"steps": ["Step 1 text", "Step 2 text"]}'
                        " Return ONLY valid JSON, no markdown or extra text."
                    )
                },
                {
                    "role": "user",
                    "content": f"Create a family-friendly recipe using: {clean_prompt}"
                }
            ]
        )

        import json
        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if content.startswith('```'):
            content = content.split('\n', 1)[1] if '\n' in content else content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()

        return json.loads(content)

    @staticmethod
    def parse_generated_recipe(text: str) -> Tuple[str, str, str]:
        """
        Parse AI-generated recipe text into structured components.

        Args:
            text: Raw AI-generated recipe text

        Returns:
            Tuple of (title, ingredients, steps)
        """
        title = ""
        ingredients = ""
        steps = ""

        # Match "Title: ..." on a single line
        title_match = re.search(r"Title:\s*(.+)", text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()

        # Match everything between "Ingredients:" and "Steps:" or "Directions:"
        ingredients_match = re.search(
            r"Ingredients:\s*([\s\S]*?)(?:\n(?:Steps:|Directions:))", text, re.IGNORECASE
        )
        if ingredients_match:
            ingredients = ingredients_match.group(1).strip()

        # Match everything after "Steps:" or "Directions:"
        steps_match = re.search(r"(?:Steps:|Directions:)\s*([\s\S]*)", text, re.IGNORECASE)
        if steps_match:
            steps = steps_match.group(1).strip()

        return title, ingredients, steps
