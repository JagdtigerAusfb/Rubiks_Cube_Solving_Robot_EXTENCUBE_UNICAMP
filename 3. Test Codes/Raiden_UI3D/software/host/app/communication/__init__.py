"""Ponto único de abertura do link serial global (host <-> firmware).

Responsabilidades DESTE arquivo (e só dele):
  - autodetectar a porta do Arduino (com override e fallback claros);
  - abrir a porta com pyserial no baud do contrato;
  - instanciar UM SerialLink global, serializado por lock (mestre/escravo);
  - expor esse link para todos os main_*.py.

Regra de negócio (sequenciar tarefas, revalidar, reagir a erro) NÃO mora aqui;
mora nos main_*.py. Aqui é só transporte + ciclo de vida da conexão.
"""

import threading

import serial
from serial.tools import list_ports

from .embedded import BAUD, ProtocolError, SerialLink

# VID/PIDs comuns de placas Arduino e clones (usados na autodetecção).
# Uno/Mega oficiais (ATmega16U2) = 0x2341; clones CH340 = 0x1A86; FTDI = 0x0403.
_ARDUINO_VIDS = {0x2341, 0x2A03, 0x1A86, 0x0403, 0x10C4}


class SerialConnectionError(Exception):
    """Falha ao localizar/abrir a porta do firmware."""


def detect_port() -> str:
    """Retorna o device (ex.: 'COM5', '/dev/ttyACM0') da placa detectada.

    Levanta SerialConnectionError se achar zero ou mais de uma candidata,
    listando o que viu — nunca 'chuta' uma porta.
    """
    ports = list(list_ports.comports())
    candidates = [p for p in ports if (p.vid in _ARDUINO_VIDS)]

    if len(candidates) == 1:
        return candidates[0].device

    if not candidates:
        visible = ", ".join(f"{p.device}({p.vid:#06x})" if p.vid else p.device
                            for p in ports) or "nenhuma porta serial"
        raise SerialConnectionError(
            f"Nenhum Arduino detectado. Portas visíveis: {visible}. "
            f"Passe a porta manualmente: open_link(port='COM5')."
        )

    achadas = ", ".join(p.device for p in candidates)
    raise SerialConnectionError(
        f"Mais de uma placa candidata ({achadas}). "
        f"Especifique qual: open_link(port='{candidates[0].device}')."
    )


class _LockedSerialLink(SerialLink):
    """SerialLink cujas operações são atômicas (um lock por ciclo Tx->Rx).

    Garante o invariante mestre/escravo mesmo se dois chamadores concorrerem
    (futuro event bus). Hoje, em uso sequencial via terminal, é transparente.
    """

    def __init__(self, port):
        super().__init__(port)
        self._lock = threading.Lock()

    # Envolve cada operação pública do SerialLink no lock. Como cada uma já é
    # um ciclo completo (envia + lê resposta), travar aqui serializa o link.
    def calibrate(self):
        with self._lock: return super().calibrate()
    def scan(self):
        with self._lock: return super().scan()
    def sense(self):
        with self._lock: return super().sense()
    def move(self, seq):
        with self._lock: return super().move(seq)
    def read_color(self, ns):
        with self._lock: return super().read_color(ns)
    def set_speed(self, us):
        with self._lock: return super().set_speed(us)
    def set_gap(self, ms):
        with self._lock: return super().set_gap(ms)
    def wait_ready(self):
        with self._lock: return super().wait_ready()


# --- Singleton do link global -----------------------------------------
_link = None
_port_obj = None


def open_link(port: str | None = None, timeout: float = 2.0,
              wait_ready: bool = True) -> _LockedSerialLink:
    """Abre (uma vez) e devolve o link global.

    port: device explícito; se None, autodetecta.
    timeout: leitura, em s — evita o Rx travar esperando '*'.
    wait_ready: consome o banner READY* do boot (reset ao abrir a porta).
    """
    global _link, _port_obj
    if _link is not None:
        return _link

    device = port or detect_port()
    try:
        _port_obj = serial.Serial(device, BAUD, timeout=timeout)
    except serial.SerialException as e:
        raise SerialConnectionError(f"Não abriu {device}: {e}") from e

    _link = _LockedSerialLink(_port_obj)

    if wait_ready:
        # Abrir a porta reseta o Arduino; ele leva ~1-2 s e emite READY*.
        try:
            _link.wait_ready()
        except ProtocolError:
            pass   # sem banner (ex.: já estava aberto): segue mesmo assim
    return _link


def get_link() -> _LockedSerialLink:
    """Retorna o link já aberto; erro se open_link() não foi chamado."""
    if _link is None:
        raise SerialConnectionError("Link não inicializado — chame open_link() primeiro.")
    return _link


def close_link():
    """Fecha a porta e zera o singleton (para reabrir/trocar de placa)."""
    global _link, _port_obj
    if _port_obj is not None:
        _port_obj.close()
    _link = None
    _port_obj = None