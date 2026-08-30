"""Testa o SensorFlow com um link falso — sem serial, sem hardware.
Roda de dentro de host/:  python test_sensor_flow.py
"""
from sensor.main_sensor import SensorFlow
from app.communication.embedded import (
    CalibrationPremiseError, SenseIncompleteError,
)

class FakeLink:
    """Link dublê: você programa o que cada método devolve ou levanta."""
    def __init__(self, scan=None, calibrate=None, sense=None):
        self._scan, self._calibrate, self._sense = scan, calibrate, sense
    def _resolve(self, v):
        if isinstance(v, Exception):      # programado pra falhar
            raise v
        return v
    def scan(self):      return self._resolve(self._scan)
    def calibrate(self): return self._resolve(self._calibrate)
    def sense(self):     return self._resolve(self._sense)


CAL_OK = {'hue':{}, 'sat':{}, 'white_sat_thresh':0.355,
          'white_balance':{'r':18.0,'g':18.0,'b':7.0}}
STATE_OK = [list("WWWWWWWW"),list("RRRRRRRR"),list("GGGGGGGG"),
            list("YYYYYYYY"),list("OOOOOOOO"),list("BBBBBBBB")]

# 1) Caminho feliz: prepare() encadeia scan->calibrate e devolve a calibração
f = SensorFlow(FakeLink(scan=[True]*12, calibrate=CAL_OK))
r = f.prepare()
assert r.ok and r.step == "calibrate", r
assert f.calibrated is True
print(f"[ok] prepare feliz -> parou em '{r.step}', ok={r.ok}")

# 2) Scan falho: prepare() PARA no scan, NÃO chama calibrate
f = SensorFlow(FakeLink(scan=[True]*5 + [False] + [True]*6))
r = f.prepare()
assert not r.ok and r.step == "scan", r
assert f.calibrated is False                 # nunca calibrou
print(f"[ok] prepare com sensor mudo -> parou em '{r.step}': {r.message}")

# 3) Calibração viola premissa (e5): etapa isolada mapeia p/ StepResult
f = SensorFlow(FakeLink(scan=[True]*12,
                        calibrate=CalibrationPremiseError("e5")))
r = f.calibrate()
assert not r.ok and r.error == 5, r
print(f"[ok] calibrate e5 -> error={r.error}: {r.message}")

# 4) Momento 2 feliz: read_for_solution -> scan->sense, entrega matriz
f = SensorFlow(FakeLink(scan=[True]*12, sense=STATE_OK))
r = f.read_for_solution()
assert r.ok and r.step == "sense" and r.data[0] == list("WWWWWWWW"), r
print(f"[ok] read_for_solution feliz -> estado {len(r.data)}x{len(r.data[0])}")

# 5) Sense incompleto (e6): read_for_solution para no sense
f = SensorFlow(FakeLink(scan=[True]*12, sense=SenseIncompleteError("e6")))
r = f.read_for_solution()
assert not r.ok and r.error == 6, r
print(f"[ok] read_for_solution e6 -> error={r.error}")

print("\n[SUCESSO] lógica do SensorFlow validada sem hardware.")