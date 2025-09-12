"""
Video recording functionality for experiments.
Supports camera preview and synchronized recording with experiment data.
"""

from __future__ import annotations

import datetime
import queue
import threading
import time
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path
from typing import Any

import cv2

logger = getLogger(__name__)


@dataclass
class CameraConfig:
    """Camera configuration settings."""

    device_id: int = 0
    fps: float = 30.0
    resolution: tuple[int, int] = (640, 480)
    codec: str = "mp4v"
    preview_fps: float = 15.0  # Preview can have lower FPS than recording
    show_timestamp: bool = True
    timestamp_format: str = "%H:%M:%S.%f"


class VideoRecorder:
    """
    Handles video recording and preview for experiments.
    Gracefully degrades if OpenCV is not available.
    """

    def __init__(self, config: CameraConfig | None = None):
        """
        Initialize the video recorder.

        Args:
            config: Camera configuration. Uses defaults if None.
        """
        self.config = config or CameraConfig()
        self._ui_resolution: tuple[int, int] | None = None
        self._ui_show_timestamp: bool | None = None
        self.is_recording = False
        self.is_previewing = False
        self.capture: cv2.VideoCapture | None = None
        self.writer: cv2.VideoWriter | None = None
        self.preview_queue: queue.Queue[Any] = queue.Queue(maxsize=2)
        self.recording_thread: threading.Thread | None = None
        self.preview_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.start_time: float | None = None
        self.save_path: Path | None = None

        # OpenCV is now a required dependency

    @property
    def is_available(self) -> bool:
        """Check if video recording is available."""
        return True

    def update_ui_settings(
        self, resolution: tuple[int, int] | None = None, show_timestamp: bool | None = None
    ):
        """
        Update UI settings that override config defaults.

        Args:
            resolution: Camera resolution (width, height). None to use config default.
            show_timestamp: Whether to show timestamp. None to use config default.
        """
        self._ui_resolution = resolution
        self._ui_show_timestamp = show_timestamp

    @property
    def current_resolution(self) -> tuple[int, int]:
        """Get current resolution (UI override or config default)."""
        return self._ui_resolution or self.config.resolution

    @property
    def current_show_timestamp(self) -> bool:
        """Get current show_timestamp setting (UI override or config default)."""
        return (
            self._ui_show_timestamp
            if self._ui_show_timestamp is not None
            else self.config.show_timestamp
        )

    def get_available_cameras(self) -> list[tuple[int, str]]:
        """
        Get list of available cameras.

        Returns:
            List of (device_id, name) tuples.
        """

        cameras = []
        # Suppress OpenCV error messages during camera detection
        import os

        old_level = os.environ.get("OPENCV_LOG_LEVEL")
        os.environ["OPENCV_LOG_LEVEL"] = "SILENT"

        # Check only first 3 camera indices
        for i in range(3):
            try:
                # Try to open camera with appropriate backend
                cap = None
                if os.name == "nt":
                    # Try DirectShow first on Windows
                    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if not cap.isOpened():
                        # Fallback to default
                        cap = cv2.VideoCapture(i)
                else:
                    cap = cv2.VideoCapture(i)

                if cap and cap.isOpened():
                    # Test if camera actually works by reading a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        name = f"Camera {i}"
                        cameras.append((i, name))
                        logger.debug(f"Found camera {i}")
                    cap.release()
            except Exception as e:
                logger.debug(f"Error checking camera {i}: {e}")

        # Restore log level
        if old_level is not None:
            os.environ["OPENCV_LOG_LEVEL"] = old_level
        else:
            os.environ.pop("OPENCV_LOG_LEVEL", None)

        logger.info(f"Found {len(cameras)} camera(s)")
        return cameras

    def start_preview(self, device_id: int | None = None) -> bool:
        """
        Start camera preview without recording.

        Args:
            device_id: Camera device ID. Uses config default if None.

        Returns:
            True if preview started successfully.
        """

        if self.is_previewing:
            logger.warning("Preview already running")
            return False

        device = device_id if device_id is not None else self.config.device_id

        # Open camera
        import os

        # Try opening with different backends
        if os.name == "nt":
            # Try DirectShow first
            self.capture = cv2.VideoCapture(device, cv2.CAP_DSHOW)
            if not self.capture.isOpened():
                logger.warning("Failed with DirectShow, trying default backend")
                self.capture = cv2.VideoCapture(device)
        else:
            self.capture = cv2.VideoCapture(device)

        if not self.capture.isOpened():
            logger.error(f"Failed to open camera {device}")
            return False

        # Set resolution (may not work with all backends)
        try:
            resolution = self.current_resolution
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        except Exception:
            logger.warning("Failed to set camera resolution, using default")

        # Test if camera actually works
        ret, test_frame = self.capture.read()
        if not ret or test_frame is None:
            logger.error("Camera opened but cannot read frames")
            self.capture.release()
            self.capture = None
            return False

        # Start preview thread
        self.is_previewing = True
        self.stop_event.clear()
        self.preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self.preview_thread.start()

        logger.info(f"Started camera preview on device {device}")
        width = self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        logger.debug(f"Camera resolution: {width}x{height}")
        return True

    def stop_preview(self):
        """Stop camera preview."""
        if not self.is_previewing:
            return

        self.is_previewing = False
        self.stop_event.set()

        if self.preview_thread:
            self.preview_thread.join(timeout=2.0)

        if self.capture:
            self.capture.release()
            self.capture = None

        # Clear the preview queue
        while not self.preview_queue.empty():
            try:
                self.preview_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("Stopped camera preview")

    def start_recording(self, save_path: Path, device_id: int | None = None) -> bool:
        """
        Start recording video to file.

        Args:
            save_path: Path to save the video file.
            device_id: Camera device ID. Uses config default if None.

        Returns:
            True if recording started successfully.
        """

        if self.is_recording:
            logger.warning("Recording already in progress")
            return False

        device = device_id if device_id is not None else self.config.device_id

        # Create save path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        self.save_path = save_path

        # Open camera if not already open for preview
        if not self.capture:
            import os

            # Try opening with different backends
            if os.name == "nt":
                # Try DirectShow first
                self.capture = cv2.VideoCapture(device, cv2.CAP_DSHOW)
                if not self.capture.isOpened():
                    logger.warning("Failed with DirectShow, trying default backend")
                    self.capture = cv2.VideoCapture(device)
            else:
                self.capture = cv2.VideoCapture(device)

            if not self.capture.isOpened():
                logger.error(f"Failed to open camera {device}")
                return False

            # Set resolution (may not work with all backends)
            try:
                resolution = self.current_resolution
                self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
                self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
            except Exception:
                logger.warning("Failed to set camera resolution, using default")

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*self.config.codec)
        resolution = self.current_resolution
        self.writer = cv2.VideoWriter(
            str(self.save_path),
            fourcc,
            self.config.fps,
            resolution,
        )

        if not self.writer.isOpened():
            logger.error(f"Failed to create video writer for {self.save_path}")
            return False

        # Start recording thread
        self.is_recording = True
        self.start_time = time.perf_counter()
        self.stop_event.clear()
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.recording_thread.start()

        logger.info(f"Started recording to {self.save_path}")
        return True

    def stop_recording(self) -> Path | None:
        """
        Stop recording video.

        Returns:
            Path to the saved video file, or None if not recording.
        """
        if not self.is_recording:
            return None

        self.is_recording = False
        self.stop_event.set()

        if self.recording_thread:
            self.recording_thread.join(timeout=5.0)

        if self.writer:
            self.writer.release()
            self.writer = None

        # Release capture if not previewing
        if not self.is_previewing and self.capture:
            self.capture.release()
            self.capture = None

        logger.info(f"Stopped recording. Video saved to {self.save_path}")
        return self.save_path

    def get_preview_frame(self) -> tuple[bool, Any] | tuple[bool, None]:
        """
        Get the latest preview frame.

        Returns:
            (success, frame) tuple. Frame is None if no frame available.
        """
        try:
            frame = self.preview_queue.get_nowait()
            return True, frame
        except queue.Empty:
            return False, None

    def _preview_loop(self):
        """Preview loop running in a separate thread."""
        if not self.capture:
            logger.error("Preview loop: capture is None")
            return

        logger.info("Preview loop started")
        frame_interval = 1.0 / self.config.preview_fps
        last_frame_time = 0
        frame_count = 0

        while self.is_previewing and not self.stop_event.is_set():
            current_time = time.perf_counter()

            # Control preview FPS
            if current_time - last_frame_time < frame_interval:
                time.sleep(0.001)
                continue

            ret, frame = self.capture.read()
            if not ret or frame is None:
                logger.warning("Failed to read frame from camera")
                time.sleep(0.1)
                continue

            frame_count += 1
            if frame_count % 30 == 1:  # Log every 30 frames
                shape_info = frame.shape if frame is not None else 'None'
                logger.debug(f"Preview: captured frame {frame_count}, shape: {shape_info}")

            # Add timestamp if configured
            if self.current_show_timestamp and not self.is_recording:
                # Only show timestamp in preview if not recording
                # (recording adds its own synced timestamp)
                timestamp = datetime.datetime.now().strftime(self.config.timestamp_format)[:-3]
                cv2.putText(
                    frame,
                    timestamp,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )

            # Put frame in preview queue (non-blocking)
            try:
                self.preview_queue.put_nowait(frame)
                if frame_count == 1:
                    logger.debug("First frame added to preview queue")
            except queue.Full:
                # Remove old frame and add new one
                try:
                    self.preview_queue.get_nowait()
                    self.preview_queue.put_nowait(frame)
                except queue.Empty:
                    pass

            last_frame_time = current_time

        logger.info("Preview loop ended")

    def _recording_loop(self):
        """Recording loop running in a separate thread."""
        if not self.capture or not self.writer:
            return

        frame_interval = 1.0 / self.config.fps
        last_frame_time = 0

        while self.is_recording and not self.stop_event.is_set():
            current_time = time.perf_counter()

            # Control recording FPS
            if current_time - last_frame_time < frame_interval:
                time.sleep(0.001)
                continue

            ret, frame = self.capture.read()
            if not ret:
                logger.warning("Failed to read frame from camera")
                time.sleep(0.1)
                continue

            # Add synced timestamp
            if self.current_show_timestamp and self.start_time:
                elapsed = current_time - self.start_time
                timestamp = f"t={elapsed:.3f}s"
                cv2.putText(
                    frame,
                    timestamp,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),  # Green for recording
                    2,
                )

            # Write frame to video file
            self.writer.write(frame)

            # Also update preview if previewing
            if self.is_previewing:
                try:
                    self.preview_queue.put_nowait(frame)
                except queue.Full:
                    # Remove old frame and add new one
                    try:
                        self.preview_queue.get_nowait()
                        self.preview_queue.put_nowait(frame)
                    except queue.Empty:
                        pass

            last_frame_time = current_time

    def cleanup(self):
        """Clean up resources."""
        self.stop_preview()
        self.stop_recording()


# Singleton instance for easy access
_recorder_instance: VideoRecorder | None = None


def get_video_recorder() -> VideoRecorder:
    """Get the global video recorder instance with settings from configuration."""
    global _recorder_instance
    if _recorder_instance is None:
        # Load settings from configuration
        from .settings import get_settings

        settings = get_settings()
        camera_settings = settings.camera

        # Create config from settings
        config = CameraConfig(
            device_id=camera_settings.default_device_id,
            fps=camera_settings.recording_fps,
            resolution=(camera_settings.resolution_width, camera_settings.resolution_height),
            codec=camera_settings.codec,
            preview_fps=camera_settings.preview_fps,
            show_timestamp=camera_settings.show_timestamp,
            timestamp_format=camera_settings.timestamp_format,
        )

        _recorder_instance = VideoRecorder(config)
    return _recorder_instance
