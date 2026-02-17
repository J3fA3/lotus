"""
Application-wide constants and configuration values.
"""

# API Configuration
API_TITLE = "Lotus v2 API"
API_DESCRIPTION = "Intelligence Flywheel Task Board"
API_VERSION = "2.0.0"

# CORS Configuration
DEFAULT_CORS_ORIGINS = "http://localhost:5173"

# Server Configuration
DEFAULT_API_HOST = "0.0.0.0"
DEFAULT_API_PORT = 8000

# Task Statuses
TASK_STATUS_TODO = "todo"
TASK_STATUS_DOING = "doing"
TASK_STATUS_DONE = "done"

VALID_TASK_STATUSES = {
    TASK_STATUS_TODO,
    TASK_STATUS_DOING,
    TASK_STATUS_DONE,
}
