"""
JSON parsing utilities for AI responses.

Handles common patterns like markdown code blocks and JSON extraction.
"""

import json
import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_json_response(response_text: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Parse JSON from AI response text, handling markdown code blocks.
    
    Removes markdown code blocks (```json, ```) and extracts JSON.
    Falls back to extracting JSON array/object from text if direct parsing fails.
    
    Args:
        response_text: Raw response text from AI
        default: Default value to return if parsing fails (default: empty dict)
        
    Returns:
        Parsed JSON as dictionary
        
    Raises:
        ValueError: If JSON cannot be parsed and no default provided
    """
    if default is None:
        default = {}
    
    try:
        # Remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Try direct JSON parsing
        return json.loads(text)
        
    except json.JSONDecodeError as e:
        logger.debug(f"Direct JSON parsing failed, attempting extraction: {e}")
        
        # Try to extract JSON array or object from text
        json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', text)
        if json_match:
            try:
                extracted_json = json_match.group(0)
                return json.loads(extracted_json)
            except json.JSONDecodeError:
                pass
        
        # If all parsing fails, log and return default
        logger.error(f"Failed to parse JSON from response: {e}")
        logger.debug(f"Raw response (first 500 chars): {response_text[:500]}")
        
        if default is not None:
            return default
        raise ValueError(f"Invalid JSON response: {e}")


def extract_json_array(response_text: str) -> list:
    """Extract JSON array from response text.
    
    Args:
        response_text: Raw response text
        
    Returns:
        Parsed JSON array
        
    Raises:
        ValueError: If no valid JSON array found
    """
    parsed = parse_json_response(response_text)
    
    # Handle both direct array and object with 'suggestions' field
    if isinstance(parsed, list):
        return parsed
    elif isinstance(parsed, dict) and 'suggestions' in parsed:
        return parsed['suggestions']
    else:
        raise ValueError("Response must be a JSON array or object with 'suggestions' field")

