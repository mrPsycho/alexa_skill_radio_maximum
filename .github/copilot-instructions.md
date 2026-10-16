# Project Guidelines — Alexa Maximum Radio Skill

Custom Alexa skill (AudioPlayer interface) that streams a single fixed radio
station. Self-hosted Python/Flask web service (not AWS Lambda, not
Alexa-hosted). See [PLAN.md](../PLAN.md) for the full build roadmap, phase
status checklist, and rationale behind design decisions — read it before
starting new work and update its status checklist as phases complete.

## Current status: LIVE in production
- Skill ID: `amzn1.ask.skill.75f2957e-6984-4005-a3ab-7249fa26db0d` ("Maximum
  Radio", invocation name "maximum radio").
- Production endpoint: `https://radio.tildaslash.sh/alexa`, served by a
  self-managed YunoHost server. See [README.md](../README.md)'s
  "Production hosting" section for the full architecture, redeploy
  commands, and diagnostics.
- Verified working end-to-end in the Alexa Simulator (launch, pause,
  resume, stop) as of Phase C/D completion in PLAN.md.

## Architecture
- Custom skill + `AudioPlayer` interface (NOT the Music/Radio/Podcast Skill
  API — that requires an Amazon partner invite and is overkill for one
  static stream).
- Backend: Flask app (`app/main.py`), handlers in `app/handlers.py`, station
  config in `app/config.py` (read from environment variables, never
  hardcode secrets or the skill ID in code).
- Alexa request verification: `flask_ask_sdk.SkillAdapter` does signature
  and timestamp checks (do not bypass). It does NOT check the skill ID —
  that's done by `SkillIdVerifier` in `app/main.py` against the
  comma-separated `ALEXA_SKILL_ID` list. Several skills (one per extra
  invocation name, e.g. "radio maximum r. u.", "morning maximum radio")
  share this one backend; add each new skill's ID to that list.
- Interaction model lives under
  `skill-package/interactionModels/custom/<locale>.json`; skill manifest at
  `skill-package/skill.json`.

## Build and Test
- Dependencies: `pip install -r requirements.txt` (Flask, `ask-sdk-core`,
  `ask-sdk-webservice-support`, `flask-ask-sdk`, `gunicorn`).
- Local run: `python -m app.main` (reads config from `.env`; copy
  `.env.example` first, never commit `.env`).
- Local HTTPS testing requires a trusted cert — use `ngrok http <port>` to
  tunnel; Alexa rejects self-signed certs outside of manual dev-console
  configuration.
- Manual smoke test: POST a sample `LaunchRequest` JSON body to the
  `/alexa` route and confirm the response includes an `AudioPlayer.Play`
  directive with the correct stream URL.
- Production redeploy: `rsync` code to `/opt/alexa_maximum_radio/` on the
  server, reinstall deps in its venv, then `systemctl restart
  maxradio.service`. Never edit files directly on the server outside of
  `.env`/nginx config — always deploy from this repo. Exact commands are in
  README.md's "Redeploying after code changes" section.

## Production hosting gotcha (YunoHost)
The production server also runs YunoHost for unrelated services. If you
ever need to touch server-side nginx/TLS config: **do not** hand-roll a
plain `/etc/nginx/sites-enabled/<domain>` vhost + your own `certbot` cert —
it was externally curl-reachable but Alexa's backend could never reach it
(root cause not fully pinned down). The fix was registering the domain via
`yunohost domain add` and installing YunoHost's own Let's Encrypt cert,
then adding a `location /` proxy block under
`/etc/nginx/conf.d/<domain>.d/` that overrides YunoHost's SSOwat
auth-check with `access_by_lua_block { return }` (an empty `{}` block is
invalid Lua and fails `nginx -t`) so Alexa's unauthenticated POSTs reach
the app. See README.md's "Production hosting" section for the full config.

## Testing on a real device/app
Official reference: [Test and Debug Your Skill](https://developer.amazon.com/en-US/docs/alexa/test/test-your-skill-overview.html)
(check this page for the latest steps if the Alexa app UI has changed).
Key points as of the last check: the skill only appears for accounts
matching the developer account (or explicit beta testers); "Skill testing"
must be enabled in "Development" on the console's Test tab; the Alexa
app/device locale must match a supported skill locale (`en-US` here); and
the app's skill-enable path differs between the standard app (☰ → Skills
and Games → Your Skills → Dev tab → Enable To Use) and the Alexa+ app
(☰ → More → Alexa+ Store → Browse Alexa Skills and Games → same Dev tab
flow). Full step-by-step is in README.md's "6. Test" section.

## Conventions
- Station name/URL/invocation name are environment-driven
  (`STATION_NAME`, `STATION_URL`, `ALEXA_SKILL_ID`) — no per-station
  hardcoding in handler logic.
- `AudioPlayer` request handlers (`PlaybackStarted`, `PlaybackFinished`,
  `PlaybackStopped`, `PlaybackNearlyFinished`, `PlaybackFailed`) must never
  return `outputSpeech`, `card`, `reprompt`, or non-`AudioPlayer` directives
  — Alexa rejects such responses.
- `AMAZON.PauseIntent` and `AMAZON.ResumeIntent` are required by the
  AudioPlayer interface; must always be handled without error even if the
  skill only supports one stream.
- Audio stream URLs must be HTTPS on port 443 with a CA-trusted cert, and
  in a supported format (AAC/MP4, MP3, PLS, M3U/M3U8, HLS).
- Keep [PLAN.md](../PLAN.md)'s phase checklist and this file in sync with
  reality whenever architecture or conventions change.
