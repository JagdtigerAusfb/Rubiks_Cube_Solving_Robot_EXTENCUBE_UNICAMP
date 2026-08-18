"""Testa ExecFlow sem hardware, com link falso.
Roda de dentro de host/:  python test_exec.py
"""
from execution.main_exec import ExecFlow
from app.communication.embedded import InvalidMoveError


class FakeLink:
    """Link dublê: registra a sequência enviada e devolve um tempo fake."""
    def __init__(self):
        self.sent = None
    def move(self, seq):
        if not seq or any(c < 'A' or c > 'R' for c in seq):
            raise InvalidMoveError("e1")
        self.sent = seq
        return len(seq) * 0.05            # tempo fake proporcional
    def set_speed(self, us): return 0.0
    def set_gap(self, ms): return 0.0


# 1) sequência inteira enviada num envio só
fk = FakeLink(); ex = ExecFlow(fk)
r = ex.execute_sequence("KNIADBE")
assert r.ok and fk.sent == "KNIADBE", (r, fk.sent)
assert abs(r.data - 7 * 0.05) < 1e-9, r.data
print(f"[ok] sequência inteira enviada de uma vez: {fk.sent!r} ({r.data:.2f}s)")

# 2) sequência vazia -> sucesso trivial, nada enviado
fk2 = FakeLink()
r = ExecFlow(fk2).execute_sequence("")
assert r.ok and fk2.sent is None, r
print("[ok] sequência vazia tratada")

# 3) char inválido -> barrado (InvalidMoveError vira StepResult, não exceção)
fk3 = FakeLink()
r = ExecFlow(fk3).execute_sequence("ADZ")     # 'Z' fora de A–R
assert not r.ok and r.error == 1, r
print(f"[ok] sequência inválida barrada: {r.message}")

# 4) config de velocidade/gap
fk4 = FakeLink(); ex4 = ExecFlow(fk4)
assert ex4.set_speed(850).ok and ex4.set_gap(10).ok
print("[ok] set_speed / set_gap")

print("\n[SUCESSO] lógica do ExecFlow validada sem hardware.")