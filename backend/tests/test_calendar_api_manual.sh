#!/bin/bash
# Manual API Testing Script for Phase 4 - Google Calendar Integration
#
# This script tests the full Phase 4 workflow:
# 1. Check health
# 2. Get auth URL
# 3. Check auth status
# 4. Sync calendar (requires authorization first)
# 5. Get events
# 6. Get preferences
# 7. Generate scheduling suggestions
# 8. Get meeting prep suggestions
#
# Usage: ./test_calendar_api_manual.sh

BASE_URL="${BASE_URL:-http://localhost:8000}"
USER_ID=1

echo "======================================"
echo "Phase 4 API Manual Testing"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4

    echo -e "${YELLOW}Testing:${NC} $name"
    echo "  $method $endpoint"

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        if [ -z "$data" ]; then
            response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "\n%{http_code}" -X POST -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint")
        fi
    elif [ "$method" = "PATCH" ]; then
        response=$(curl -s -w "\n%{http_code}" -X PATCH -H "Content-Type: application/json" -d "$data" "$BASE_URL$endpoint")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "  ${GREEN}✓ Success${NC} ($http_code)"
        echo "  Response: $(echo $body | jq -C '.' 2>/dev/null || echo $body)" | head -n 5
    else
        echo -e "  ${RED}✗ Failed${NC} ($http_code)"
        echo "  Response: $body"
    fi
    echo ""
}

# 1. Check health
test_endpoint "Health Check" "GET" "/api/health"

# 2. Get work preferences
test_endpoint "Get Work Preferences" "GET" "/api/calendar/preferences?user_id=$USER_ID"

# 3. Check auth status
test_endpoint "Check Auth Status" "GET" "/api/auth/google/status?user_id=$USER_ID"

# 4. Get authorization URL (if not authorized)
echo -e "${YELLOW}Step: Get OAuth URL${NC}"
auth_response=$(curl -s "$BASE_URL/api/auth/google/authorize?user_id=$USER_ID")
auth_url=$(echo $auth_response | jq -r '.authorization_url' 2>/dev/null)

if [ "$auth_url" != "null" ] && [ -n "$auth_url" ]; then
    echo -e "  ${GREEN}✓ Authorization URL generated${NC}"
    echo "  URL: $auth_url"
    echo ""
    echo -e "${YELLOW}To authorize:${NC}"
    echo "  1. Visit: $auth_url"
    echo "  2. Grant access"
    echo "  3. Get redirected back to callback"
    echo ""
    echo -e "${YELLOW}After authorization, continue with:${NC}"
    echo "  - Sync calendar: curl -X POST $BASE_URL/api/calendar/sync?user_id=$USER_ID"
    echo "  - Get events: curl $BASE_URL/api/calendar/events?user_id=$USER_ID"
    echo ""
else
    echo -e "  ${RED}✗ Failed to get auth URL${NC}"
    echo ""
fi

# 5. Try to sync calendar (will fail if not authorized)
echo -e "${YELLOW}Note:${NC} Calendar sync requires authorization first"
test_endpoint "Sync Calendar (may fail if not authorized)" "POST" "/api/calendar/sync?user_id=$USER_ID"

# 6. Get calendar events
test_endpoint "Get Calendar Events" "GET" "/api/calendar/events?user_id=$USER_ID&days_ahead=7"

# 7. Get today's events
test_endpoint "Get Today's Events" "GET" "/api/calendar/events/today?user_id=$USER_ID"

# 8. Generate scheduling suggestions (requires tasks)
test_endpoint "Generate Scheduling Suggestions" "POST" "/api/calendar/schedule-tasks?user_id=$USER_ID"

# 9. Get meeting prep suggestions
test_endpoint "Get Meeting Prep Suggestions" "GET" "/api/calendar/meeting-prep?user_id=$USER_ID&days_ahead=3"

# 10. Update preferences
echo -e "${YELLOW}Testing:${NC} Update Preferences"
update_data='{"deep_work_time": "morning"}'
test_endpoint "Update Preferences (change to morning)" "PATCH" "/api/calendar/preferences?user_id=$USER_ID" "$update_data"

# 11. Reset preferences
test_endpoint "Reset Preferences to Defaults" "POST" "/api/calendar/preferences/reset?user_id=$USER_ID"

echo "======================================"
echo "Testing Complete"
echo "======================================"
echo ""
echo -e "${YELLOW}Full Workflow (after authorization):${NC}"
echo "1. Visit auth URL and authorize"
echo "2. curl -X POST $BASE_URL/api/calendar/sync?user_id=$USER_ID"
echo "3. curl $BASE_URL/api/calendar/events?user_id=$USER_ID | jq"
echo "4. curl -X POST $BASE_URL/api/calendar/schedule-tasks?user_id=$USER_ID | jq"
echo "5. curl $BASE_URL/api/calendar/meeting-prep?user_id=$USER_ID | jq"
echo "6. curl -X POST $BASE_URL/api/calendar/approve-block?block_id=1&user_id=$USER_ID"
echo ""
echo "View API docs: $BASE_URL/docs"
