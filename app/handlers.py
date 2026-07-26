"""Request handlers for the Maximum Radio Alexa skill.

Handles the small set of intents needed for a single always-on live
stream: start/resume playback, pause/stop, help, and the AudioPlayer
lifecycle requests Alexa sends to report playback state.
"""

import logging

from ask_sdk_core.dispatch_components import (
    AbstractExceptionHandler,
    AbstractRequestHandler,
)
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_intent_name, is_request_type
from ask_sdk_model import Response
from ask_sdk_model.interfaces.audioplayer import (
    AudioItem,
    PlayBehavior,
    PlayDirective,
    Stream,
    StopDirective,
)
from ask_sdk_model.ui import SimpleCard

from app.config import STATION_NAME, STATION_URL

logger = logging.getLogger(__name__)

STREAM_TOKEN = "live-stream"


def _play_directive(offset_in_milliseconds: int = 0) -> PlayDirective:
    """Build a REPLACE_ALL Play directive pointing at the live stream."""
    return PlayDirective(
        play_behavior=PlayBehavior.REPLACE_ALL,
        audio_item=AudioItem(
            stream=Stream(
                token=STREAM_TOKEN,
                url=STATION_URL,
                offset_in_milliseconds=offset_in_milliseconds,
            )
        ),
    )


class LaunchOrPlayIntentHandler(AbstractRequestHandler):
    """Starts (or restarts) the live stream from the beginning."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input) or is_intent_name(
            "PlayRadioIntent"
        )(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speech = f"Starting {STATION_NAME}."
        return (
            handler_input.response_builder.speak(speech)
            .set_card(SimpleCard(STATION_NAME, speech))
            .add_directive(_play_directive())
            .set_should_end_session(True)
            .response
        )


class ResumeIntentHandler(AbstractRequestHandler):
    """AMAZON.ResumeIntent - live stream has no saved offset, just restart."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.ResumeIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder.add_directive(_play_directive())
            .set_should_end_session(True)
            .response
        )


class PauseIntentHandler(AbstractRequestHandler):
    """AMAZON.PauseIntent - required by the AudioPlayer interface."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.PauseIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder.add_directive(StopDirective())
            .set_should_end_session(True)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """AMAZON.CancelIntent / AMAZON.StopIntent - stop playback with a goodbye."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.CancelIntent")(handler_input) or is_intent_name(
            "AMAZON.StopIntent"
        )(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return (
            handler_input.response_builder.speak("Goodbye!")
            .add_directive(StopDirective())
            .set_should_end_session(True)
            .response
        )


class HelpIntentHandler(AbstractRequestHandler):
    """AMAZON.HelpIntent - explain the available voice commands."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speech = (
            f"You can say play to start {STATION_NAME}, "
            "pause or stop to stop it, or resume to start it again."
        )
        return (
            handler_input.response_builder.speak(speech)
            .ask(speech)
            .set_should_end_session(False)
            .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    """AMAZON.FallbackIntent - catch utterances that don't match anything."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        speech = "Sorry, I didn't understand that. Say play, pause, or stop."
        return (
            handler_input.response_builder.speak(speech)
            .ask(speech)
            .set_should_end_session(False)
            .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response


class PlaybackStartedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackStarted - no response allowed, just acknowledge."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("AudioPlayer.PlaybackStarted")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("Playback started")
        return handler_input.response_builder.response


class PlaybackFinishedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackFinished - stream ended on its own (unexpected for live radio)."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("AudioPlayer.PlaybackFinished")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("Playback finished")
        return handler_input.response_builder.response


class PlaybackStoppedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackStopped - Alexa stopped playback (voice request, Stop, etc.)."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("AudioPlayer.PlaybackStopped")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        logger.info("Playback stopped")
        return handler_input.response_builder.response


class PlaybackNearlyFinishedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackNearlyFinished - no-op, a live stream has no next track."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("AudioPlayer.PlaybackNearlyFinished")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response


class PlaybackFailedHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackFailed - try to reconnect the live stream once."""

    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("AudioPlayer.PlaybackFailed")(handler_input)

    def handle(self, handler_input: HandlerInput) -> Response:
        error = handler_input.request_envelope.request.error
        logger.error("Playback failed: %s", error)
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True

    def handle(self, handler_input: HandlerInput, exception: Exception) -> Response:
        logger.error("Unhandled exception", exc_info=exception)
        speech = "Sorry, something went wrong. Please try again."
        return (
            handler_input.response_builder.speak(speech)
            .ask(speech)
            .set_should_end_session(False)
            .response
        )


REQUEST_HANDLERS = [
    LaunchOrPlayIntentHandler(),
    ResumeIntentHandler(),
    PauseIntentHandler(),
    CancelOrStopIntentHandler(),
    HelpIntentHandler(),
    FallbackIntentHandler(),
    SessionEndedRequestHandler(),
    PlaybackStartedHandler(),
    PlaybackFinishedHandler(),
    PlaybackStoppedHandler(),
    PlaybackNearlyFinishedHandler(),
    PlaybackFailedHandler(),
]

EXCEPTION_HANDLERS = [
    CatchAllExceptionHandler(),
]
