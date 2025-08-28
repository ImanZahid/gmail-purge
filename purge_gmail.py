import argparse
import json
import os
import sys
import time
from typing import Generator, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Scope allows moving to Trash and permanent deletion.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_service():
    """
    Returns an authenticated Gmail API service.
    Stores/loads OAuth tokens in token.json next to this script.
    """
    creds = None
    token_path = os.path.join(os.getcwd(), "token.json")
    cred_path = os.path.join(os.getcwd(), "credentials.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(cred_path):
                print("Missing credentials.json in the current directory.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)

def list_message_ids(service, query: Optional[str], include_spam_trash: bool, max_count: int) -> Generator[str, None, None]:
    """
    Yields message IDs matching the query (or all if query is None).
    """
    user_id = "me"
    page_token = None
    total = 0

    while True:
        resp = service.users().messages().list(
            userId=user_id,
            q=query,
            includeSpamTrash=include_spam_trash,
            pageToken=page_token,
            maxResults=500
        ).execute()

        for m in resp.get("messages", []):
            if max_count and total >= max_count:
                return
            msg_id = m.get("id")
            if msg_id:
                total += 1
                yield msg_id

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

def chunks(seq: List[str], size: int) -> Generator[List[str], None, None]:
    for i in range(0, len(seq), size):
        yield seq[i:i + size]

def process_batch(service, ids: List[str], mode: str):
    """
    mode='trash' → batchModify add TRASH label
    mode='delete' → batchDelete
    """
    user_id = "me"
    if mode == "trash":
        service.users().messages().batchModify(
            userId=user_id,
            body={"ids": ids, "addLabelIds": ["TRASH"], "removeLabelIds": []}
        ).execute()
    elif mode == "delete":
        service.users().messages().batchDelete(
            userId=user_id,
            body={"ids": ids}
        ).execute()
    else:
        raise ValueError("mode must be 'trash' or 'delete'")

def main():
    parser = argparse.ArgumentParser(description="Purge Gmail messages by query.")
    parser.add_argument("--mode", choices=["trash", "delete"], default="trash",
                        help="trash (default, reversible ~30 days) or delete (permanent, IRREVERSIBLE)")
    parser.add_argument("--query", type=str, default=None,
                        help="Gmail search query. Example: 'label:inbox older_than:1y -category:promotions'")
    parser.add_argument("--all", action="store_true",
                        help="Target ALL messages (dangerous). Ignores --query.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Count matches only; do not change anything.")
    parser.add_argument("--batch-size", type=int, default=1000,
                        help="IDs per batch request (1..1000).")
    parser.add_argument("--max", type=int, default=0,
                        help="Limit maximum messages processed (0 = unlimited).")
    parser.add_argument("--include-spam-trash", action="store_true",
                        help="Include Spam and Trash in the search scope.")
    parser.add_argument("--sleep-ms", type=int, default=250,
                        help="Sleep between batches to be gentle on API (milliseconds).")

    args = parser.parse_args()

    if not args.all and not args.query:
        print("Provide either --all (EXTREMELY DANGEROUS) or --query '...'\n"
              "Example: --query 'label:inbox older_than:1y -category:promotions'")
        sys.exit(2)

    if not (1 <= args.batch_size <= 1000):
        print("--batch-size must be in [1, 1000]")
        sys.exit(2)

    target_desc = "(ALL MAIL)" if args.all else f"query: {args.query!r}"
    print(f"\nTarget → {target_desc}")
    print(f"Mode   → {args.mode}{' (dry-run)' if args.dry_run else ''}")
    print(f"Batch  → {args.batch_size}   Max → {args.max or '∞'}   IncludeSpamTrash → {bool(args.include_spam_trash)}\n")

    try:
        service = get_service()
        q = None if args.all else args.query

        buffered: List[str] = []
        total = 0

        for msg_id in list_message_ids(service, q, args.include_spam_trash, args.max):
            buffered.append(msg_id)
            total += 1
            if len(buffered) >= 5000:
                if args.dry_run:
                    print(f"[dry-run] would process {len(buffered)} messages")
                else:
                    for group in chunks(buffered, args.batch_size):
                        process_batch(service, group, args.mode)
                        time.sleep(args.sleep_ms / 1000.0)
                buffered.clear()
                print(f"Processed so far: {total}")

        if buffered:
            if args.dry_run:
                print(f"[dry-run] would process {len(buffered)} messages")
            else:
                for group in chunks(buffered, args.batch_size):
                    process_batch(service, group, args.mode)
                    time.sleep(args.sleep_ms / 1000.0)

        print(f"\nDone. Matched messages: {total}.")
        if args.mode == "trash":
            print("Messages are now in Trash (auto-deleted by Gmail after ~30 days).")
            print("Once confident, you can permanently delete with --mode delete on the same query (or use --query 'in:trash').")

    except HttpError as e:
        try:
            data = json.loads(e.content.decode("utf-8"))
            print("Gmail API error:", json.dumps(data, indent=2))
        except Exception:
            print("Gmail API error:", e)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)

if __name__ == "__main__":
    main()
