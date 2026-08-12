from collections.abc import Iterator
import cv2

class RTSPCamera:
    def __init__(self, url: str):
        self.url = url
        self.capture: cv2.VideoCapture | None = None

    def connect(self) -> bool:
        self.capture = cv2.VideoCapture(self.url)
        return bool(self.capture.isOpened())

    def frames(self) -> Iterator[object]:
        if self.capture is None and not self.connect():
            raise RuntimeError("Unable to connect to RTSP camera")
        assert self.capture is not None
        while True:
            ok, frame = self.capture.read()
            if not ok:
                break
            yield frame

    def close(self) -> None:
        if self.capture is not None:
            self.capture.release()
