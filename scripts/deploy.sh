#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# deploy.sh — Full deployment script for @techwithhareen Insta Handler
#
# Steps:
#   1. Validate .env and gcloud auth
#   2. Push secrets to GCP Secret Manager
#   3. Build & push Docker image via Cloud Build
#   4. terraform apply — updates Cloud Run with latest image + env vars
#   5. Run Gmail watch setup
#   6. Smoke-test /healthz
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (gcloud auth login)
#   - terraform installed (brew install terraform)
#   - .env file populated (cp .env.example .env && fill in values)
#   - token.pickle present (run scripts/setup_gmail_watch.py first if not)
#
# Usage:
#   chmod +x scripts/deploy.sh && ./scripts/deploy.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# Fix for macOS: gcloud needs Python 3.12 when 3.13 is not installed
export CLOUDSDK_PYTHON=/opt/homebrew/opt/python@3.12/libexec/bin/python3
export PATH="/opt/homebrew/share/google-cloud-sdk/bin:$PATH"

PROJECT_ID="techwithhareen"
REGION="us-central1"
APP_NAME="insta-handler"
SERVICE_URL="https://insta-handler-h76gkuoriq-uc.a.run.app"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$ROOT_DIR/infra/terraform"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[deploy]${NC} $*"; }
success() { echo -e "${GREEN}[deploy]${NC} ✅ $*"; }
warn()    { echo -e "${YELLOW}[deploy]${NC} ⚠️  $*"; }
die()     { echo -e "${RED}[deploy]${NC} ❌ $*" >&2; exit 1; }

# ── Step 0: Load & validate .env ──────────────────────────────────────────────
info "Loading .env..."
ENV_FILE="$ROOT_DIR/.env"
[[ -f "$ENV_FILE" ]] || die ".env not found — run: cp .env.example .env && fill in values"
set -a; source "$ENV_FILE"; set +a

for var in ANTHROPIC_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_OWNER_CHAT_ID SERPER_API_KEY; do
    [[ -n "${!var:-}" ]] || die "$var is not set in .env"
done
success ".env loaded"

# ── Step 1: gcloud auth check ─────────────────────────────────────────────────
info "Checking gcloud auth..."
command -v gcloud &>/dev/null || die "gcloud not installed — see: https://cloud.google.com/sdk/docs/install"
gcloud config set project "$PROJECT_ID" --quiet
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | head -1)
[[ -n "$ACTIVE_ACCOUNT" ]] || die "Not authenticated — run: gcloud auth login"
success "Authenticated as $ACTIVE_ACCOUNT"

# ── Step 2: Push secrets to Secret Manager ────────────────────────────────────
info "Pushing secrets to Secret Manager..."

push_secret() {
    local secret_id="$1" value="$2"
    echo -n "$value" | gcloud secrets versions add "$secret_id" \
        --data-file=- --project="$PROJECT_ID" --quiet 2>/dev/null \
        && echo "  ✓ $secret_id" \
        || warn "  Skipped $secret_id (may already be current)"
}

push_secret "anthropic-api-key"      "$ANTHROPIC_API_KEY"
push_secret "telegram-bot-token"     "$TELEGRAM_BOT_TOKEN"
push_secret "telegram-owner-chat-id" "$TELEGRAM_OWNER_CHAT_ID"
push_secret "serper-api-key"         "$SERPER_API_KEY"

# credentials.json
CREDS_PATH="${GMAIL_CREDENTIALS_PATH:-$ROOT_DIR/credentials.json}"
if [[ -f "$CREDS_PATH" ]]; then
    gcloud secrets versions add "gmail-oauth-credentials" \
        --data-file="$CREDS_PATH" --project="$PROJECT_ID" --quiet 2>/dev/null \
        && echo "  ✓ gmail-oauth-credentials" \
        || warn "  Skipped gmail-oauth-credentials"
else
    warn "credentials.json not found — skipping gmail-oauth-credentials"
fi

# token.pickle — base64-encoded so it survives as a text env var in Cloud Run
TOKEN_PATH="${GMAIL_TOKEN_PATH:-$ROOT_DIR/token.pickle}"
if [[ -f "$TOKEN_PATH" ]]; then
    base64 < "$TOKEN_PATH" | gcloud secrets versions add "gmail-oauth-token" \
        --data-file=- --project="$PROJECT_ID" --quiet 2>/dev/null \
        && echo "  ✓ gmail-oauth-token" \
        || warn "  Skipped gmail-oauth-token"
else
    warn "token.pickle not found — Gmail trigger won't work."
    warn "After deploying, run: python scripts/setup_gmail_watch.py"
    warn "Then re-run this script to push the token."
fi

success "Secrets pushed"

# ── Step 3: Build & push Docker image via Cloud Build ─────────────────────────
info "Submitting Cloud Build (~3-4 min)..."
cd "$ROOT_DIR"
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "manual")
gcloud builds submit \
    --config=infra/cloudbuild.yaml \
    --project="$PROJECT_ID" \
    --substitutions="_REGION=${REGION},_APP_NAME=${APP_NAME},COMMIT_SHA=${COMMIT_SHA}" \
    --quiet
success "Image built and pushed (sha: $COMMIT_SHA)"

# ── Step 4: terraform apply ───────────────────────────────────────────────────
info "Running terraform apply..."
command -v terraform &>/dev/null || die "terraform not installed — brew install terraform"

cd "$TERRAFORM_DIR"
terraform init -input=false -reconfigure -upgrade -backend=false 2>/dev/null || terraform init -input=false

terraform apply \
    -var="project_id=${PROJECT_ID}" \
    -var="region=${REGION}" \
    -var="app_name=${APP_NAME}" \
    -auto-approve \
    -input=false

success "Cloud Run updated via terraform"
cd "$ROOT_DIR"

# ── Step 5: Gmail watch ───────────────────────────────────────────────────────
if [[ -f "$TOKEN_PATH" ]]; then
    info "Setting up Gmail watch..."
    python scripts/setup_gmail_watch.py && success "Gmail watch active" \
        || warn "Gmail watch setup failed — run manually: python scripts/setup_gmail_watch.py"
else
    warn "Skipping Gmail watch (no token.pickle)"
fi

# ── Step 6: Smoke test ────────────────────────────────────────────────────────
info "Waiting for Cloud Run to be ready..."
sleep 8
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/healthz")
if [[ "$HTTP_STATUS" == "200" ]]; then
    success "/healthz → 200 — service is live!"
else
    warn "/healthz → $HTTP_STATUS — still warming up, check: gcloud run services describe $APP_NAME --region=$REGION"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🚀 Deployment complete!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════${NC}"
echo ""
echo "  Service:      $SERVICE_URL"
echo "  Health:       ${SERVICE_URL}/healthz"
echo ""
echo "  Test a story end-to-end (sends to your Telegram):"
echo "  curl -X POST ${SERVICE_URL}/test/story \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"headline\": \"OpenAI launches GPT-5\", \"summary\": \"OpenAI announced...\"}'"
echo ""
