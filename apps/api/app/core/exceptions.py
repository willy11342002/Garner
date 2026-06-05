class VideoTooLongError(Exception):
    """Raised when a video's duration exceeds the processable limit, or cannot be determined."""

    MAX_DURATION_SEC = 20 * 60  # 20 minutes

    def __init__(self, duration_sec: int | None):
        self.duration_sec = duration_sec
        if duration_sec is None:
            super().__init__("Video duration unknown; cannot verify within limit")
        else:
            super().__init__(
                f"Video duration {duration_sec}s exceeds {self.MAX_DURATION_SEC}s limit"
            )
