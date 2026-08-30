"""Comunicação entre os main_*.py — barramento de eventos (publish/subscribe).

Antes: placeholder, porque a operação por terminal era sequencial e direta.
Agora a GUI existe e o sistema tem DUAS threads: a de render (60 fps, nunca
pode bloquear) e a worker (fala serial, bloqueia por segundos). Este é o
único ponto de encontro entre elas.

Invariante: publish() pode ser chamado de QUALQUER thread; os handlers só
rodam quando alguém chama drain(), ou seja, SEMPRE na thread que consome
(a de render). Assim nenhum estado da UI é tocado pela thread worker.

Regra de negócio continua fora daqui: isto é só transporte de eventos.
"""

import queue
import threading


class EventBus:
    """Fila de eventos thread-safe com despacho adiado (pull, não push)."""

    def __init__(self, maxsize: int = 512):
        self._q = queue.Queue(maxsize=maxsize)
        self._subs = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def subscribe(self, topic: str, handler):
        """Registra handler(payload) para um tópico. Chamar antes do loop."""
        with self._lock:
            self._subs.setdefault(topic, []).append(handler)

    def publish(self, topic: str, payload=None):
        """Enfileira um evento. Seguro de qualquer thread; nunca bloqueia."""
        try:
            self._q.put_nowait((topic, payload))
        except queue.Full:
            pass                      # UI atrasada: descarta em vez de travar

    # ------------------------------------------------------------------
    def drain(self, max_events: int = 128) -> list:
        """Consome os eventos pendentes, despacha aos handlers e os devolve.

        Chamado uma vez por frame pela thread de render.
        """
        drained = []
        for _ in range(max_events):
            try:
                topic, payload = self._q.get_nowait()
            except queue.Empty:
                break
            drained.append((topic, payload))
            with self._lock:
                handlers = list(self._subs.get(topic, ()))
            for h in handlers:
                h(payload)
        return drained


# Barramento global do processo (um sistema, um barramento).
BUS = EventBus()


# ----------------------------------------------------------------------
# Tópicos canônicos (fonte única dos nomes — evita string solta na UI)
# ----------------------------------------------------------------------
class Topic:
    LOG = "log"             # payload: (nivel, texto)  nivel: ok/err/warn/info
    BUSY = "busy"           # payload: bool
    STEP = "step"           # payload: StepResult
    STATE = "state"         # payload: matriz 6x8 sensoriada
    SOLUTION = "solution"   # payload: dict do solver
    EXEC_START = "exec"     # payload: robot_sequence (chars A-R)
    RUN = "run"             # payload: None — começou o ciclo cronometrado
    LINK = "link"           # payload: dict {mode, port, connected, method}
