# Alexa Maximum Radio Skill

A custom Alexa skill (using the `AudioPlayer` interface) that streams a
single, fixed radio station. Self-hosted Python/Flask web service — no AWS
Lambda, no Alexa-hosted skill, no Music/Radio/Podcast Skill API.

See [PLAN.md](PLAN.md) for the full design rationale and phase-by-phase
build roadmap.

## Current status

The skill is **built and deployed to production**. Live details:

| Item | Value |
|------|-------|
| Skill name | Maximum Radio |
| Skill ID | `amzn1.ask.skill.75f2957e-6984-4005-a3ab-7249fa26db0d` |
| Invocation name | "maximum radio" |
| Production endpoint | `https://radio.tildaslash.sh/alexa` |
| Hosting | Self-managed YunoHost server (see [Production hosting](#production-hosting) below) |

The sections below are written as general onboarding/setup instructions (useful if
re-deploying elsewhere or onboarding a new contributor), but the actual working
instance already exists at the endpoint above — you generally don't need to redo
steps 4–5 unless setting up a *new* skill or a *new* server.

## Requirements
- Python 3.10+
- An [Amazon developer account](https://developer.amazon.com/alexa/console/ask)
- [ngrok](https://ngrok.com/) (or another HTTPS tunnel) for local testing
- A public HTTPS endpoint with a CA-trusted certificate for production

## 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **Note:** `requirements.txt` intentionally does not pin versions (latest
> compatible releases are installed), except for one forced `oscrypto` git
> commit that patches a real bug affecting OpenSSL 3.x systems — see the
> comment in [requirements.txt](requirements.txt) and PLAN.md's "Known
> environment issue" section for details.

## 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable         | Description                                                                 |
|-------------------|------------------------------------------------------------------------------|
| `ALEXA_SKILL_ID`  | Your skill's Amazon-assigned ID (from the developer console), used to verify incoming requests. |
| `STATION_NAME`    | Display/spoken name of the station, e.g. `Maximum Radio`.                    |
| `STATION_URL`     | HTTPS stream URL (AAC/MP4, MP3, PLS, M3U/M3U8, or HLS), port 443, trusted cert. |
| `PORT`            | Local port for the Flask/gunicorn server (default `5000`).                   |

`.env` is git-ignored and must never be committed.

## 3. Run locally

```bash
python -m app.main
```

Confirm it's up:

```bash
curl http://localhost:5000/health
# {"status":"ok"}
```

## 4. Expose via HTTPS (local dev)

Alexa requires a CA-trusted HTTPS endpoint, so tunnel your local server:

```bash
ngrok http 5000
```

Copy the `https://<random>.ngrok-free.app` URL ngrok gives you.

## 5. Create the skill in the Alexa developer console

1. Go to the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask) → **Create Skill**.
2. Choose model **Custom**, hosting method **Provision your own**.
3. Under **Interfaces**, enable **Audio Player**.
4. Under **Interaction Model** → **JSON Editor**, paste the contents of
   [skill-package/interactionModels/custom/en-US.json](skill-package/interactionModels/custom/en-US.json).
   Confirm/change the invocation name (currently `maximum radio`) before
   building.
5. Under **Endpoint**, choose **HTTPS**, set the default endpoint to your
   ngrok URL + `/alexa` (e.g. `https://<random>.ngrok-free.app/alexa`), and
   select **"My development endpoint has a certificate from a trusted
   certificate authority"**.
6. Save and **Build Model**.
7. Copy the **Skill ID** shown in the console into your `.env` as
   `ALEXA_SKILL_ID`, then restart the app so it picks up the new value.

## 6. Test

Official reference: [Test and Debug Your Skill](https://developer.amazon.com/en-US/docs/alexa/test/test-your-skill-overview.html).

### Simulator
Developer console → **Test** tab (make sure "Skill testing is enabled in:
**Development**"). Try "open maximum radio", "pause", "resume", "stop" —
directives appear in Skill I/O (audio itself won't play in the simulator).

### Alexa app (phone/tablet/desktop)
1. Make sure "Skill testing is enabled in: **Development**" is set on the
   **Test** tab of the developer console (required before the skill will
   show up in the app at all).
2. Sign in to the [Alexa app](https://www.amazon.com/b?ie=UTF8&node=18354642011)
   with the **same credentials as your developer account**.
3. Set the app's locale to match a locale your skill supports: **More** →
   **Settings** → **Alexa on This Phone** → **Language** → e.g. "English
   (United States)" for `en-US`.
4. Enable the skill:
   - **Standard Alexa app**: tap the ☰ menu → **Skills and Games** →
     **Your Skills** → scroll the skill-type tabs to **Dev** → find
     "Maximum Radio" → tap it → **ENABLE TO USE**.
   - **Alexa+ app**: tap the ☰ menu → **More** → **Alexa+ Store** → scroll
     down → **Browse Alexa Skills and Games**, then the same **Your
     Skills** → **Dev** flow as above.
5. Say **"Alexa, open maximum radio"**, then test "Alexa, pause" / "Alexa,
   resume" / "Alexa, stop" from the app's mic or a linked device.

To let other people test without sharing your developer credentials, use a
[beta test](https://developer.amazon.com/en-US/docs/alexa/custom-skills/skills-beta-testing-for-alexa-skills.html)
instead of trying to add them as a household/Family member.

### Real Alexa-enabled device (Echo, etc.)
1. Register the device with the **same email address** used for your
   Amazon developer account. Make sure the device's locale matches a
   locale your skill supports.
2. If the device is already registered to a different account, you must
   [reset the device](https://www.amazon.com/gp/help/customer/display.html?nodeId=GK7P5SPCQ3MN65VR)
   and re-register it with your developer account (or use
   [Amazon Household](https://www.amazon.com/myh/amazonFamily)/a beta test
   instead of resetting, if you don't want to lose the device's existing
   account association).
3. Say **"Alexa, open maximum radio"** (wake word + invocation name), then
   "Alexa, pause" / "Alexa, resume" / "Alexa, stop".
4. Testing behind a corporate firewall requires opening specific ports for
   Echo device connectivity — see the "Test your skills behind a firewall"
   section of the official doc linked above if relevant.

If something fails only on-device but works in the simulator, check
`journalctl -u maxradio.service` and nginx's
`radio.tildaslash.sh-access.log`/`-error.log` on the production server for
the actual request/response (see [Production hosting](#production-hosting)
for server access details).

## Project structure

```
app/
  main.py      # Flask entrypoint, mounts flask-ask-sdk SkillAdapter at /alexa
  handlers.py  # Alexa request/exception handlers (Launch, Pause, Resume, AudioPlayer events, ...)
  config.py    # Environment-driven config (station name/URL, skill ID, port)
skill-package/
  skill.json                                # Skill manifest
  interactionModels/custom/en-US.json       # Invocation name + intents
```

## Production hosting

The live instance runs on a self-managed **YunoHost** server (Debian 12),
domain `radio.tildaslash.sh` pointed at the server's public IP. Architecture:

```
Alexa backend  --HTTPS-->  nginx (YunoHost-managed vhost, port 443)
                              |  proxy_pass
                              v
                        gunicorn (127.0.0.1:5000, systemd unit maxradio.service)
                              |
                        app.main:app (Flask + flask_ask_sdk.SkillAdapter)
```

Key server-side pieces:

| Piece | Location |
|-------|----------|
| App code | `/opt/alexa_maximum_radio/` (deployed via `rsync`, excludes `.venv`/`.git`/`.env`) |
| Python venv | `/opt/alexa_maximum_radio/.venv/` |
| Production `.env` | `/opt/alexa_maximum_radio/.env` (mode `600`, owned by `maxradio:maxradio`) |
| systemd service | `/etc/systemd/system/maxradio.service` \u2014 runs `gunicorn -w 2 -b 127.0.0.1:5000 app.main:app` as the unprivileged `maxradio` system user |
| nginx vhost | `/etc/nginx/conf.d/radio.tildaslash.sh.conf` (generated by YunoHost) |
| nginx app proxy config | `/etc/nginx/conf.d/radio.tildaslash.sh.d/maxradio.conf` (hand-written, see below) |
| TLS cert | `/etc/yunohost/certs/radio.tildaslash.sh/` (managed by YunoHost, **not** certbot directly) |

### ⚠️ YunoHost-specific gotcha
This server already runs YunoHost for other services. **Do not** hand-roll a
separate `/etc/nginx/sites-enabled/<domain>` vhost + your own `certbot`
certificate for a new domain on a YunoHost box — in practice this domain was
externally reachable via plain `curl` but Alexa's backend could never reach
it (confirmed via packet capture showing zero inbound packets during a
simulator test), and the exact reason was never fully root-caused. What
fixed it was registering the domain the "YunoHost way":

```bash
yunohost domain add radio.tildaslash.sh   # or via the YunoHost admin web UI
# then install a Let's Encrypt cert for it through YunoHost (admin UI or
# `yunohost domain cert-install radio.tildaslash.sh`)
```

This generates `/etc/nginx/conf.d/<domain>.conf` (with YunoHost's SSOwat
hook) and `/etc/nginx/conf.d/<domain>.d/` for app-specific includes.
YunoHost's vhost applies SSO (`access_by_lua_file .../access.lua`) to
**every** location by default, which would reject Alexa's unauthenticated
POST requests. To bypass SSO for this app, `/etc/nginx/conf.d/radio.tildaslash.sh.d/maxradio.conf` contains:

```nginx
location / {
    access_by_lua_block { return }
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

(`access_by_lua_block { return }` is a no-op Lua override that disables the
inherited SSO check for just this location — `{}` alone is invalid Lua and
will fail `nginx -t`.)

### Redeploying after code changes
```bash
rsync -az --exclude='.venv' --exclude='.git' --exclude='.env' \
  --exclude='__pycache__' --exclude='*.pyc' \
  ./ root@<server-ip>:/opt/alexa_maximum_radio/
ssh root@<server-ip> "cd /opt/alexa_maximum_radio && \
  .venv/bin/pip install -r requirements.txt && \
  systemctl restart maxradio.service"
```

### Useful diagnostics on the server
```bash
systemctl status maxradio.service
journalctl -u maxradio.service -n 50 --no-pager
tail -f /var/log/nginx/radio.tildaslash.sh-access.log
tail -f /var/log/nginx/radio.tildaslash.sh-error.log
nginx -t                       # validate config before reloading
systemctl reload nginx
```

### Setting up a brand-new production host (non-YunoHost)
If deploying to a plain VPS instead: install Nginx + Certbot, obtain a cert
with `certbot --nginx -d <domain>`, and run the Flask app under `gunicorn`
as a systemd service the same way `maxradio.service` does. Update the
skill's endpoint in the developer console to the new domain once ready. See
PLAN.md Phase D for the original step-by-step.

## Security notes

- Request signature/timestamp/skill-ID verification is handled automatically
  by `flask_ask_sdk.SkillAdapter` — do not bypass or reimplement it.
- Never hardcode secrets or the skill ID in code; everything sensitive is
  read from environment variables via `app/config.py`.
- `AudioPlayer` request handlers (`PlaybackStarted`, `PlaybackFinished`,
  etc.) must never return `outputSpeech`, `card`, `reprompt`, or
  non-`AudioPlayer` directives.
