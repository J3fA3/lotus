"""
Field Extractor Service

This service extracts task fields from natural language context:
- Due dates: "Friday" → next Friday, "end of month" → last day of month
- Priorities: "urgent" → high, "soon" → medium, default → medium
- Tags: Query knowledge graph for project names
- Status: Default 'todo'

The extractor uses a combination of:
1. Pattern matching for common date/priority phrases
2. LLM-based extraction for complex cases
3. Knowledge graph queries for project/team tags

If a field is ambiguous, it returns None rather than guessing.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import re
import httpx
import json

from db.models import Entity


# Priority keywords mapping
PRIORITY_KEYWORDS = {
    "high": ["urgent", "asap", "critical", "important", "high priority", "immediately"],
    "medium": ["soon", "medium priority", "moderate", "normal"],
    "low": ["low priority", "whenever", "eventually", "nice to have"]
}

# Status keywords (for detecting status updates)
STATUS_KEYWORDS = {
    "todo": ["todo", "to do", "not started", "pending"],
    "doing": ["doing", "in progress", "working on", "started"],
    "done": ["done", "completed", "finished", "closed"]
}


class FieldExtractor:
    """Extracts task fields from natural language context.

    This service parses context and entities to populate task fields
    intelligently without requiring structured input.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        """Initialize field extractor.

        Args:
            db: Optional database session for knowledge graph queries
        """
        self.db = db

    async def extract_fields(
        self,
        context: str,
        entities: List[Dict],
        proposed_task: Optional[Dict] = None
    ) -> Dict:
        """Extract task fields from context and entities.

        Args:
            context: Raw context text
            entities: Extracted entities from context
            proposed_task: Optional proposed task data (for enrichment)

        Returns:
            Dictionary with extracted fields:
            {
                "due_date": "2025-11-22" or None,
                "priority": "high" | "medium" | "low" or None,
                "tags": ["CRESCO", "Menu Team"] or [],
                "status": "todo" | "doing" | "done",
                "assignee": "Jef Adriaenssens" or None,
                "value_stream": "CRESCO" or None
            }
        """
        fields = {}

        # Extract due date
        fields["due_date"] = await self.extract_due_date(context, entities)

        # Extract priority
        fields["priority"] = self.extract_priority(context)

        # Extract tags from entities (projects, teams)
        fields["tags"] = await self.extract_tags(entities)

        # Extract status (if mentioned)
        fields["status"] = self.extract_status(context) or "todo"

        # Extract assignee from PERSON entities
        fields["assignee"] = self.extract_assignee(entities)

        # Extract value stream (primary project)
        fields["value_stream"] = self.extract_value_stream(entities)

        return fields

    async def extract_due_date(
        self,
        context: str,
        entities: List[Dict]
    ) -> Optional[str]:
        """Extract due date from context.

        Handles common date patterns:
        - "Friday" → next Friday
        - "tomorrow" → tomorrow's date
        - "next week" → 7 days from now
        - "end of month" → last day of current month
        - "November 26th" → 2025-11-26
        - DATE entities from entity extraction

        Args:
            context: Raw context text
            entities: Extracted entities (may include DATE type)

        Returns:
            ISO date string (YYYY-MM-DD) or None if no date found
        """
        context_lower = context.lower()

        # Check for DATE entities first
        date_entities = [e for e in entities if e.get("type") == "DATE"]
        if date_entities:
            # Try to parse the first DATE entity
            date_str = date_entities[0].get("name", "")
            parsed_date = self._parse_date_string(date_str)
            if parsed_date:
                return parsed_date

        # Pattern 1: "tomorrow"
        if "tomorrow" in context_lower:
            tomorrow = datetime.now() + timedelta(days=1)
            return tomorrow.strftime("%Y-%m-%d")

        # Pattern 2: Day of week (e.g., "Friday", "next Monday")
        weekday_match = re.search(
            r'\b(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            context_lower
        )
        if weekday_match:
            is_next_week = weekday_match.group(1) is not None
            weekday_name = weekday_match.group(2)
            target_date = self._get_next_weekday(weekday_name, is_next_week)
            return target_date.strftime("%Y-%m-%d")

        # Pattern 3: "end of month" / "month end"
        if re.search(r'\b(end of month|month end|eom)\b', context_lower):
            today = datetime.now()
            # Get last day of current month
            next_month = today.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            return last_day.strftime("%Y-%m-%d")

        # Pattern 4: "next week"
        if "next week" in context_lower:
            next_week = datetime.now() + timedelta(days=7)
            return next_week.strftime("%Y-%m-%d")

        # Pattern 5: "in X days"
        days_match = re.search(r'\bin\s+(\d+)\s+days?\b', context_lower)
        if days_match:
            days = int(days_match.group(1))
            target = datetime.now() + timedelta(days=days)
            return target.strftime("%Y-%m-%d")

        # Pattern 6: Specific date format (Nov 26, November 26th, 11/26, etc.)
        date_pattern_match = re.search(
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b',
            context_lower
        )
        if date_pattern_match:
            month_abbr = date_pattern_match.group(1)
            day = int(date_pattern_match.group(2))
            parsed = self._parse_month_day(month_abbr, day)
            if parsed:
                return parsed

        return None

    def _parse_date_string(self, date_str: str) -> Optional[str]:
        """Parse a date string from entity extraction.

        Args:
            date_str: Date string (e.g., "November 26th", "Friday")

        Returns:
            ISO date string or None
        """
        date_str_lower = date_str.lower()

        # Try specific date patterns first
        month_day_match = re.search(
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})',
            date_str_lower
        )
        if month_day_match:
            month_abbr = month_day_match.group(1)
            day = int(month_day_match.group(2))
            return self._parse_month_day(month_abbr, day)

        # Try weekday patterns
        weekday_match = re.search(
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            date_str_lower
        )
        if weekday_match:
            weekday_name = weekday_match.group(1)
            is_next_week = "next" in date_str_lower
            target_date = self._get_next_weekday(weekday_name, is_next_week)
            return target_date.strftime("%Y-%m-%d")

        return None

    def _parse_month_day(self, month_abbr: str, day: int) -> Optional[str]:
        """Parse month abbreviation and day into ISO date.

        Args:
            month_abbr: Month abbreviation (jan, feb, etc.)
            day: Day of month

        Returns:
            ISO date string or None
        """
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4,
            "may": 5, "jun": 6, "jul": 7, "aug": 8,
            "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }

        month = month_map.get(month_abbr[:3])
        if not month:
            return None

        # Assume current year, or next year if date has passed
        today = datetime.now()
        year = today.year

        try:
            target_date = datetime(year, month, day)
            # If date has passed, use next year
            if target_date < today:
                target_date = datetime(year + 1, month, day)
            return target_date.strftime("%Y-%m-%d")
        except ValueError:
            return None

    def _get_next_weekday(self, weekday_name: str, is_next_week: bool = False) -> datetime:
        """Get the date of the next occurrence of a weekday.

        Args:
            weekday_name: Name of weekday (monday, tuesday, etc.)
            is_next_week: If True, get weekday from next week

        Returns:
            datetime object for the target weekday
        """
        weekday_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }

        target_weekday = weekday_map[weekday_name.lower()]
        today = datetime.now()
        current_weekday = today.weekday()

        # Calculate days until target weekday
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0:  # Target day has passed this week
            days_ahead += 7

        if is_next_week:
            days_ahead += 7

        return today + timedelta(days=days_ahead)

    def extract_priority(self, context: str) -> Optional[str]:
        """Extract priority from context.

        Args:
            context: Raw context text

        Returns:
            "high", "medium", "low", or None
        """
        context_lower = context.lower()

        # Check for high priority keywords
        for keyword in PRIORITY_KEYWORDS["high"]:
            if keyword in context_lower:
                return "high"

        # Check for low priority keywords
        for keyword in PRIORITY_KEYWORDS["low"]:
            if keyword in context_lower:
                return "low"

        # Check for medium priority keywords
        for keyword in PRIORITY_KEYWORDS["medium"]:
            if keyword in context_lower:
                return "medium"

        # Default: medium priority for most tasks
        # Return None to let orchestrator decide
        return None

    async def extract_tags(self, entities: List[Dict]) -> List[str]:
        """Extract tags from entities (projects, teams).

        Args:
            entities: Extracted entities

        Returns:
            List of tag strings
        """
        tags = []

        # Extract PROJECT entities as tags
        projects = [e.get("name") for e in entities if e.get("type") == "PROJECT"]
        tags.extend(projects)

        # Extract TEAM entities as tags
        teams = [e.get("name") for e in entities if e.get("type") == "TEAM"]
        tags.extend(teams)

        # Remove duplicates, preserve order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag and tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)

        return unique_tags

    def extract_status(self, context: str) -> Optional[str]:
        """Extract status from context if explicitly mentioned.

        Args:
            context: Raw context text

        Returns:
            "todo", "doing", "done", or None
        """
        context_lower = context.lower()

        # Check for status keywords
        for status, keywords in STATUS_KEYWORDS.items():
            for keyword in keywords:
                if keyword in context_lower:
                    # Additional check: is this about task status?
                    # Look for phrases like "is done", "status is", etc.
                    if re.search(rf'\b(is|status|now)\s+{re.escape(keyword)}\b', context_lower):
                        return status

        return None

    def extract_assignee(self, entities: List[Dict]) -> Optional[str]:
        """Extract assignee from PERSON entities.

        Heuristic: First PERSON mentioned is likely the assignee.

        Args:
            entities: Extracted entities

        Returns:
            Assignee name or None
        """
        # Get all PERSON entities
        people = [e.get("name") for e in entities if e.get("type") == "PERSON"]

        if not people:
            return None

        # Return first person (most likely assignee)
        # Future improvement: Use context to determine correct assignee
        return people[0]

    def extract_value_stream(self, entities: List[Dict]) -> Optional[str]:
        """Extract value stream (primary project) from entities.

        Heuristic: First PROJECT mentioned is the value stream.

        Args:
            entities: Extracted entities

        Returns:
            Value stream name or None
        """
        # Get all PROJECT entities
        projects = [e.get("name") for e in entities if e.get("type") == "PROJECT"]

        if not projects:
            return None

        # Return first project as value stream
        return projects[0]

    async def enrich_with_llm(self, context: str, existing_fields: Dict) -> Dict:
        """Use LLM to extract fields that pattern matching missed.

        This is a fallback for complex cases where pattern matching fails.

        Args:
            context: Raw context text
            existing_fields: Fields already extracted

        Returns:
            Dictionary with additional/refined fields
        """
        # Build prompt for LLM
        prompt = f"""Extract task fields from this context. Return JSON only.

Context: {context}

Already extracted fields:
{json.dumps(existing_fields, indent=2)}

Extract any missing fields:
- due_date: ISO date (YYYY-MM-DD) or null
- priority: "high" | "medium" | "low" or null
- assignee: Person's full name or null
- value_stream: Project name or null

Output ONLY this JSON format:
{{"due_date": "2025-11-22", "priority": "high", "assignee": "Jef Adriaenssens", "value_stream": "CRESCO"}}

DO NOT include explanation.
"""

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "qwen2.5:7b-instruct",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                )

                result = response.json()
                response_text = result.get("response", "")

                # Parse JSON from response
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]

                llm_fields = json.loads(response_text.strip())

                # Merge with existing fields (existing takes precedence)
                for key, value in llm_fields.items():
                    if key not in existing_fields or existing_fields[key] is None:
                        existing_fields[key] = value

                return existing_fields

        except Exception:
            # LLM extraction failed, return existing fields
            return existing_fields
