#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000/api/v1}"
ROOT_URL="${ROOT_URL:-http://localhost:8000}"

echo "==> Health check"
curl -s "$ROOT_URL/health" | cat
echo

echo "==> Create tenant"
tenant_resp=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/admin/tenants" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Tenant"}')
tenant_body="${tenant_resp%$'\n'*}"
tenant_code="${tenant_resp##*$'\n'}"
if [ "$tenant_code" != "200" ]; then
  echo "Create tenant failed ($tenant_code): $tenant_body"
  exit 1
fi
TENANT_ID=$(python -c "import sys, json; print(json.loads(sys.stdin.read())['id'])" <<< "$tenant_body")
echo "TENANT_ID=$TENANT_ID"

echo "==> Create admin user"
email_suffix="$(python -c 'import uuid; print(str(uuid.uuid4())[:8])')"
admin_resp=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/admin/users" \
  -H "Content-Type: application/json" \
  -d "{\"tenant_id\":\"$TENANT_ID\",\"email\":\"admin+$email_suffix@test.com\",\"full_name\":\"Test Admin\",\"role\":\"admin\",\"department\":\"IT\"}")
admin_body="${admin_resp%$'\n'*}"
admin_code="${admin_resp##*$'\n'}"
if [ "$admin_code" != "200" ]; then
  echo "Create admin user failed ($admin_code): $admin_body"
  exit 1
fi
ADMIN_ID=$(python -c "import sys, json; print(json.loads(sys.stdin.read())['id'])" <<< "$admin_body")
echo "ADMIN_ID=$ADMIN_ID"

echo "==> Create project"
project_resp=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/admin/projects" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $ADMIN_ID" \
  -d "{\"tenant_id\":\"$TENANT_ID\",\"name\":\"Test Policies\",\"department\":\"HR\"}")
project_body="${project_resp%$'\n'*}"
project_code="${project_resp##*$'\n'}"
if [ "$project_code" != "200" ]; then
  echo "Create project failed ($project_code): $project_body"
  exit 1
fi
PROJECT_ID=$(python -c "import sys, json; print(json.loads(sys.stdin.read())['id'])" <<< "$project_body")
echo "PROJECT_ID=$PROJECT_ID"

echo "==> Upload document"
upload_resp=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/rag/projects/$PROJECT_ID/documents" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $ADMIN_ID" \
  -d '{"title":"WFH Policy","content":"Test tenant allows remote work 1 day a week."}')
upload_body="${upload_resp%$'\n'*}"
upload_code="${upload_resp##*$'\n'}"
if [ "$upload_code" != "200" ]; then
  echo "Upload document failed ($upload_code): $upload_body"
  exit 1
fi
echo "$upload_body"
echo

echo "==> Ask question"
chat_resp=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/rag/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $ADMIN_ID" \
  -d "{\"user_id\":\"$ADMIN_ID\",\"project_id\":\"$PROJECT_ID\",\"question\":\"How many remote work days are allowed?\"}")
chat_body="${chat_resp%$'\n'*}"
chat_code="${chat_resp##*$'\n'}"
if [ "$chat_code" != "200" ]; then
  echo "Chat failed ($chat_code): $chat_body"
  exit 1
fi
echo "$chat_body"
echo

echo "==> Done"
