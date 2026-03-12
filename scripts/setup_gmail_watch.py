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

from src.utils.gmail_client import setup_gmail_watch, get_gmail_service


async def main():
    project_id = os.environ.get("GCP_PROJECT_ID")
    if not project_id:
        print("ERROR: GCP_PROJECT_ID not set in environment")
        sys.exit(1)

    topic_name = f"projects/{project_id}/topics/gmail-notifications"
    print(f"Setting up Gmail watch for topic: {topic_name}")

    service = get_gmail_service()
    history_id = await setup_gmail_watch(service, topic_name)
    print(f"✅ Gmail watch active. Initial historyId: {history_id}")
    print("Watch expires in 7 days. Cloud Scheduler will renew it daily at 06:00 UTC.")


if __name__ == "__main__":
    asyncio.run(main())
