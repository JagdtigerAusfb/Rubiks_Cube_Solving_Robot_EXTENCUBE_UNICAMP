"""Porta serial FALSA (em memória) que fala o protocolo do firmware.

Mimetiza a interface mínima do pyserial (write/read/close) usada pelo host.
Responde a cada comando conforme o serial_protocol.md e devolve, no r0*, um
STATE default = scramble 'R U R' U' F2 L D' (o mesmo validado com o solver).
Permite rodar o ecossistema inteiro sem hardware nenhum.
"""


class FakeSerialPort:
    # Estado sensoriado do scramble R U R' U' F2 L D (48 chars, ordem URFDLB).
    DEFAULT_STATE = ("BWOGYYRB" "ORWRGGRO" "WGGGWBRW"
                     "YWGWWYYY" "OOBOGBBO" "BRYYRROB")
    # Calibração válida (6H _ 6S _ thresh _ wR _ wG _ wB) — da bancada real.
    CALIB = ("280.9_356.2_132.1_54.1_0.6_233.6_"
             "0.086_0.741_0.624_0.863_0.961_0.813_0.355_18_18_7")
    KOLOR = "WWRRGGYYOOBB"          # cor por ns (face resolvida)

    def __init__(self):
        self._out = bytearray(b"READY*")     # banner de boot já enfileirado

    # --- interface pyserial mínima ---
    def write(self, data: bytes):
        cmd = data.decode("ascii", "replace").rstrip("*")
        self._out += (self._respond(cmd) + "*").encode("ascii")

    def read(self, n: int = 1) -> bytes:
        if not self._out:
            return b""                        # "timeout" (não ocorre em demo)
        chunk = bytes(self._out[:n])
        del self._out[:n]
        return chunk

    def close(self):
        pass

    # --- espelho do protocolo ---
    def _respond(self, cmd: str) -> str:
        if cmd == "c0":
            return self.CALIB
        if cmd == "s0":
            return "111111111111"
        if cmd == "r0":
            return self.DEFAULT_STATE
        if cmd.startswith("k_"):
            try:
                ns = int(cmd[2:])
            except ValueError:
                return "e3"
            return self.KOLOR[ns] if 0 <= ns < 12 else "e3"
        if cmd.startswith(("v_", "g_")):
            return "d_0.000"
        if cmd and all("A" <= ch <= "R" for ch in cmd):   # MOVE 1..N chars
            return f"d_{len(cmd) * 0.05:.3f}"              # tempo fake
        return "e0"