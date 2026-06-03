class CalDAVError(Exception):
    """Base error for CalDAV operations."""


class AuthError(CalDAVError):
    """Authentication failed — check credentials."""


class NotFoundError(CalDAVError):
    """Calendar or event not found."""


class ConflictError(CalDAVError):
    """Resource was modified by another client (ETag mismatch)."""


class RateLimitError(CalDAVError):
    """Server rate limit exceeded."""


class ReadOnlyError(CalDAVError):
    """Write operation blocked by read-only mode."""
