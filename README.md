# Horror Studio V4.1 — US & Europe English Horror | Cloud-first Telegram → Drive → GitHub Actions → YouTube

A configurable starter system for **English-only horror Shorts and long videos targeting the United States and Europe**. It is **not deployed** until you create the GitHub repo, configure Google/Telegram/Cloudflare credentials, and deploy the Worker.

## What it automates

1. A scheduled GitHub workflow collects horror-topic candidates from Google Trends RSS.
2. It sends a Telegram message with **Approve / Skip** buttons. Nothing is produced before approval.
3. Approval reaches the Cloudflare Worker, which dispatches a GitHub Actions production workflow.
4. You upload Flow MP4 clips to your existing Google Drive folder: `INBOX/<JOB_ID>/scene_01.mp4`, `scene_02.mp4`, etc.
5. The cloud workflow downloads the clips, assembles them with FFmpeg, creates **English narration** using Edge TTS, burns English subtitles when supplied, uploads the finished MP4 to Drive, optionally publishes it to YouTube, then sends every published Short to your Telegram chat. Shorts under 49 MB are attached as MP4; larger files are delivered as YouTube + Google Drive links.

**Flow generation remains manual**: this project does not automate Google account switching, browser scraping, or bypass Flow limits. Use Flow normally in each account and upload the resulting MP4s.

## Architecture

`Google Trends RSS → GitHub Actions (topic scout) → Telegram approval → Cloudflare Worker → GitHub workflow_dispatch → Google Drive clips → FFmpeg + Edge TTS → Drive output → YouTube Data API`

Cloudflare handles only short webhook requests. Video rendering happens on ephemeral GitHub-hosted runners; no always-on PC/server is needed. Standard GitHub-hosted runners are CPU-only; rendering speed depends on clip length and runner capacity.

## 1. Create the public GitHub repository

1. Create a new **public** repository, e.g. `horror-studio-v4`.
2. Upload the contents of this ZIP (not the parent folder) to the repository root.
3. In **Settings → Secrets and variables → Actions → New repository secret**, add the secrets listed below.
4. In **Settings → Actions → General**, allow GitHub Actions and workflow permissions to read/write repository contents only if needed. The workflows here need `contents: read` only.
5. Enable the scheduled workflow under **Actions** if GitHub asks.

### GitHub Actions secrets

| Secret | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your personal Telegram chat ID (send `/start` to your bot and obtain it from a trusted getUpdates method, or use a bot chat-ID helper) |
| `GOOGLE_CLIENT_ID` | OAuth client ID from Google Cloud |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `GOOGLE_REFRESH_TOKEN` | Offline refresh token for the Google account that owns the Drive folder and YouTube channel |
| `DRIVE_INBOX_FOLDER_ID` | Google Drive folder ID for `INBOX` |
| `DRIVE_OUTPUT_FOLDER_ID` | Google Drive folder ID for `OUTPUT` |
| `YOUTUBE_PRIVACY_STATUS` | Start with `private`; later change to `unlisted` or `public` |
| `CLOUDFLARE_WORKER_URL` | Deployed Worker URL, e.g. `https://horror-hook.<subdomain>.workers.dev` |
| `TOPIC_INGEST_SECRET` | Long random shared secret used by topic-scout workflow to write candidates to Worker KV |

Do not commit `.env`, OAuth JSON, refresh tokens, bot tokens, videos, or credentials. Public repository code is visible to everyone; GitHub Secrets are not.

## 2. Google Drive + YouTube OAuth setup (same Google account recommended)

1. In Google Cloud Console, create/select a project.
2. Enable **Google Drive API** and **YouTube Data API v3**.
3. Configure OAuth consent screen. For a personal test, add your Google account as a test user if the app is in Testing.
4. Create an OAuth Client ID of type **Desktop app**.
5. Use Google's OAuth Playground or a local OAuth flow to request these scopes:
   - `https://www.googleapis.com/auth/drive`
   - `https://www.googleapis.com/auth/youtube.upload`
6. Request offline access and exchange the authorization code for a refresh token. Store the refresh token only in GitHub Secrets.
7. Create Drive folders `INBOX` and `OUTPUT`. Copy each folder ID from its URL into the matching secret. The approved-topic workflow creates the per-job subfolder and starter `manifest.json` automatically.
8. Confirm the Google account authorized for OAuth has access to both folders and is the YouTube channel owner/manager.

OAuth Playground can issue refresh tokens only when configured with your own OAuth client. Google may show an unverified-app warning during testing. Do not publish credentials or share the refresh token.

## 3. Cloudflare Worker setup

1. Create a Cloudflare account and a Worker named `horror-hook`.
2. Create a Workers KV namespace named `HORROR_TOPICS`.
3. In `cloudflare/wrangler.toml`, replace `REPLACE_WITH_KV_NAMESPACE_ID` with its namespace ID.
4. Set Worker secrets (Cloudflare dashboard → Worker → Settings → Variables and Secrets):
   - `TELEGRAM_BOT_TOKEN` = same Telegram bot token
   - `TELEGRAM_WEBHOOK_SECRET` = a long random string (32+ characters)
   - `GITHUB_TOKEN` = fine-grained GitHub PAT with Actions: read/write on this repo
   - `GITHUB_OWNER` = GitHub username/org
   - `GITHUB_REPO` = repository name
   - `GITHUB_REF` = `main` (or your default branch)
   - `ALLOWED_TELEGRAM_CHAT_ID` = your personal Telegram chat ID (restricts bot control to you)
   - `TOPIC_INGEST_SECRET` = same long random value as GitHub secret `TOPIC_INGEST_SECRET`
5. Deploy the Worker using Wrangler (`npx wrangler deploy`) or the Cloudflare dashboard.
6. Set Telegram webhook to `https://<worker-host>/telegram/<TELEGRAM_WEBHOOK_SECRET>`. Use the Telegram Bot API `setWebhook` method. Keep the secret path private.
7. Add the deployed Worker URL to GitHub secret `CLOUDFLARE_WORKER_URL`.

The Worker validates Telegram's secret URL path, handles callback approvals, stores candidate topics in KV, and dispatches GitHub Actions. Do not expose the webhook secret publicly.

## 4. Configure GitHub workflows

Edit `.github/workflows/topic-scout.yml` and set your preferred schedule. Default is daily at 03:30 UTC (09:00 IST). Scheduled workflows may be delayed by GitHub and can be disabled after long inactivity; you can also run the workflow manually.

Edit `.github/workflows/production.yml` only if you want different defaults. The first publish setting should remain `private`.

## 5. Telegram commands

- `/start` — instructions
- `/help` — command help
- `/trending` — manually run topic scouting
- `/status` — opens the GitHub Actions run list

The topic scout checks Google Trends RSS for the United States, United Kingdom and Ireland. It never uses India as a trend region. Suggestions are creative inspiration only and require your approval. Approved packs target English-speaking viewers in the United States and Europe; story settings, dialogue, narration, subtitles, titles and metadata are English. The workflow does not auto-generate Flow video. Upload your Flow clips to Drive using the job ID in the message.

## 6. Create a Drive job folder and manifest

The approval workflow creates `INBOX/<JOB_ID>/manifest.json` for you. Edit it in Drive. Example:

```json
{
  "title": "The Last Train at 2:17 AM",
  "format": "short",
  "target_minutes": 1,
  "language": "English",
  "target_audience": "United States and Europe",
  "english_narration": "At 2:17 a.m., the last train stopped at a station that was not on the map...",
  "english_subtitles": "At 2:17 a.m....",
  "youtube_description": "An original English-language cinematic horror story for viewers in the United States and Europe. Fictional story.",
  "youtube_tags": ["horror story", "scary stories", "paranormal", "supernatural horror"],
  "publish": false,
  "telegram_delivery": true
}
```

Upload files as `scene_01.mp4`, `scene_02.mp4`, etc. Use 9:16 Flow clips for Shorts and 16:9 for long videos. Use English dialogue and visuals set in the United States or Europe; do not use Indian/South Asian locations or Hindi. The default narration voice is en-US-GuyNeural. The renderer concatenates clips and loops the visual sequence to cover the narration duration; long-form videos therefore need enough unique scenes to avoid obvious repetition. The manifest's `publish` value must be `true` to upload. Workflow privacy defaults to `private`. After a successful YouTube upload, published Shorts are sent to your Telegram chat: MP4 attachment if under 49 MB, otherwise a YouTube/Drive link. Set `telegram_delivery` to `false` to disable this for a job.

## 7. Start a render

GitHub → Actions → **Horror production** → Run workflow. Enter the Drive job folder ID (not the folder name) or use the `job_id` field if your folder is named by job ID. The workflow locates the matching folder inside `INBOX`.

When complete, the output MP4 is uploaded to `OUTPUT`. If `publish: true`, it is also uploaded to YouTube using the OAuth account. YouTube upload processing can take time; check YouTube Studio.

## 8. Shorts delivery to Facebook and Instagram

This V4 configuration uses **Telegram delivery after YouTube upload** as the reliable default. It avoids requiring Meta business permissions and a publicly reachable video-hosting URL. Open the Telegram message on your phone, save the MP4, and upload it to your Facebook Page and Instagram account. If a Short is 49 MB or larger, the bot sends the YouTube and Google Drive links instead; open the Drive link to download the original.

Automatic Facebook Page + Instagram Reels publishing is not enabled in this package. It requires a Facebook Page, an Instagram Professional account linked to that Page, Meta app permissions/access tokens, and a publicly reachable video URL for Meta's Reels publishing API. This can be added as an optional integration later; Telegram delivery works without those Meta prerequisites.

## 8. Cost and limits

- No paid video-generation API is called.
- Cloudflare Worker handles only webhook events; it does not render video.
- Public repositories generally receive free standard GitHub-hosted runner usage, subject to GitHub's current terms, fair-use rules, and platform limits. Large video jobs can still hit runner time/storage limits.
- Google Drive and YouTube API usage is subject to Google's quotas and policies.
- Edge TTS is used through the `edge-tts` Python package; it is a community client for Microsoft's online speech service, not a guaranteed SLA. If unavailable, the job fails with a clear error.
- This starter does not include a paid LLM. It produces an English-language story prompt pack from an approved topic using templates. You can edit the English narration and English subtitle text in the Drive manifest.

## 9. Safety and troubleshooting

- Never put secrets in code, Issues, commit history, or Telegram messages.
- Keep the repo public only if you are comfortable exposing source code. Do not store personal data or media in it.
- If Telegram buttons do nothing, check Worker logs, webhook URL, KV binding, and GitHub PAT permissions.
- If Drive download fails, check OAuth scopes, refresh token, folder IDs, and file sharing.
- If YouTube upload fails, verify `youtube.upload` scope and channel permissions. Keep privacy at `private` for first tests.
- GitHub runners are temporary. All source clips must be in Drive; do not rely on runner files persisting between jobs.
- You must comply with Google Flow, YouTube, Telegram, GitHub, and Cloudflare terms. Do not automate account rotation or circumvent quotas.

## Repository layout

- `cloudflare/worker.js` — Telegram webhook, approval callback, GitHub dispatch
- `.github/workflows/topic-scout.yml` — scheduled topic discovery + Telegram approval
- `.github/workflows/production.yml` — cloud story pack/render/upload workflow
- `src/drive.py` — Drive API helpers
- `src/story_pack.py` — prompt pack generator
- `src/render.py` — FFmpeg + Edge TTS assembly
- `src/youtube.py` — YouTube upload
- `src/notify_telegram.py` — sends published Shorts to Telegram (MP4 under 49 MB, links otherwise)
- `scripts/topic_scout.py` — Google Trends RSS candidate collector
- `examples/manifest.json` — manifest template
