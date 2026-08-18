"""Espelho Python do serial_protocol.md — a ponte host <-> firmware.

Host é MESTRE: envia um comando (Tx) e aguarda a resposta terminada em '*'
(Rx) antes do próximo. Tx monta/serializa; Rx lê/parseia/decide erro.
A porta serial é injetada (pyserial real ou Arduino Uno de teste), então
nenhuma das classes conhece o transporte concreto.
"""

# ----------------------------------------------------------------------
# Exceções — cada e<n>* do contrato vira um tipo nomeado
# ----------------------------------------------------------------------
class FirmwareError(Exception):
    """Base: firmware respondeu e<n>*."""
    code = None

class UnknownCommandError(FirmwareError):   code = 0   # e0
class InvalidMoveError(FirmwareError):      code = 1   # e1
class LineOverflowError(FirmwareError):     code = 2   # e2
class InvalidSensorError(FirmwareError):    code = 3   # e3
class CalibrationReadError(FirmwareError):  code = 4   # e4
class CalibrationPremiseError(FirmwareError): code = 5 # e5
class SenseIncompleteError(FirmwareError):  code = 6   # e6
class NotImplementedFirmwareError(FirmwareError): code = 9  # e9

_ERROR_MAP = {
    0: UnknownCommandError, 1: InvalidMoveError, 2: LineOverflowError,
    3: InvalidSensorError, 4: CalibrationReadError, 5: CalibrationPremiseError,
    6: SenseIncompleteError, 9: NotImplementedFirmwareError,
}

class ProtocolError(Exception):
    """Resposta malformada / fora do contrato (não é um e<n>* válido)."""


# ----------------------------------------------------------------------
# Constantes do contrato
# ----------------------------------------------------------------------
TERM = '*'
BAUD = 115200
NUM_SENSORS = 12
NUM_FACES = 6
STICKERS_PER_FACE = 8          # 48 no total
COLOR_ORDER = ('W', 'R', 'G', 'Y', 'O', 'B')   # ordem das cores da calibração


# ----------------------------------------------------------------------
# Tx — monta e envia comandos (host como mestre)
# ----------------------------------------------------------------------
class Tx:
    """Serializa comandos do contrato e os escreve na porta, com '*' final.

    Só constrói e envia — não lê resposta. Cada método corresponde a uma
    linha da tabela 'Host -> Firmware' do serial_protocol.md.
    """

    def __init__(self, port):
        self._port = port          # objeto com .write(bytes)

    def _send(self, body: str):
        msg = (body + TERM).encode('ascii')
        self._port.write(msg)
        return body                # devolve o corpo enviado (útil p/ teste/log)

    # -- comandos de subsistema --
    def calibrate(self):        return self._send('c0')
    def scan(self):             return self._send('s0')
    def sense(self):            return self._send('r0')

    # -- movimento: 1..N chars A–R --
    def move(self, seq: str):
        seq = seq.upper()
        if not seq or any(c < 'A' or c > 'R' for c in seq):
            # falha cedo no host: não gasta ida à serial com char inválido
            raise ValueError(f"sequência de movimento inválida: {seq!r}")
        return self._send(seq)

    # -- diagnóstico / config --
    def read_color(self, ns: int):
        if not 0 <= ns < NUM_SENSORS:
            raise ValueError(f"NS fora de 0..{NUM_SENSORS-1}: {ns}")
        return self._send(f'k_{ns}')

    def set_speed(self, us: int):   return self._send(f'v_{us}')
    def set_gap(self, ms: int):     return self._send(f'g_{ms}')


# ----------------------------------------------------------------------
# Rx — lê até '*' e parseia conforme o comando que a originou
# ----------------------------------------------------------------------
class Rx:
    """Lê uma resposta (até '*') e a converte no tipo Python adequado.

    Erros e<n>* viram exceção nomeada. Como várias respostas são payloads
    'nus' (STATE, SCAN-MAP), o parsing é dirigido pelo comando esperado:
    quem chama diz o que pediu, e o Rx valida/estrutura a resposta.
    """

    def __init__(self, port, timeout_read=None):
        self._port = port
        self._timeout = timeout_read

    def _read_raw(self) -> str:
        """Lê bytes até o terminador '*'. Ignora \\r \\n (banner/eco)."""
        buf = bytearray()
        while True:
            ch = self._port.read(1)
            if not ch:                      # timeout do transporte
                raise ProtocolError("timeout aguardando '*' do firmware")
            if ch in (b'\r', b'\n'):
                continue
            if ch == b'*':
                return buf.decode('ascii', errors='replace')
            buf += ch

    def _check_error(self, body: str):
        """Se for e<n>*, levanta a exceção correspondente."""
        if len(body) >= 2 and body[0] == 'e' and body[1:].isdigit():
            code = int(body[1:])
            raise _ERROR_MAP.get(code, FirmwareError)(f"firmware retornou e{code}*")

    # -- leitura genérica (qualquer resposta), já tratando erro --
    def read(self) -> str:
        body = self._read_raw()
        self._check_error(body)
        return body

    # -- parsers por tipo de resposta --
    def read_done(self) -> float:
        """d_<seg>* -> tempo em segundos (float). Aceita 'd' sem arg -> 0.0."""
        body = self.read()
        if body == 'd':
            return 0.0
        if body.startswith('d_'):
            try:
                return float(body[2:])
            except ValueError:
                raise ProtocolError(f"DONE malformado: {body!r}")
        raise ProtocolError(f"esperava DONE, veio {body!r}")

    def read_scan(self) -> list:
        """<12 chars 1/0>* -> lista de bool (True=ON), índice = canal físico."""
        body = self.read()
        if len(body) != NUM_SENSORS or any(c not in '01' for c in body):
            raise ProtocolError(f"SCAN-MAP malformado: {body!r}")
        return [c == '1' for c in body]

    def read_state(self):
        """<48 chars W/R/G/Y/O/B>* -> matriz 6x8 (lista de listas)."""
        body = self.read()
        n = NUM_FACES * STICKERS_PER_FACE
        if len(body) != n or any(c not in 'WRGYOB' for c in body):
            raise ProtocolError(f"STATE malformado ({len(body)} chars): {body!r}")
        return [list(body[f*STICKERS_PER_FACE:(f+1)*STICKERS_PER_FACE])
                for f in range(NUM_FACES)]

    def read_color(self) -> str:
        """resposta do k_<ns>*: 1 char de cor, ou 'X' (leitura inválida)."""
        body = self.read()
        if body in ('W', 'R', 'G', 'Y', 'O', 'B', 'X'):
            return body
        raise ProtocolError(f"cor inesperada: {body!r}")

    def read_calibration(self) -> dict:
        """c0*: 6 H _ 6 S _ whiteSatThresh _ wR _ wG _ wB -> dict estruturado."""
        body = self.read()
        parts = body.split('_')
        if len(parts) != 16:
            raise ProtocolError(f"calibração malformada ({len(parts)} campos): {body!r}")
        try:
            vals = [float(p) for p in parts]
        except ValueError:
            raise ProtocolError(f"calibração com campo não-numérico: {body!r}")
        return {
            'hue':   dict(zip(COLOR_ORDER, vals[0:6])),
            'sat':   dict(zip(COLOR_ORDER, vals[6:12])),
            'white_sat_thresh': vals[12],
            'white_balance': {'r': vals[13], 'g': vals[14], 'b': vals[15]},
        }


# ----------------------------------------------------------------------
# SerialLink — segura a porta e orquestra o handshake mestre/escravo
# ----------------------------------------------------------------------
class SerialLink:
    """Une Tx+Rx sobre uma porta e impõe o padrão 'envia -> espera resposta'.

    A porta é injetada (pyserial real OU Arduino Uno de teste), então esta
    classe é agnóstica ao transporte. Cada método público = um ciclo completo.
    """

    def __init__(self, port):
        self._port = port
        self.tx = Tx(port)
        self.rx = Rx(port)

    # cada operação: envia comando (Tx) e consome a resposta esperada (Rx)
    def calibrate(self) -> dict:
        self.tx.calibrate();   return self.rx.read_calibration()

    def scan(self) -> list:
        self.tx.scan();        return self.rx.read_scan()

    def sense(self):
        self.tx.sense();       return self.rx.read_state()

    def move(self, seq: str) -> float:
        self.tx.move(seq);     return self.rx.read_done()

    def read_color(self, ns: int) -> str:
        self.tx.read_color(ns); return self.rx.read_color()

    def set_speed(self, us: int) -> float:
        self.tx.set_speed(us); return self.rx.read_done()

    def set_gap(self, ms: int) -> float:
        self.tx.set_gap(ms);   return self.rx.read_done()

    def wait_ready(self):
        """Consome o banner READY* de boot/reset."""
        body = self.rx.read()
        if body != 'READY':
            raise ProtocolError(f"esperava READY, veio {body!r}")