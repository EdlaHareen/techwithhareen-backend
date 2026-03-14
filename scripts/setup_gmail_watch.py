"""
One-time script to set up Gmail push notifications via Pub/Sub.

Run this once to start the watch, and daily via Cloud Scheduler to renew it.

Usage:
    python scripts/setup_gmail_watch.py

Requirements:
    - credentials.json in project root (from Google Cloud Console)
    - GCP_PROJECT_ID set in environment
    - Pub/Sub topic 'gmail-notifications' already created via Terraform
"""

import os
import sys
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.utils.gmail_client import setup_gmail_watch, SCOPES
import pickle
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


def get_or_create_token(credentials_path: str, token_path: str):
    """Run local OAuth flow if token doesn't exist yet."""
    import os
    from google.auth.transport.requests import Request

    creds = None
    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing existing token...")
            creds.refresh(Request())
        else:
            print("No token found — launching browser OAuth flow...")
            if not os.path.exists(credentials_path):
                print(f"ERROR: {credentials_path} not found.")
                print("Download it from: Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "wb") as f:
            pickle.dump(creds, f)
        print(f"✅ Token saved to {token_path}")

    return build("gmail", "v1", credentials=creds)


async def main():
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        print("ERROR: GCP_PROJECT_ID not set in .env")
        sys.exit(1)

    credentials_path = os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json")
    token_path = os.environ.get("GMAIL_TOKEN_PATH", "token.pickle")

    # Step 1: OAuth (opens browser if no token exists)
    service = get_or_create_token(credentials_path, token_path)

    # Step 2: Start Gmail watch
    topic_name = f"projects/{project_id}/topics/gmail-notifications"
    print(f"\nSetting up Gmail watch → {topic_name}")
    history_id = await setup_gmail_watch(service, topic_name)
    print(f"✅ Gmail watch active. historyId: {history_id}")
    print("Watch expires in 7 days — Cloud Scheduler renews it daily at 06:00 UTC.")

    # Step 3: Push token to Secret Manager + Cloud Run
    print("\nPushing token to GCP Secret Manager...")
    token_b64 = base64.b64encode(open(token_path, "rb").read()).decode()

    import subprocess
    subprocess.run([
        "gcloud", "secrets", "versions", "add", "gmail-oauth-token",
        f"--data-file={token_path}",
        f"--project={project_id}",
        "--quiet",
    ], env={**os.environ,
            "CLOUDSDK_PYTHON": "/opt/homebrew/opt/python@3.12/libexec/bin/python3",
            "PATH": f"/opt/homebrew/share/google-cloud-sdk/bin:{os.environ['PATH']}"},
       check=False)

    print("Updating Cloud Run with GMAIL_TOKEN_B64...")
    subprocess.run([
        "gcloud", "run", "services", "update", "insta-handler",
        "--region=us-central1",
        f"--project={project_id}",
        f"--update-env-vars=GMAIL_TOKEN_B64={token_b64}",
        "--quiet",
    ], env={**os.environ,
            "CLOUDSDK_PYTHON": "/opt/homebrew/opt/python@3.12/libexec/bin/python3",
            "PATH": f"/opt/homebrew/share/google-cloud-sdk/bin:{os.environ['PATH']}"},
       check=False)

    print("\n🚀 Done! Gmail → Pub/Sub → Cloud Run pipeline is fully active.")


if __name__ == "__main__":
    asyncio.run(main())
