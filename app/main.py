"""Flask entrypoint that exposes the skill as a self-hosted web service.

Alexa POSTs signed requests to /alexa. flask_ask_sdk.SkillAdapter verifies
the request signature, timestamp, and skill_id before dispatching to our
registered handlers - do not bypass or reimplement that verification here.
"""

import logging

from ask_sdk_core.skill_builder import SkillBuilder
from flask import Flask
from flask_ask_sdk.skill_adapter import SkillAdapter

from app.config import ALEXA_SKILL_ID, PORT
from app.handlers import EXCEPTION_HANDLERS, REQUEST_HANDLERS

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

sb = SkillBuilder()
for handler in REQUEST_HANDLERS:
    sb.add_request_handler(handler)
for handler in EXCEPTION_HANDLERS:
    sb.add_exception_handler(handler)

skill_adapter = SkillAdapter(skill=sb.create(), skill_id=ALEXA_SKILL_ID, app=app)
skill_adapter.register(app=app, route="/alexa")


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
