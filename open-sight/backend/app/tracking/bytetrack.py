class ByteTrackAdapter:
    """Optional adapter. Keeps tracking behind a replaceable interface."""
    def __init__(self):
        try:
            import supervision as sv
        except ImportError as exc:
            raise RuntimeError("Install supervision to enable tracking") from exc
        self.tracker = sv.ByteTrack()
