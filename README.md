# Gmail Purge Script

Bulk-manage Gmail using the Gmail API. Safely move messages to Trash (reversible for ~30 days) or permanently delete them. Supports Gmail search queries (`older_than:1y`, `in:trash`, `category:promotions`, etc.), batching, and a dry-run mode.

⚠️ **Irreversible actions**: `--mode delete` permanently erases messages. Always start with `--dry-run` and preferably use `--mode trash` first.

## Features

🔎 **Query support**: target exactly what you want using Gmail search operators.

🧪 **Dry run**: count matches without changing anything.

🗑️ **Trash mode (default)**: reversible for ~30 days.

💣 **Permanent delete**: when you're 100% sure.

📦 **Batching**: fast and API-friendly (up to 1000 IDs per batch).

🧰 **CLI options**: `--all`, `--max`, `--batch-size`, `--include-spam-trash`, `--sleep-ms`.

## What's in this repo

```
purge_gmail.py       # the script
requirements.txt     # pip deps (or install from README)
.gitignore           # ignores secrets and local artifacts
README.md
```

**Do NOT commit `credentials.json` or `token.json`.**

## Quick Start

### 0) Requirements

- Python 3.9+
- A Google Cloud project with the Gmail API enabled
- OAuth 2.0 Desktop client credentials (`credentials.json`)

### 1) Enable Gmail API & create OAuth credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → select/create a project.
2. **APIs & Services** → **Library** → search **Gmail API** → **Enable**.
3. **APIs & Services** → **OAuth consent screen**
   - **User type**: External
   - Keep **Publishing status** = Testing
   - Add your Gmail under **Test users** (up to 100 allowed).
4. **APIs & Services** → **Credentials** → **Create credentials** → **OAuth client ID**
   - **Application type**: Desktop app
   - Download the JSON → save as `credentials.json` (do not commit).

### 2) Local setup

```bash
# from your project folder
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
# or:
# pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Place your downloaded `credentials.json` in the same folder as `purge_gmail.py`.

## Usage

**First run a dry run to confirm the match count.**

### Dry run (count only)

```bash
python purge_gmail.py --dry-run --query "label:inbox older_than:1y"
# or everything:
python purge_gmail.py --dry-run --all
```

- The first time, a browser opens → sign in with the test user you added → allow access.
- A `token.json` will be created locally.

### Move messages to Trash (safe)

```bash
# by query
python purge_gmail.py --mode trash --query "category:promotions older_than:2y"

# all mail (reversible ~30 days)
python purge_gmail.py --mode trash --all
```

### Permanently delete (IRREVERSIBLE)

```bash
# by query
python purge_gmail.py --mode delete --query "category:promotions older_than:2y"

# empty the Trash
python purge_gmail.py --mode delete --query "in:trash"

# delete EVERYTHING (use with extreme caution)
python purge_gmail.py --mode delete --all
```

## Useful queries

- **Old inbox mail**: `label:inbox older_than:1y`
- **Promotions**: `category:promotions`
- **Big mails**: `larger:5M`
- **From a domain**: `from:@example.com`
- **Combine/exclude**: `label:inbox older_than:2y -category:promotions`
- **Trash only**: `in:trash`

## Command-line options

```
--mode trash|delete       # default: trash
--query "..."             # Gmail search query
--all                     # ignore --query and target ALL messages
--dry-run                 # only count; no changes
--batch-size 1000         # 1..1000 (API limit per batch)
--max 0                   # limit total processed (0 = unlimited)
--include-spam-trash      # include Spam/Trash in search scope
--sleep-ms 250            # delay between batches (ms)
```

**Examples:**

```bash
# cap processing to first 2000 messages, gentle pacing
python purge_gmail.py --mode trash --all --max 2000 --batch-size 500 --sleep-ms 750
```

## Safety checklist

1. Start with `--dry-run` and a narrow query; widen gradually.
2. Prefer `--mode trash` first; verify in Gmail → Trash.
3. Only then consider `--mode delete` (irreversible).
4. Keep scope minimal: this script uses only `gmail.modify`.
5. Never publish `credentials.json` or `token.json`.
6. If you accidentally exposed them, revoke the OAuth client in Google Cloud and create a new one.

## Troubleshooting

### 403 access_denied / "app not verified"

- OAuth consent screen **User type** = External, status **Testing**.
- Add your Gmail under **Test users**.
- Delete local `token.json` and retry.
- Use the same Gmail you added; if multiple accounts, try incognito.

### Wrong project / client

- Ensure the `client_id` in your local `credentials.json` matches the OAuth client you created for this project.
- If you replaced credentials, delete `token.json` and run again.

### Insufficient permissions

- Scope must be `https://www.googleapis.com/auth/gmail.modify`.
- Delete `token.json` to re-consent if you changed scopes.

### Rate limits / 429 / 5xx

- Increase `--sleep-ms` and/or reduce `--batch-size`.

## Development tips

- Add a confirmation prompt for destructive commands unless `--force`.
- Add logging (`--log file.log`) for audit trails.
- Implement exponential backoff for retries.

## License

MIT — do what you want, but you are responsible for how you use it.

## Credits

Built with the official Google Python client libraries:

- [google-api-python-client](https://github.com/googleapis/google-api-python-client)
- [google-auth-httplib2](https://github.com/googleapis/google-auth-library-python-httplib2)
- [google-auth-oauthlib](https://github.com/googleapis/google-auth-library-python-oauthlib)
