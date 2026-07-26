# Plan: Custom Alexa Radio-Streaming Skill (Python, self-hosted web service)

## Decisions
- Single fixed station, URL: `https://hls-01-maximum.hostingradio.ru/maximum/playlist.m3u8` (HLS — supported format per AudioPlayer URL requirements)
- Hosting: self-hosted HTTPS web service (not Lambda, not Alexa-hosted)
- Language: Python
- Audio-only (no screen/APL metadata)

## Key research findings
- Custom skill + AudioPlayer interface is the right fit (NOT the Music/Radio/Podcast Skill API — that requires an Amazon partner invite and is overkill for one static stream).
- `AudioPlayer.Play` directive needs: `playBehavior` (`REPLACE_ALL` to start), `audioItem.stream.url`, `token`, `offsetInMilliseconds`.
- Must implement `AMAZON.PauseIntent` and `AMAZON.ResumeIntent` (required); recommended: `CancelIntent`, `StopIntent`, `HelpIntent`, `FallbackIntent`.
- Must handle AudioPlayer requests: `PlaybackStarted`, `PlaybackFinished`, `PlaybackStopped`, `PlaybackNearlyFinished`, `PlaybackFailed` (skill isn't required to respond to most, but should not error).
- Self-hosted web service requirements: HTTPS port 443, Amazon-trusted CA cert (self-signed only for dev/testing), must verify `SignatureCertChainUrl` + `Signature-256` header and timestamp (<150s tolerance).
- Python SDK: `ask-sdk-core`, `ask-sdk-webservice-support`, and Flask extension `flask-ask-sdk` (`SkillAdapter` handles signature/timestamp/application-id verification automatically when given `skill_id`).

## Status
- [x] Research & design complete (custom skill + AudioPlayer approach chosen)
- [x] Plan documented in this file
- [x] Phase A — project scaffold (`app/`, `requirements.txt`, `.env.example`,
      `.gitignore`, `skill-package/skill.json`,
      `skill-package/interactionModels/custom/en-US.json`)
- [x] Phase B — skill logic (handlers implemented in `app/handlers.py`, wired
      in `app/main.py`; verified locally: `/health` responds, unsigned
      `/alexa` requests are rejected with HTTP 400, and `LaunchRequest`
      produces a correct `AudioPlayer.Play` directive with `REPLACE_ALL` and
      the configured station URL)
- [x] Phase C — skill created in Alexa developer console (Custom model,
      self-provisioned HTTPS hosting), AudioPlayer interface enabled,
      interaction model built, endpoint verified reachable, and tested
      successfully in the Alexa Simulator ("open maximum radio", "pause",
      "resume", "stop" all produce correct directives with no errors).
      Superseded the original ngrok-based local-dev plan — went straight to
      the real production endpoint below instead of a temporary tunnel.
- [x] Phase D — production hosting: deployed to a self-hosted YunoHost
      server (domain `radio.tildaslash.sh`, registered via
      `yunohost domain add` with a YunoHost-managed Let's Encrypt cert —
      *do not* hand-roll a separate certbot/sites-enabled vhost on a
      YunoHost box, it will not be reliably reachable). App runs under
      gunicorn as systemd unit `maxradio.service`
      (`/etc/systemd/system/maxradio.service`, bound to `127.0.0.1:5000`).
      Reverse proxy + SSO bypass configured in
      `/etc/nginx/conf.d/radio.tildaslash.sh.d/maxradio.conf` (overrides
      YunoHost's SSOwat lua check via `access_by_lua_block { return }` so
      Alexa's unauthenticated requests reach the app).

### Known environment issue (resolved)
`ask-sdk-webservice-support` depends on `certvalidator` → `oscrypto`, whose
PyPI release (1.3.0) fails with `LibraryNotFoundError: Error detecting the
version of libcrypto` on OpenSSL 3.x (unresolved upstream:
https://github.com/wbond/oscrypto/issues/78). Fixed by forcing
`requirements.txt` to install oscrypto from patched commit
`d5f3437ed24257895ae1edd9e503cfb352e635a8` instead of the broken PyPI
release. Not a version pin — a required bugfix with no released
alternative; remove once upstream ships a fix.

---

## Steps

### Phase A — Project scaffold (parallel-safe, no dependencies)
1. Create Python project structure in the repo root:
   - `app/main.py` — Flask app, mounts `flask_ask_sdk.SkillAdapter` at `/` (or `/alexa`), reads `ALEXA_SKILL_ID` from env for verification.
   - `app/handlers.py` — all request handlers (see Phase B).
   - `app/config.py` — `STATION_NAME`, `STATION_URL` from environment variables (with defaults matching the provided URL), `INVOCATION_NAME`.
   - `requirements.txt` — flask, ask-sdk-core, ask-sdk-webservice-support, flask-ask-sdk, gunicorn.
   - `.env.example` — `ALEXA_SKILL_ID`, `STATION_NAME`, `STATION_URL`, `PORT`.
   - `.gitignore` — `.env`, `__pycache__`, `venv`.
2. Create interaction model: `skill-package/interactionModels/custom/en-US.json` with invocation name (default `maximum radio`, user can rename), intents:
   - `PlayRadioIntent` (explicit "play the radio" utterances) — maps to launch behavior too.
   - Built-ins: `AMAZON.PauseIntent`, `AMAZON.ResumeIntent`, `AMAZON.StopIntent`, `AMAZON.CancelIntent`, `AMAZON.HelpIntent`, `AMAZON.FallbackIntent`, `AMAZON.NavigateHomeIntent`.
3. Create `skill-package/skill.json` skill manifest stub (publishingInformation with placeholder name/description/examplePhrases, `apis.custom.endpoint` of type HTTPS pointing to the future public URL, no interfaces beyond default — AudioPlayer interface is enabled via console toggle, not required in manifest for it to work but can be declared).

### Phase B — Skill logic (*depends on Phase A structure*)
4. Implement handlers in `app/handlers.py` using `ask_sdk_core.dispatch_components.AbstractRequestHandler`:
   - `LaunchRequestHandler` / `PlayRadioIntentHandler` → build response with `AudioPlayer.Play` directive (`playBehavior=REPLACE_ALL`, `audioItem.stream.url=STATION_URL`, `token="live-stream"`, `offsetInMilliseconds=0`), short speech "Starting <station name>", `should_end_session=True`.
   - `PauseIntentHandler` (`AMAZON.PauseIntent`) → `AudioPlayer.Stop` directive, end session.
   - `ResumeIntentHandler` (`AMAZON.ResumeIntent`) → same as launch (re-send Play directive since it's a live stream, no offset resume).
   - `CancelOrStopIntentHandler` (`AMAZON.CancelIntent` / `AMAZON.StopIntent`) → `AudioPlayer.Stop` directive + short goodbye speech.
   - `HelpIntentHandler` → speech explaining "say play, pause, resume, or stop".
   - `FallbackIntentHandler`, `SessionEndedRequestHandler`, generic `CatchAllExceptionHandler`.
   - AudioPlayer request handlers (no standard speech allowed in responses to these): `PlaybackStartedHandler`, `PlaybackFinishedHandler`, `PlaybackStoppedHandler`, `PlaybackNearlyFinishedHandler` (no-op, live stream has no "next"), `PlaybackFailedHandler` (log error, optionally re-issue `AudioPlayer.Play` with a new token to auto-reconnect the stream).
5. Wire `SkillBuilder` in `app/main.py`: register all handlers, build skill, wrap with `flask_ask_sdk.SkillAdapter(skill=skill, skill_id=ALEXA_SKILL_ID, app=flask_app)`, expose `/alexa` POST route via `skill_adapter.dispatch_request`.

### Phase C — Local verification (*depends on Phase B*)
6. Run Flask app locally (`python app/main.py` or `flask run`), expose via `ngrok http <port>` to get a temporary trusted HTTPS URL (needed because Alexa requires a CA-trusted cert; self-signed certs need extra console config and are dev-only).
7. In the Alexa developer console: create the skill (Custom model), paste the interaction model JSON (or use ASK CLI), enable the **AudioPlayer** interface under Interfaces, set the endpoint to the ngrok HTTPS URL + `/alexa`, choose "My development endpoint has a certificate from a trusted certificate authority", Build Model.
8. Test in the Alexa Simulator (directives visible in Skill I/O, audio itself won't render) and then on a real Echo device: "Alexa, open maximum radio" → expect stream to start; "Alexa, pause" / "Alexa, resume" / "Alexa, stop".

### Phase D — Production hosting (*depends on Phase C passing tests*)
9. Provision a small VPS (or existing server) with a real domain name pointed at it.
10. Install Nginx as reverse proxy + Certbot (Let's Encrypt) for a trusted TLS cert; run the Flask app under `gunicorn` as a systemd service; Nginx proxies HTTPS 443 → gunicorn's local port.
11. Update the skill's endpoint in the developer console to the permanent HTTPS domain URL; re-select "trusted certificate authority" option; Build Model again.
12. (Optional) Submit for certification only if the user wants public distribution — for private/personal use, the skill works fine "Enabled" only for the developer's own account without certification.

## Relevant files (to be created)
- `app/main.py` — Flask entrypoint + SkillAdapter wiring
- `app/handlers.py` — all intent/AudioPlayer/exception handlers
- `app/config.py` — env-driven station config
- `requirements.txt`, `.env.example`, `.gitignore`
- `skill-package/skill.json` — skill manifest
- `skill-package/interactionModels/custom/en-US.json` — interaction model

## Verification
1. Unit-level: run Flask app locally, `curl -X POST` with a sample `LaunchRequest` JSON body (from ASK docs) to confirm a valid response with the `AudioPlayer.Play` directive and correct stream URL.
2. Integration: Alexa Simulator in developer console — confirm `AudioPlayer.Play` directive appears in Skill I/O with the exact station URL.
3. Device test: real Echo device — confirm audio actually plays, pause/resume/stop work via voice, and via `PlaybackFailed` reconnect logic if the stream is interrupted.
4. Security checks: confirm requests without a valid `Signature-256`/`SignatureCertChainUrl` or with stale timestamps are rejected (flask-ask-sdk's SkillAdapter handles this — verify by sending a forged request and confirming HTTP 400).

## Scope boundaries
- Included: single hardcoded station, play/pause/resume/stop voice control, audio-only (no screen metadata), self-hosted Python/Flask backend, dev (ngrok) + production (VPS+Nginx+Certbot) hosting paths.
- Excluded: multi-station selection by voice, screen/APL visuals, in-skill purchasing, account linking, public certification/store submission (only mentioned as an optional future step), Music/Radio/Podcast Skill API (not needed for a single static stream).

## Further considerations (resolved or deferred)
1. Invocation name — defaulted to "maximum radio" as a placeholder; user should confirm/change before building the interaction model (must be 2+ words, lowercase, no special Alexa-reserved words).
2. `PlaybackFailed` reconnect strategy — plan re-issues a fresh `Play` directive with a new token on failure to handle transient live-stream drops; can be simplified to a no-op if undesired.
