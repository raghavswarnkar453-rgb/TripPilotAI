class PlannerError(Exception):
    """Base class. `status_code` and `message` are safe to return to the client."""

    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DestinationNotFound(PlannerError):
    status_code = 404


class UpstreamUnavailable(PlannerError):
    status_code = 502


class RateLimited(UpstreamUnavailable):
    status_code = 429


class ModelNotFound(UpstreamUnavailable):
    status_code = 502


class NotConfigured(PlannerError):
    status_code = 503


class ItineraryInvalid(PlannerError):
    status_code = 502


class Unauthorized(PlannerError):
    status_code = 401
