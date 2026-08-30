"""Robot serial controller — manages the Arduino connection and move dispatch."""

import logging
import time

import serial
import serial.tools.list_ports

from config import SERIAL_BAUDRATE, SERIAL_TIMEOUT, SERIAL_INIT_DELAY, MOVE_TABLE

logger = logging.getLogger(__name__)


class RobotController:
    """Handles opening, sending, and polling the serial connection to the robot."""

    def __init__(self):
        self._serial: serial.Serial | None = None
        self.is_busy = False
        self.last_elapsed: str = "--"

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def list_ports(self) -> list[str]:
        return [p.device for p in serial.tools.list_ports.comports()]

    def connect(self, port: str) -> bool:
        """Opens the serial port without triggering Arduino reset (DTR disabled).

        Returns True on success, False on failure.
        """
        if self._serial is not None:
            return True  # already connected

        try:
            s = serial.Serial()
            s.port     = port
            s.baudrate = SERIAL_BAUDRATE
            s.timeout  = SERIAL_TIMEOUT
            s.setDTR(False)  # prevent Arduino auto-reset on connect
            s.open()
            time.sleep(SERIAL_INIT_DELAY)  # wait for firmware boot
            self._serial = s
            logger.info("Serial connected to %s", port)
            return True
        except serial.SerialException:
            logger.exception("Failed to connect to %s", port)
            self._serial = None
            return False

    def disconnect(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info("Serial disconnected")
        self._serial = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    # ------------------------------------------------------------------
    # Sending moves
    # ------------------------------------------------------------------

    def send_moves(self, sequence: str, speed: int, delay: int) -> bool:
        """Sends a pre-encoded character sequence to the robot.

        *sequence* is already in robot format (single chars from MOVE_TABLE).
        Returns False if the connection is not open or the robot is busy.
        """
        if not self.is_connected or self.is_busy:
            return False
        if not sequence:
            return False

        try:
            self.is_busy = True
            s = self._serial
            s.reset_input_buffer()
            s.reset_output_buffer()
            s.write(b"<START>\n")
            s.write(f"<SPEED:{speed}>\n".encode())
            s.write(f"<DELAY:{delay}>\n".encode())
            for move in sequence:
                s.write((move + "\n").encode())
                time.sleep(0.005)
            s.write(b"<END>\n")
            logger.info("Sent %d-move sequence to robot", len(sequence))
            return True
        except serial.SerialException:
            logger.exception("Serial write failed")
            self.is_busy = False
            return False

    # ------------------------------------------------------------------
    # Polling for completion
    # ------------------------------------------------------------------

    def check_for_done(self) -> bool:
        """Non-blocking poll. Returns True if a DONE message was just received."""
        if not self.is_connected or not self._serial.in_waiting:
            return False
        try:
            line = self._serial.readline().decode(errors="replace").strip()
            if line.startswith("DONE"):
                parts = line.split()
                self.last_elapsed = parts[1] if len(parts) > 1 else "?"
                self.is_busy = False
                logger.info("Robot finished in %s s", self.last_elapsed)
                return True
        except serial.SerialException:
            logger.exception("Serial read failed")
        return False

    # ------------------------------------------------------------------
    # Move conversion helper
    # ------------------------------------------------------------------

    @staticmethod
    def notation_to_robot(notation_sequence: str) -> str:
        """Converts a space-separated Kociemba notation string to robot chars."""
        try:
            return "".join(MOVE_TABLE[m] for m in notation_sequence.split())
        except KeyError as exc:
            raise ValueError(f"Invalid move: {exc}") from exc
