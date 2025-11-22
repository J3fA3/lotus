# Timezone Fix Summary - Critical Bug Resolution

## 🚨 Critical Bug: "can't compare offset-naive and offset-aware datetimes"

### Root Cause
Multiple locations in the codebase were using `datetime.utcnow()` which creates **naive datetimes** (no timezone), but these were being compared with **timezone-aware datetimes** from:
- Calendar events (stored as timezone-aware)
- Task due dates (parsed as timezone-aware)
- Free blocks (generated as timezone-aware)

Python cannot compare naive and timezone-aware datetimes, causing the error.

---

## ✅ Fixes Applied

### 1. **Scheduling Agent** (`backend/agents/scheduling_agent.py`)

**Fixed Locations:**
- Line 207: `now = datetime.utcnow()` → `now = datetime.now(timezone.utc)`
- Line 218: Added timezone check for `due` date before comparison
- Line 229: Added timezone check for `event.start_time` before comparison
- Line 581: `datetime.utcnow()` → `datetime.now(timezone.utc)` with timezone check for `due`
- Line 636: Fixed task sorting to use timezone-aware due dates

**Changes:**
```python
# BEFORE (naive)
now = datetime.utcnow()
hours_until_due = (due - now).total_seconds() / 3600

# AFTER (timezone-aware)
now = datetime.now(timezone.utc)
if due.tzinfo is None:
    due = due.replace(tzinfo=timezone.utc)
hours_until_due = (due - now).total_seconds() / 3600
```

### 2. **Meeting Prep Assistant** (`backend/agents/meeting_prep_assistant.py`)

**Fixed Locations:**
- Line 127: `datetime.utcnow()` → `datetime.now(timezone.utc)`
- Line 286: Fixed comparison with timezone-aware `meeting_time`

**Changes:**
```python
# BEFORE
start_time = datetime.utcnow()
hours_until = (meeting_time - datetime.utcnow()).total_seconds() / 3600

# AFTER
from datetime import timezone
start_time = datetime.now(timezone.utc)
now = datetime.now(timezone.utc)
if meeting_time.tzinfo is None:
    meeting_time = meeting_time.replace(tzinfo=timezone.utc)
hours_until = (meeting_time - now).total_seconds() / 3600
```

### 3. **Meeting Parser** (`backend/agents/meeting_parser.py`)

**Fixed Location:**
- Line 323: `datetime.utcnow()` → `datetime.now(timezone.utc)`

### 4. **Calendar Sync Service** (`backend/services/calendar_sync.py`)

**Fixed Locations:**
- Line 75: `datetime.utcnow()` → `datetime.now(timezone.utc)`
- Line 205-206: `datetime.utcnow()` → `datetime.now(timezone.utc)`

### 5. **Calendar Routes** (`backend/api/calendar_routes.py`)

**Fixed Location:**
- Line 303: `datetime.utcnow()` → `datetime.now(timezone.utc)`

### 6. **Task Sorting in Fallback Scheduling**

**Fixed:**
- Added helper function `get_due_date_for_sort()` to normalize due dates
- Ensures all due dates are timezone-aware before sorting
- Prevents comparison errors when sorting tasks

---

## 🔍 Pattern for Future Fixes

**Always use timezone-aware datetimes:**
```python
# ❌ WRONG (naive)
now = datetime.utcnow()
date = datetime.fromisoformat("2025-01-01T10:00:00")

# ✅ CORRECT (timezone-aware)
from datetime import timezone
now = datetime.now(timezone.utc)
date = datetime.fromisoformat("2025-01-01T10:00:00Z").replace(tzinfo=timezone.utc)

# ✅ Also ensure comparisons are safe
if date.tzinfo is None:
    date = date.replace(tzinfo=timezone.utc)
```

---

## 🧪 Testing Checklist

After these fixes, test:
1. ✅ Scheduling suggestions generation
2. ✅ Urgent task detection (due dates)
3. ✅ Meeting prep urgency calculation
4. ✅ Calendar event parsing
5. ✅ Task sorting by due date

---

## 📝 Files Modified

1. `backend/agents/scheduling_agent.py` - 5 fixes
2. `backend/agents/meeting_prep_assistant.py` - 2 fixes
3. `backend/agents/meeting_parser.py` - 1 fix
4. `backend/services/calendar_sync.py` - 2 fixes
5. `backend/api/calendar_routes.py` - 1 fix

**Total:** 11 timezone fixes across 5 files

---

## 🎯 Result

All datetime operations are now timezone-aware and consistent. The error "can't compare offset-naive and offset-aware datetimes" should be completely resolved.

**Next Steps:**
1. Test scheduling functionality
2. Monitor backend logs for any remaining timezone issues
3. If issues persist, check database models to ensure stored datetimes are timezone-aware

