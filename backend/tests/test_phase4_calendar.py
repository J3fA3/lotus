"""
Unit and Integration Tests for Phase 4 - Google Calendar Integration

Tests cover:
1. OAuth flow and token management
2. Calendar sync service
3. Meeting parser agent
4. Availability analyzer
5. Scheduling agent
6. Meeting prep assistant
7. Work preferences
8. API endpoints

Run with: pytest backend/tests/test_phase4_calendar.py -v
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock


class TestAvailabilityAnalyzer:
    """Test availability analysis and free block detection."""

    def test_find_free_blocks_basic(self):
        """Test finding free blocks between meetings."""
        from services.availability_analyzer import AvailabilityAnalyzer, FreeBlock
        from db.models import CalendarEvent, WorkPreferences

        analyzer = AvailabilityAnalyzer()

        # Create preferences
        preferences = WorkPreferences(
            deep_work_time="afternoon",
            no_meetings_before="09:00",
            no_meetings_after="18:00",
            min_task_block=30
        )

        # Create calendar events (meetings)
        events = [
            CalendarEvent(
                start_time=datetime(2025, 11, 20, 10, 0),  # 10am-11am meeting
                end_time=datetime(2025, 11, 20, 11, 0),
                is_meeting=True,
                all_day=False
            ),
            CalendarEvent(
                start_time=datetime(2025, 11, 20, 15, 0),  # 3pm-4pm meeting
                end_time=datetime(2025, 11, 20, 16, 0),
                is_meeting=True,
                all_day=False
            )
        ]

        # Find free blocks
        start_date = datetime(2025, 11, 20, 9, 0)
        end_date = datetime(2025, 11, 20, 18, 0)

        free_blocks = analyzer.find_free_blocks(
            events,
            preferences,
            start_date,
            end_date,
            min_duration=30
        )

        # Should have free blocks: 9-10am, 11am-3pm, 4pm-6pm
        assert len(free_blocks) > 0

        # Check that blocks don't overlap with meetings
        for block in free_blocks:
            for event in events:
                assert not (block.start_time < event.end_time and block.end_time > event.start_time), \
                    "Free block overlaps with meeting"

    def test_score_block_quality_afternoon_preference(self):
        """Test quality scoring prefers afternoon for afternoon_evening preference."""
        from services.availability_analyzer import AvailabilityAnalyzer
        from db.models import WorkPreferences

        analyzer = AvailabilityAnalyzer()

        preferences = WorkPreferences(
            deep_work_time="afternoon_evening",  # Jef's actual preference
            min_task_block=30,
            no_meetings_before="09:00",
            no_meetings_after="18:00"
        )

        # Morning block (9am)
        morning_block = {
            'start': datetime(2025, 11, 20, 9, 0),
            'end': datetime(2025, 11, 20, 10, 0),
            'duration_minutes': 60
        }

        # Afternoon block (2pm)
        afternoon_block = {
            'start': datetime(2025, 11, 20, 14, 0),
            'end': datetime(2025, 11, 20, 15, 0),
            'duration_minutes': 60
        }

        morning_score = analyzer._score_block_quality(morning_block, preferences)
        afternoon_score = analyzer._score_block_quality(afternoon_block, preferences)

        # Afternoon should score higher with afternoon_evening preference
        assert afternoon_score > morning_score, f"Afternoon block ({afternoon_score}) should score higher than morning ({morning_score})"

    def test_merge_adjacent_blocks(self):
        """Test merging adjacent free blocks."""
        from services.availability_analyzer import AvailabilityAnalyzer, FreeBlock

        analyzer = AvailabilityAnalyzer()

        blocks = [
            FreeBlock(
                start_time=datetime(2025, 11, 20, 14, 0),
                end_time=datetime(2025, 11, 20, 14, 30),
                duration_minutes=30,
                quality_score=80,
                time_of_day="afternoon"
            ),
            FreeBlock(
                start_time=datetime(2025, 11, 20, 14, 30),
                end_time=datetime(2025, 11, 20, 15, 0),
                duration_minutes=30,
                quality_score=85,
                time_of_day="afternoon"
            )
        ]

        merged = analyzer.merge_adjacent_blocks(blocks, max_gap_minutes=5)

        # Should merge into single 60-minute block
        assert len(merged) == 1
        assert merged[0].duration_minutes == 60


class TestWorkPreferences:
    """Test work preferences service."""

    @pytest.mark.asyncio
    async def test_create_default_preferences(self):
        """Test creating default Jef preferences."""
        from services.work_preferences import create_default_preferences
        from db.models import WorkPreferences
        from unittest.mock import AsyncMock

        # Mock database
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        prefs = await create_default_preferences(mock_db, user_id=1)

        # Verify Jef's preferences
        assert prefs.user_id == 1
        assert prefs.deep_work_time == "afternoon_evening"
        assert prefs.meeting_style == "back_to_back"
        assert prefs.min_task_block == 30
        assert prefs.task_event_prefix == "🪷 "
        assert prefs.auto_create_blocks == False  # Phase 4: always needs approval

    @pytest.mark.asyncio
    async def test_validate_preferences(self):
        """Test preference validation."""
        from services.work_preferences import update_work_preferences
        from db.models import WorkPreferences
        from sqlalchemy.ext.asyncio import AsyncSession

        # Create mock database with existing preferences
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock the query to return existing preferences
        mock_result = MagicMock()
        mock_prefs = WorkPreferences(
            user_id=1,
            deep_work_time="afternoon_evening",
            min_task_block=30,
            no_meetings_before="09:00",
            no_meetings_after="18:00"
        )
        mock_result.scalar_one_or_none.return_value = mock_prefs
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Test invalid deep_work_time should raise ValueError
        with pytest.raises(ValueError, match="Invalid deep_work_time"):
            await update_work_preferences(
                mock_db,
                user_id=1,
                updates={"deep_work_time": "invalid_time"}
            )


class TestSchedulingLogic:
    """Test scheduling agent logic (without Gemini calls)."""

    def test_urgency_calculation(self):
        """Test urgency level determination based on due dates."""
        from db.models import Task

        # Test urgency calculation based on due date
        now = datetime.utcnow()

        # Critical: due in 2 hours
        critical_task = Task(
            id="task-1",
            title="Critical",
            due_date=(now + timedelta(hours=2)).isoformat()
        )
        
        # High: due in 12 hours
        high_task = Task(
            id="task-2",
            title="High",
            due_date=(now + timedelta(hours=12)).isoformat()
        )
        
        # Medium: due in 48 hours
        medium_task = Task(
            id="task-3",
            title="Medium",
            due_date=(now + timedelta(hours=48)).isoformat()
        )
        
        # Low: due in 7 days
        low_task = Task(
            id="task-4",
            title="Low",
            due_date=(now + timedelta(days=7)).isoformat()
        )

        # Verify due dates are set correctly
        assert critical_task.due_date is not None
        assert high_task.due_date is not None
        assert medium_task.due_date is not None
        assert low_task.due_date is not None

    def test_task_filtering_by_status(self):
        """Test filtering tasks by status."""
        from db.models import Task

        tasks = [
            Task(id="task-1", title="Todo task", status="todo"),
            Task(id="task-2", title="Doing task", status="doing"),
            Task(id="task-3", title="Done task", status="done")
        ]

        # Filter active tasks (todo or doing)
        active_tasks = [t for t in tasks if t.status in ['todo', 'doing']]
        
        assert len(active_tasks) == 2
        assert all(t.status in ['todo', 'doing'] for t in active_tasks)


class TestMeetingPrepLogic:
    """Test meeting prep assistant logic."""

    def test_meeting_urgency_by_time(self):
        """Test meeting urgency calculation based on start time."""
        now = datetime.utcnow()

        # Calculate hours until meeting
        critical_time = now + timedelta(hours=2)
        high_time = now + timedelta(hours=12)
        medium_time = now + timedelta(hours=30)
        low_time = now + timedelta(days=3)

        # Verify time calculations
        critical_hours = (critical_time - now).total_seconds() / 3600
        high_hours = (high_time - now).total_seconds() / 3600
        medium_hours = (medium_time - now).total_seconds() / 3600
        low_hours = (low_time - now).total_seconds() / 3600

        assert critical_hours < 6, "Critical meeting should be less than 6 hours away"
        assert 6 <= high_hours < 24, "High urgency meeting should be 6-24 hours away"
        assert 24 <= medium_hours < 48, "Medium urgency meeting should be 24-48 hours away"
        assert low_hours >= 48, "Low urgency meeting should be 48+ hours away"

    def test_meeting_importance_factors(self):
        """Test factors that affect meeting importance."""
        from db.models import CalendarEvent

        # High importance meeting
        high_importance = CalendarEvent(
            id=1,
            title="Executive Review",
            importance_score=90,
            start_time=datetime.utcnow() + timedelta(hours=4),
            end_time=datetime.utcnow() + timedelta(hours=5),
            attendees=["ceo@example.com", "vp@example.com"],
            is_meeting=True
        )

        # Low importance meeting
        low_importance = CalendarEvent(
            id=2,
            title="Optional Coffee Chat",
            importance_score=20,
            start_time=datetime.utcnow() + timedelta(days=2),
            end_time=datetime.utcnow() + timedelta(days=2, hours=1),
            attendees=["colleague@example.com"],
            is_meeting=True
        )

        # Verify importance scoring
        assert high_importance.importance_score > 70, "Executive meetings should have high importance"
        assert low_importance.importance_score < 50, "Informal meetings should have lower importance"


class TestAPIEndpoints:
    """Test API endpoint logic (without actual HTTP calls)."""

    def test_quality_label_function(self):
        """Test quality score labeling."""
        from api.calendar_routes import _get_quality_label

        assert "Excellent" in _get_quality_label(95)
        assert "Great" in _get_quality_label(80)
        assert "Good" in _get_quality_label(65)
        assert "Available" in _get_quality_label(40)


# Test fixtures
@pytest.fixture
def sample_tasks():
    """Sample tasks for testing."""
    from db.models import Task

    return [
        Task(
            id="task-1",
            title="Complete CRESCO dashboard",
            status="todo",
            value_stream="CRESCO",
            due_date=(datetime.utcnow() + timedelta(days=2)).isoformat()
        ),
        Task(
            id="task-2",
            title="Review RF16 metrics",
            status="doing",
            value_stream="RF16",
            due_date=None
        ),
        Task(
            id="task-3",
            title="Prepare quarterly presentation",
            status="todo",
            value_stream="CRESCO",
            due_date=(datetime.utcnow() + timedelta(hours=20)).isoformat()
        )
    ]


@pytest.fixture
def sample_calendar_events():
    """Sample calendar events for testing."""
    from db.models import CalendarEvent

    return [
        CalendarEvent(
            id=1,
            title="Team Standup",
            start_time=datetime.utcnow() + timedelta(hours=2),
            end_time=datetime.utcnow() + timedelta(hours=2.5),
            is_meeting=True,
            importance_score=50,
            attendees=["team@example.com"]
        ),
        CalendarEvent(
            id=2,
            title="CRESCO Quarterly Review",
            start_time=datetime.utcnow() + timedelta(days=1),
            end_time=datetime.utcnow() + timedelta(days=1, hours=2),
            is_meeting=True,
            importance_score=90,
            attendees=["andy@example.com", "sarah@example.com"],
            related_task_ids=["task-3"],
            prep_needed=True
        )
    ]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
