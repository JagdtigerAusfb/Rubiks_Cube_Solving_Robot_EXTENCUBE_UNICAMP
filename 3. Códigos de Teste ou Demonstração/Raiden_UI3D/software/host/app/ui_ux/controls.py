"""Ações do usuário: botões, controles, campos de inserção.

Duas responsabilidades:

1. VOCABULÁRIO — quais teclas existem, que comando cada número dispara e
   quais campos o painel de configuração expõe. É o espelho 1:1 do menu de
   terminal do main_raiden (1..9, 0), para quem já opera o robô não ter que
   reaprender nada.

2. DESPACHO — leva o comando para uma thread worker. A serial bloqueia por
   segundos (um sense mexe motor); o loop de render não pode esperar. Cada
   job roda na worker e publica o que aconteceu no barramento (inner.BUS);
   a UI só reage a eventos.

Regra de subsistema continua nos flows (sensor/solver/execution): aqui só
se compõe a mesma sequência de momentos que o Raiden compõe, com um evento
publicado entre as etapas para a tela poder acompanhar em tempo real.
"""

import queue
import threading

import pygame

from app.communication import close_link, SerialConnectionError
from app.communication.inner import Topic
from app.communication.outer import visual_to_char
from app.main_raiden import Mode, Raiden

# ----------------------------------------------------------------------
# Ações
# ----------------------------------------------------------------------
A_PREPARE = "prepare"
A_SOLVE_EXEC = "solve_exec"
A_SCAN = "scan"
A_CALIBRATE = "calibrate"
A_SENSE = "sense"
A_SOLVE = "solve"
A_EXEC_SEQ = "exec_seq"
A_METHOD = "method"
A_CONFIG = "config"
A_QUIT = "quit"

FLOWS = [
    ("1", A_PREPARE,    "Preparar",            "scan + calibração"),
    ("2", A_SOLVE_EXEC, "Resolver + Executar", "sense › solve › exec"),
]

STEPS = [
    ("3", A_SCAN,      "Scan",                 "12 sensores"),
    ("4", A_CALIBRATE, "Calibrar",             "cubo resolvido"),
    ("5", A_SENSE,     "Sensoriar",            "lê o embaralhamento"),
    ("6", A_SOLVE,     "Resolver",             "calcula a solução"),
    ("7", A_EXEC_SEQ,  "Executar sequência…",  "chars A–R"),
]

# número da tecla -> ação (mesmos números do terminal)
NUMBER_ACTIONS = {
    pygame.K_1: A_PREPARE, pygame.K_2: A_SOLVE_EXEC, pygame.K_3: A_SCAN,
    pygame.K_4: A_CALIBRATE, pygame.K_5: A_SENSE, pygame.K_6: A_SOLVE,
    pygame.K_7: A_EXEC_SEQ, pygame.K_8: A_METHOD, pygame.K_9: A_CONFIG,
    pygame.K_0: A_QUIT,
}
# teclado numérico
NUMBER_ACTIONS.update({
    pygame.K_KP1: A_PREPARE, pygame.K_KP2: A_SOLVE_EXEC, pygame.K_KP3: A_SCAN,
    pygame.K_KP4: A_CALIBRATE, pygame.K_KP5: A_SENSE, pygame.K_KP6: A_SOLVE,
    pygame.K_KP7: A_EXEC_SEQ, pygame.K_KP8: A_METHOD, pygame.K_KP9: A_CONFIG,
    pygame.K_KP0: A_QUIT,
})

# giros manuais do cubo (funcionalidade herdada do Cube3D)
MOVE_KEYS = {
    pygame.K_r: 'R', pygame.K_l: 'L', pygame.K_u: 'U',
    pygame.K_d: 'D', pygame.K_f: 'F', pygame.K_b: 'B',
}

CONFIG_HINT_ACTIVE = "↑↓ campo · ENTER aplica · ESC fecha"
CONFIG_HINT_IDLE = "[9] editar"

FOOTER_LEFT = ("[1-7] comandos    [8] método    [9] config    "
               "[R L U D F B] giro    [Shift]+giro anti-horário    "
               "[Ctrl]+giro 180°")
FOOTER_RIGHT = ("arraste com o mouse para girar a câmera    ·    "
                "[C] reposiciona o cubo virtual    ·    [0] ou [ESC] sair")


# ----------------------------------------------------------------------
# Campos de inserção do painel de configuração
# ----------------------------------------------------------------------
class Field:
    """Um campo editável do painel (o antigo diálogo [S], agora inline)."""

    def __init__(self, key, label, kind, value, options=None, unit="", hint=""):
        self.key = key
        self.label = label
        self.kind = kind            # "enum" | "int" | "text"
        self.value = value
        self.options = options or []
        self.unit = unit
        self.hint = hint
        self.buf = str(value)
        self.dirty = False

    # -- leitura --
    def display(self):
        if self.kind == "enum":
            return f"‹ {self.value} ›"
        txt = self.buf if self.buf != "" else "—"
        return f"{txt}{self.unit}" if self.buf else txt

    # -- edição --
    def cycle(self, delta):
        if self.kind != "enum" or not self.options:
            return
        i = (self.options.index(self.value) + delta) % len(self.options)
        self.value = self.options[i]
        self.buf = self.value
        self.dirty = True

    def type_char(self, ch):
        if self.kind == "int" and not ch.isdigit():
            return
        if self.kind == "enum":
            return
        if len(self.buf) < 32:
            self.buf += ch
            self.dirty = True

    def backspace(self):
        if self.kind != "enum" and self.buf:
            self.buf = self.buf[:-1]
            self.dirty = True

    def commit(self):
        """Valida o buffer e devolve o valor final (ou None se inválido)."""
        if self.kind == "enum":
            self.dirty = False
            return self.value
        if self.kind == "int":
            try:
                self.value = int(self.buf)
            except ValueError:
                self.buf = str(self.value)
                return None
        else:
            self.value = self.buf.strip()
        self.buf = str(self.value)
        self.dirty = False
        return self.value


class ConfigPanel:
    """Estado do painel de configuração (navegação por teclado).

    Campos de AJUSTE (método, velocidade, pausa) são aplicados sozinhos ao
    sair do campo ou fechar o painel — ninguém perde o que digitou por não
    ter apertado ENTER. Campos DESTRUTIVOS (modo, porta) reabrem o link,
    então exigem ENTER explícito e voltam ao valor real no ESC.
    """

    AUTO_APPLY = ("method", "speed", "gap")

    def __init__(self, mode, port, method, speed, gap):
        self.fields = [
            Field("mode", "Modo", "enum", mode,
                  options=[Mode.DEMO, Mode.UNO_DUMMY, Mode.REAL]),
            Field("port", "Porta serial", "text", port or "", hint="vazio = autodetectar"),
            Field("method", "Método", "enum", method, options=["kociemba", "m2op"]),
            Field("speed", "Velocidade", "int", speed, unit=" µs/passo"),
            Field("gap", "Pausa", "int", gap, unit=" ms"),
        ]
        self.index = 0
        self.active = False

    @property
    def current(self):
        return self.fields[self.index]

    def move(self, delta):
        self.index = (self.index + delta) % len(self.fields)

    def revert(self, applied):
        """Volta os campos destrutivos ao valor real do host (ESC)."""
        for f in self.fields:
            if f.key in self.AUTO_APPLY:
                continue
            if f.key in applied and applied[f.key] not in (None, ""):
                f.value = applied[f.key]
            f.buf = str(f.value)
            f.dirty = False

    def pending(self):
        """Campos de ajuste editados e ainda não aplicados."""
        return [f for f in self.fields if f.dirty and f.key in self.AUTO_APPLY]

    def field(self, key):
        for f in self.fields:
            if f.key == key:
                return f
        return None


class Prompt:
    """Campo de texto modal (entrada da sequência do comando 7)."""

    def __init__(self, title, hint, text=""):
        self.title = title
        self.hint = hint
        self.text = text


# ----------------------------------------------------------------------
# Controller — despacha os comandos para a thread worker
# ----------------------------------------------------------------------
class Controller:
    """Fila de jobs sobre o Raiden, com resultados publicados no barramento."""

    def __init__(self, bus, mode=Mode.REAL, port=None, method="kociemba",
                 speed=None, gap=None):
        self.bus = bus
        self.mode = mode
        self.port = port
        self.method = method
        self.speed = speed
        self.gap = gap
        self.raiden = None
        self._busy = False
        self._q = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="raiden-worker",
                                        daemon=True)
        self._thread.start()
        self.submit(self._job_connect, mode, port, method)

    # -- infraestrutura ------------------------------------------------
    @property
    def busy(self):
        return self._busy or not self._q.empty()

    def submit(self, fn, *args, queued=False):
        """Enfileira um job.

        Por padrão recusa se a worker está ocupada (evita empilhar fluxos
        sem querer). Ajustes de configuração passam queued=True: são
        baratos e devem entrar na fila em vez de serem descartados.
        """
        if self.busy and not queued:
            self.log("warn", "Ocupado — aguarde a etapa atual terminar.")
            return False
        self._q.put((fn, args))
        return True

    def shutdown(self):
        self._stop.set()
        self._q.put((None, ()))
        if self.raiden:
            try:
                self.raiden.close()
            except Exception:
                pass

    def _run(self):
        while not self._stop.is_set():
            fn, args = self._q.get()
            if fn is None:
                break
            self._busy = True
            self.bus.publish(Topic.BUSY, True)
            try:
                fn(*args)
            except SerialConnectionError as e:
                self.log("err", f"Conexão: {e}")
            except Exception as e:                       # ProtocolError inclusive
                self.log("err", f"{type(e).__name__}: {e}")
            finally:
                self._busy = False
                self.bus.publish(Topic.BUSY, False)

    # -- publicação ----------------------------------------------------
    def log(self, level, msg):
        self.bus.publish(Topic.LOG, (level, msg))

    def _emit(self, res):
        """StepResult -> evento de etapa + linha de log."""
        self.bus.publish(Topic.STEP, res)
        self.log("ok" if res.ok else "err", res.message)
        return res.ok

    def _link_event(self):
        self.bus.publish(Topic.LINK, {
            "mode": self.mode, "port": self.port,
            "connected": self.raiden is not None,
            "method": self.raiden.solver.method if self.raiden else self.method,
        })

    # -- jobs ----------------------------------------------------------
    def _job_connect(self, mode, port, method):
        if self.raiden is not None:
            try:
                self.raiden.close()
            except Exception:
                pass
            self.raiden = None
        try:
            close_link()
        except Exception:
            pass

        try:
            self.raiden = Raiden(mode, port or None, method)
            self.mode, self.port, self.method = mode, port, method
            self.log("ok", f"Modo {mode.upper()} pronto — solver {method}.")
        except SerialConnectionError as e:
            self.log("err", f"Conexão: {e}")
            self.raiden = Raiden(Mode.DEMO, None, method)
            self.mode = Mode.DEMO
            self.log("warn", "Caindo para DEMO (serial simulada).")
        if self.mode == Mode.REAL:
            self.log("warn", "ATENÇÃO: modo REAL — os motores vão se mover.")
        # Empurra velocidade/pausa do painel para o firmware, senão a tela
        # mostraria um valor que a placa nunca recebeu (ela tem os próprios
        # defaults e é resetada a cada abertura de porta).
        try:
            if self.speed is not None:
                self.raiden.set_speed(int(self.speed))
            if self.gap is not None:
                self.raiden.set_gap(int(self.gap))
            self.log("info", f"Velocidade {self.speed} µs/passo · "
                             f"pausa {self.gap} ms aplicadas.")
        except Exception as e:
            self.log("warn", f"Não apliquei velocidade/pausa: {e}")
        self._link_event()

    def _need(self):
        if self.raiden is None:
            self.log("err", "Sem link — configure o modo/porta em [9].")
            return None
        return self.raiden

    # Momento 1 — scan › calibração (mesma composição de Raiden.prepare)
    def _job_prepare(self):
        rd = self._need()
        if not rd:
            return
        if not self._emit(rd.scan()):
            return
        self._emit(rd.calibrate())

    # Momento 2 — scan › sense › solve › exec (o "botão solver")
    def _job_solve_exec(self):
        rd = self._need()
        if not rd:
            return
        if not self._emit(rd.scan()):
            return
        # A partir daqui vale o cronômetro: sensoriamento -> cubo resolvido.
        self.bus.publish(Topic.RUN)
        r = rd.sense()
        if r.ok:
            self.bus.publish(Topic.STATE, r.data)
        if not self._emit(r):
            return
        s = rd.solve()
        if s.ok:
            self.bus.publish(Topic.SOLUTION, s.data)
        if not self._emit(s):
            return
        seq = s.data["robot_sequence"]
        self.bus.publish(Topic.EXEC_START, seq)
        self._emit(rd.execute(seq))

    def _job_scan(self):
        rd = self._need()
        if rd:
            self._emit(rd.scan())

    def _job_calibrate(self):
        rd = self._need()
        if rd:
            self._emit(rd.calibrate())

    def _job_sense(self):
        rd = self._need()
        if not rd:
            return
        self.bus.publish(Topic.RUN)
        r = rd.sense()
        if r.ok:
            self.bus.publish(Topic.STATE, r.data)
        self._emit(r)

    def _job_solve(self):
        rd = self._need()
        if not rd:
            return
        r = rd.solve()
        if r.ok:
            self.bus.publish(Topic.SOLUTION, r.data)
        self._emit(r)

    def _job_execute(self, seq):
        rd = self._need()
        if not rd:
            return
        self.bus.publish(Topic.RUN)
        self.bus.publish(Topic.EXEC_START, seq)
        self._emit(rd.execute(seq))

    def _job_move(self, char):
        rd = self._need()
        if not rd:
            return
        r = rd.execute(char)
        if not r.ok:
            self._emit(r)

    def _job_set_method(self, name):
        rd = self._need()
        if not rd:
            return
        if self._emit(rd.set_method(name)):
            self.method = name
            self._link_event()

    def _job_set_speed(self, us):
        rd = self._need()
        if rd and self._emit(rd.set_speed(us)):
            self.speed = us

    def _job_set_gap(self, ms):
        rd = self._need()
        if rd and self._emit(rd.set_gap(ms)):
            self.gap = ms

    # -- API usada pela UI --------------------------------------------
    def dispatch(self, action, arg=None):
        table = {
            A_PREPARE: self._job_prepare,
            A_SOLVE_EXEC: self._job_solve_exec,
            A_SCAN: self._job_scan,
            A_CALIBRATE: self._job_calibrate,
            A_SENSE: self._job_sense,
            A_SOLVE: self._job_solve,
        }
        if action in table:
            return self.submit(table[action])
        return False

    def execute_sequence(self, seq):
        return self.submit(self._job_execute, seq)

    def manual_move(self, face, turns):
        char = visual_to_char(face, turns)
        if char:
            return self.submit(self._job_move, char)
        return False

    def apply_field(self, field):
        """Aplica um campo do painel de config (chamado no ENTER)."""
        value = field.commit()
        if value is None:
            self.log("err", f"{field.label}: valor inválido.")
            return
        if field.key == "method":
            self.submit(self._job_set_method, value, queued=True)
        elif field.key == "speed":
            self.submit(self._job_set_speed, int(value), queued=True)
        elif field.key == "gap":
            self.submit(self._job_set_gap, int(value), queued=True)
        elif field.key in ("mode", "port"):
            self.log("info", "Reconectando…")
            self.submit(self._job_connect,
                        field.value if field.key == "mode" else self.mode,
                        value if field.key == "port" else self.port,
                        self.method)

    def last_solution_sequence(self):
        rd = self.raiden
        return (rd._last_solution or "") if rd else ""
