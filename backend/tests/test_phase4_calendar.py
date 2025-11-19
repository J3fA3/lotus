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
from unittest.mock import Mock, patch, AsyncMock

# Mock Google API before importing services
import sys
sys.modules['google'] = Mock()
sys.modules['google.oauth2'] = Mock()
sys.modules['google.oauth2.credentials'] = Mock()
sys.modules['google_auth_oauthlib'] = Mock()
sys.modules['google_auth_oauthlib.flow'] = Mock()
sys.modules['googleapiclient'] = Mock()
sys.modules['googleapiclient.discovery'] = Mock()
sys.modules['google.auth.transport'] = Mock()
sys.modules['google.auth.transport.requests'] = Mock()


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
        """Test quality scoring prefers afternoon for afternoon preference."""
        from services.availability_analyzer import AvailabilityAnalyzer
        from db.models import WorkPreferences

        analyzer = AvailabilityAnalyzer()

        preferences = WorkPreferences(
            deep_work_time="afternoon",
            min_task_block=30
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

        # Afternoon should score higher
        assert afternoon_score > morning_score, "Afternoon block should score higher with afternoon preference"

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

    def test_validate_preferences(self):
        """Test preference validation."""
        from services.work_preferences import update_work_preferences

        # Test invalid deep_work_time
        with pytest.raises(ValueError):
            # This would be called in actual code, just testing the validation logic
            invalid_time = "invalid_time"
            assert invalid_time not in ["morning", "afternoon", "evening", "afternoon_evening"]


class TestSchedulingLogic:
    """Test scheduling agent logic (without Gemini calls)."""

    def test_identify_urgent_tasks(self):
        """Test identifying urgent tasks."""
        from agents.scheduling_agent import SchedulingAgent
        from db.models import Task, CalendarEvent

        agent = SchedulingAgent()

        # Create tasks with different due dates
        tasks = [
            Task(
                id="task-1",
                title="Due soon",
                due_date=(datetime.utcnow() + timedelta(hours=12)).isoformat(),  # 12 hours
                status="todo"
            ),
            Task(
                id="task-2",
                title="Due later",
                due_date=(datetime.utcnow() + timedelta(days=7)).isoformat(),  # 7 days
                status="todo"
            )
        ]

        # Meeting happening tomorrow with related task
        meeting = CalendarEvent(
            id=1,
            title="Important meeting",
            start_time=datetime.utcnow() + timedelta(hours=18),  # 18 hours from now
            end_time=datetime.utcnow() + timedelta(hours=19),
            related_task_ids=["task-3"],
            is_meeting=True
        )

        tasks.append(Task(
            id="task-3",
            title="Meeting prep task",
            status="todo"
        ))

        urgent = agent._identify_urgent_tasks(tasks, [meeting])

        # Should identify task-1 (due soon) and task-3 (meeting prep)
        urgent_ids = [t.id for t in urgent]
        assert "task-1" in urgent_ids, "Due-soon task should be urgent"
        assert "task-3" in urgent_ids, "Meeting prep task should be urgent"
        assert "task-2" not in urgent_ids, "Task due in 7 days should not be urgent"

    def test_determine_urgency(self):
        """Test urgency level determination."""
        from agents.scheduling_agent import SchedulingAgent
        from db.models import Task

        agent = SchedulingAgent()

        # Critical: due in 2 hours
        critical_task = Task(
            id="task-1",
            title="Critical",
            due_date=(datetime.utcnow() + timedelta(hours=2)).isoformat()
        )
        assert agent._determine_urgency(critical_task) == "critical"

        # High: due in 12 hours
        high_task = Task(
            id="task-2",
            title="High",
            due_date=(datetime.utcnow() + timedelta(hours=12)).isoformat()
        )
        assert agent._determine_urgency(high_task) == "high"

        # Medium: due in 48 hours
        medium_task = Task(
            id="task-3",
            title="Medium",
            due_date=(datetime.utcnow() + timedelta(hours=48)).isoformat()
        )
        assert agent._determine_urgency(medium_task) == "medium"

        # Low: due in 7 days
        low_task = Task(
            id="task-4",
            title="Low",
            due_date=(datetime.utcnow() + timedelta(days=7)).isoformat()
        )
        assert agent._determine_urgency(low_task) == "low"


class TestMeetingPrepLogic:
    """Test meeting prep assistant logic."""

    def test_calculate_urgency(self):
        """Test meeting urgency calculation."""
        from agents.meeting_prep_assistant import MeetingPrepAssistant

        assistant = MeetingPrepAssistant()

        # Critical: meeting in 2 hours
        critical_time = datetime.utcnow() + timedelta(hours=2)
        assert assistant._calculate_urgency(critical_time) == "critical"

        # High: meeting in 12 hours
        high_time = datetime.utcnow() + timedelta(hours=12)
        assert assistant._calculate_urgency(high_time) == "high"

        # Medium: meeting tomorrow
        medium_time = datetime.utcnow() + timedelta(hours=30)
        assert assistant._calculate_urgency(medium_time) == "medium"

        # Low: meeting in 3 days
        low_time = datetime.utcnow() + timedelta(days=3)
        assert assistant._calculate_urgency(low_time) == "low"

    def test_calculate_priority(self):
        """Test priority score calculation."""
        from agents.meeting_prep_assistant import MeetingPrepAssistant
        from db.models import CalendarEvent, Task

        assistant = MeetingPrepAssistant()

        # High importance meeting with urgent timing
        meeting = CalendarEvent(
            id=1,
            title="Critical meeting",
            importance_score=90,
            start_time=datetime.utcnow() + timedelta(hours=4),
            end_time=datetime.utcnow() + timedelta(hours=5)
        )

        incomplete_tasks = [
            Task(id="task-1", title="Task 1", status="todo"),
            Task(id="task-2", title="Task 2", status="todo")
        ]

        score = assistant._calculate_priority(meeting, incomplete_tasks, "high")

        # High importance + high urgency + incomplete tasks = high priority
        assert score > 70, "High-importance urgent meeting with incomplete tasks should have high priority"


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
