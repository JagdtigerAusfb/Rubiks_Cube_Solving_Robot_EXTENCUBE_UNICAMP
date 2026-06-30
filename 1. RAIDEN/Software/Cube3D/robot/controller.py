import logging
import time

import pygame
import serial
import serial.tools.list_ports

logger = logging.getLogger(__name__)

DEFAULT_PORT     = "COM4"
DEFAULT_BAUDRATE = 9600
DEFAULT_SPEED    = 1000
DEFAULT_DELAY    = 0
CONNECT_WAIT_S   = 3


class RobotController:
    def __init__(self):
        self.ser = None
        self.port = DEFAULT_PORT
        self.speed = DEFAULT_SPEED
        self.delay = DEFAULT_DELAY
        self.last_solve_time = "--"
        self.last_solution = None
        self.last_move_count = "--"
        self.is_busy = False
        self.auto_connect()

    # ------------------------------------------------------------------
    # Conexão serial
    # ------------------------------------------------------------------

    def auto_connect(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if self.port in ports:
            self.connect(self.port)
        elif ports:
            self.connect(ports[0])
        else:
            logger.warning("Nenhuma porta serial encontrada.")

    def connect(self, port: str) -> bool:
        """
        Abre a conexão serial com o robô.
        O sleep de 3s aguarda o reset do Arduino após DTR.
        Atenção: bloqueia a thread principal — idealmente rodar em thread separada.
        """
        try:
            if self.ser:
                self.ser.close()
            ser = serial.Serial()
            ser.port = port
            ser.baudrate = DEFAULT_BAUDRATE
            ser.timeout = 0.1
            ser.setDTR(False)
            ser.open()
            time.sleep(CONNECT_WAIT_S)
            self.ser = ser
            self.port = port
            logger.info("Conectado em %s", port)
            return True
        except serial.SerialException as e:
            logger.error("Falha ao conectar em %s: %s", port, e)
            self.ser = None
            return False

    # ------------------------------------------------------------------
    # Comunicação
    # ------------------------------------------------------------------

    def check_for_done(self):
        """Verifica se o robô enviou 'DONE'. Deve ser chamado a cada frame."""
        if not self.ser or not self.is_busy:
            return
        if self.ser.in_waiting:
            try:
                line = self.ser.readline().decode().strip()
                if line.startswith("DONE"):
                    parts = line.split()
                    if len(parts) > 1:
                        self.last_solve_time = parts[1]
                    self.is_busy = False
                    pygame.event.clear()
            except Exception as e:
                logger.warning("Erro ao ler serial: %s", e)

    def send_moves(self, sequence_str: str):
        """Envia uma sequência de movimentos ao robô via serial."""
        if not self.ser or not self.ser.is_open:
            logger.warning("Tentativa de envio sem conexão serial.")
            return
        try:
            self.ser.write(b"<START>\n")
            self.ser.write(f"<SPEED:{self.speed}>\n".encode())
            self.ser.write(f"<DELAY:{self.delay}>\n".encode())
            for move in sequence_str:
                self.ser.write((move + "\n").encode())
                time.sleep(0.01)
            self.ser.write(b"<END>\n")
            self.is_busy = True
        except serial.SerialException as e:
            logger.error("Erro ao enviar movimentos: %s", e)
            self.is_busy = False
