"""Flask entrypoint that exposes the skill as a self-hosted web service.

Alexa POSTs signed requests to /alexa. flask_ask_sdk.SkillAdapter verifies
the request signature, timestamp, and skill_id before dispatching to our
registered handlers - do not bypass or reimplement that verification here.
"""

import logging
import os

from ask_sdk_core.skill_builder import SkillBuilder
from flask import Flask, Response, send_from_directory
from ask_sdk_webservice_support.verifier import AbstractVerifier, VerificationException
from flask_ask_sdk.skill_adapter import SkillAdapter

from app.config import ALEXA_SKILL_IDS, PORT
from app.handlers import EXCEPTION_HANDLERS, REQUEST_HANDLERS

ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skill-package",
    "icons",
)

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

sb = SkillBuilder()
for handler in REQUEST_HANDLERS:
    sb.add_request_handler(handler)
for handler in EXCEPTION_HANDLERS:
    sb.add_exception_handler(handler)

class SkillIdVerifier(AbstractVerifier):
    def verify(self, headers, serialized_request_env, deserialized_request_env):
        app_id = deserialized_request_env.context.system.application.application_id
        if app_id not in ALEXA_SKILL_IDS:
            raise VerificationException(f"Unknown skill ID: {app_id}")


if not ALEXA_SKILL_IDS:
    raise RuntimeError("ALEXA_SKILL_ID must be set")

skill_adapter = SkillAdapter(
    skill=sb.create(),
    skill_id="maximum-radio",
    verifiers=[SkillIdVerifier()],
    app=app,
)
skill_adapter.register(app=app, route="/alexa")


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


PRIVACY_POLICY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Maximum Radio - Privacy Policy</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family: sans-serif; max-width: 40em; margin: 2em auto; line-height: 1.5;">
  <h1>Privacy Policy for Maximum Radio (Alexa Skill)</h1>
  <p><em>Last updated: 2026-07-26</em></p>

  <p>Maximum Radio is a personal, non-commercial Alexa skill that streams a
  single fixed, publicly available internet radio station using the
  AudioPlayer interface.</p>

  <h2>What data we process</h2>
  <p>The skill does not collect, store, or share any personal information.
  It does not use account linking, does not request access to your name,
  location, contacts, or any other Alexa customer profile data, and does
  not persist any data about your requests. Each request is handled
  statelessly to start, pause, resume, or stop a fixed audio stream.</p>

  <p>Amazon's Alexa service itself may process standard request metadata
  (such as a session ID and timestamp) as part of delivering your voice
  request to this skill and returning its response, in accordance with
  <a href="https://www.amazon.com/privacy">Amazon's own privacy notice</a>.
  This skill's own backend does not log, retain, or transmit this metadata
  anywhere beyond what is needed to serve the immediate request.</p>

  <h2>Third-party streaming service</h2>
  <p>Playing the stream causes your Alexa device to connect directly to the
  third-party radio station's own streaming server to fetch the audio.
  That connection is subject to the third-party station's own terms and
  privacy practices, not this skill's.</p>

  <h2>Children's privacy</h2>
  <p>This skill is not directed at children under 13 and does not knowingly
  collect information from children.</p>

  <h2>Contact</h2>
  <p>Questions about this policy can be sent to the developer via the
  contact details listed on this skill's Alexa Skill Store page.</p>
</body>
</html>
"""


@app.route("/privacy", methods=["GET"])
def privacy():
    return Response(PRIVACY_POLICY_HTML, mimetype="text/html")


@app.route("/assets/icon-108.png", methods=["GET"])
def icon_small():
    response = send_from_directory(ICONS_DIR, "icon_108_A2Z.png", mimetype="image/png")
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/assets/icon-512.png", methods=["GET"])
def icon_large():
    response = send_from_directory(ICONS_DIR, "icon_512_A2Z.png", mimetype="image/png")
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)

