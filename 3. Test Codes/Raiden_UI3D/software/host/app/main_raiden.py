"""Main dos mains — composition root e loop de operação do sistema Raiden.

Liga o sistema, instancia o link (conforme o modo) e os três flows, e opera
por um menu de terminal (while True). NÃO implementa regra de subsistema —
apenas compõe e sequencia os momentos.

Modos: DEMO (serial simulada em Python), UNO_DUMMY (Arduino Uno com o sketch
firmware_dummy) e REAL (robô acoplado). Uno dummy e real compartilham o
caminho serial (pyserial); só muda o que está fisicamente conectado.
"""

import os

from common import StepResult
from dummy_serial import FakeSerialPort
from app.communication import open_link, close_link, SerialConnectionError
from app.communication.embedded import SerialLink, ProtocolError
from sensor.main_sensor import SensorFlow
from solver.main_solver import SolverFlow, DEFAULT_METHOD
from execution.main_exec import ExecFlow


# ======================================================================
# Modos e construção do link
# ======================================================================
class Mode:
    DEMO = "demo"
    UNO_DUMMY = "uno_dummy"
    REAL = "real"


def _make_link(mode, port=None):
    if mode == Mode.DEMO:
        link = SerialLink(FakeSerialPort())
        link.wait_ready()                     # consome READY* do fake
        return link
    # UNO_DUMMY e REAL: mesmo caminho serial real (pyserial autodetecta).
    return open_link(port=port)


# ======================================================================
# Raiden — compõe os flows e encadeia os momentos
# ======================================================================
class Raiden:
    def __init__(self, mode, port=None, method=DEFAULT_METHOD):
        self.mode = mode
        self._link = _make_link(mode, port)
        self.sensor = SensorFlow(self._link)
        self.solver = SolverFlow(method)
        self.exec = ExecFlow(self._link)
        self._last_state = None
        self._last_solution = None
        self._last_solution_data = None

    # --- Momentos (fluxos) ---
    def prepare(self) -> StepResult:
        """Momento 1: scan -> calibração (cubo resolvido)."""
        return self.sensor.prepare()

    def solve_and_execute(self) -> StepResult:
        """Momento 2: sense -> solve -> execute (o 'botão solver')."""
        r = self.sensor.read_for_solution()          # scan -> sense
        if not r.ok:
            return r
        self._last_state = r.data
        s = self.solve(self._last_state)             # calcula
        if not s.ok:
            return s
        return self.execute(self._last_solution)     # executa

    # --- Etapas isoladas (passo-a-passo / tratar erro) ---
    def scan(self) -> StepResult:
        return self.sensor.scan()

    def calibrate(self) -> StepResult:
        return self.sensor.calibrate()

    def sense(self) -> StepResult:
        r = self.sensor.sense()
        if r.ok:
            self._last_state = r.data
        return r

    def solve(self, state=None) -> StepResult:
        st = state if state is not None else self._last_state
        if st is None:
            return StepResult(False, "solve",
                              message="Nenhum estado sensoriado. Sensorie antes.")
        result = self.solver.solve_state(st)
        if "error" in result:
            return StepResult(False, "solve",
                              message=f"Solver ({self.solver.method}): {result['error']}")
        self._last_solution = result["robot_sequence"]
        self._last_solution_data = result
        return StepResult(True, "solve", data=result,
                          message=f"Solução ({self.solver.method}): "
                                  f"{result['move_count']} movimentos.")

    def execute(self, seq=None) -> StepResult:
        s = seq if seq is not None else self._last_solution
        if not s:
            return StepResult(False, "execute",
                              message="Nenhuma solução para executar.")
        return self.exec.execute_sequence(s)

    # --- Config ---
    def set_method(self, name) -> StepResult:
        try:
            self.solver = SolverFlow(name)
        except ValueError as e:
            return StepResult(False, "method", message=str(e))
        return StepResult(True, "method", message=f"Método: {name}.")

    def set_speed(self, us) -> StepResult:
        return self.exec.set_speed(us)

    def set_gap(self, ms) -> StepResult:
        return self.exec.set_gap(ms)

    def close(self):
        if self.mode != Mode.DEMO:
            try:
                close_link()
            except Exception:
                pass


# ======================================================================
# Terminal — responsivo e colorido (ANSI, sem dependência externa)
# ======================================================================
class C:
    R = "\033[0m"; B = "\033[1m"; DIM = "\033[2m"
    CY = "\033[36m"; GR = "\033[32m"; RD = "\033[31m"; YL = "\033[33m"; MG = "\033[35m"

# Bloco colorido por cor de adesivo (256 cores).
_BG = {"W": 255, "R": 196, "G": 46, "Y": 226, "O": 208, "B": 21, "X": 240}
_CW_RM = [0, 1, 2, 5, 8, 7, 6, 3]                  # pos horária -> row-major
_FACE_COLOR = {0: "W", 1: "R", 2: "G", 3: "Y", 4: "O", 5: "B"}


def _sq(ch):
    return f"\033[48;5;{_BG.get(ch, 240)}m {ch} {C.R}"


def show_result(res):
    mark = f"{C.GR}✓{C.R}" if res.ok else f"{C.RD}✗{C.R}"
    print(f"  {mark} {res.message}")


def show_state(state):
    print(f"  {C.DIM}estado (URFDLB):{C.R}")
    for f, row in enumerate(state):
        grid = [None] * 9
        grid[4] = _FACE_COLOR[f]
        for pos in range(8):
            grid[_CW_RM[pos]] = row[pos]
        lab = "URFDLB"[f]
        print(f"   {C.B}{lab}{C.R} " + "".join(_sq(grid[i]) for i in range(0, 3)))
        print(f"     "               + "".join(_sq(grid[i]) for i in range(3, 6)))
        print(f"     "               + "".join(_sq(grid[i]) for i in range(6, 9)))


def show_solution(data):
    print(f"  {C.DIM}solução:{C.R} {data['solution']}")
    print(f"  {C.DIM}robot  :{C.R} {C.MG}{data['robot_sequence']}{C.R} "
          f"({data['move_count']} movs)")


def render_menu(rd):
    lbl = {Mode.DEMO: "DEMO", Mode.UNO_DUMMY: "UNO DUMMY", Mode.REAL: "REAL"}[rd.mode]
    col = {Mode.DEMO: C.YL, Mode.UNO_DUMMY: C.CY, Mode.REAL: C.GR}[rd.mode]
    print()
    print(f"{C.B}{C.CY}╔════════════════════════════════════════════════╗{C.R}")
    print(f"{C.B}{C.CY}║{C.R}  {C.B}RAIDEN{C.R} · Solucionador de Cubo Mágico"
          f"   {col}{lbl:>9}{C.R}  {C.B}{C.CY}║{C.R}")
    print(f"{C.B}{C.CY}╚════════════════════════════════════════════════╝{C.R}")
    print(f"  {C.DIM}solver:{C.R} {C.MG}{rd.solver.method}{C.R}")
    print(f"\n  {C.DIM}FLUXOS{C.R}")
    print(f"   {C.B}1{C.R}) Preparar          {C.DIM}scan + calibração{C.R}")
    print(f"   {C.B}2{C.R}) Resolver+executar {C.DIM}sense → solve → exec{C.R}")
    print(f"\n  {C.DIM}ETAPAS ISOLADAS{C.R}")
    print(f"   {C.B}3{C.R}) Scan       {C.B}4{C.R}) Calibrar   {C.B}5{C.R}) Sensoriar")
    print(f"   {C.B}6{C.R}) Resolver   {C.B}7{C.R}) Executar sequência…")
    print(f"\n  {C.DIM}CONFIG{C.R}")
    print(f"   {C.B}8{C.R}) Método (kociemba/m2op)   {C.B}9{C.R}) Velocidade/gap")
    print(f"\n   {C.B}0{C.R}) Sair")


def dispatch(rd, choice):
    if choice == "1":
        show_result(rd.prepare())
    elif choice == "2":
        r = rd.solve_and_execute()
        if r.ok and rd._last_solution_data:
            show_solution(rd._last_solution_data)
        show_result(r)
    elif choice == "3":
        show_result(rd.scan())
    elif choice == "4":
        show_result(rd.calibrate())
    elif choice == "5":
        r = rd.sense(); show_result(r)
        if r.ok:
            show_state(r.data)
    elif choice == "6":
        r = rd.solve(); show_result(r)
        if r.ok:
            show_solution(r.data)
    elif choice == "7":
        seq = input(f"  sequência (chars A–R): ").strip().upper()
        show_result(rd.execute(seq))
    elif choice == "8":
        m = input(f"  método [kociemba/m2op]: ").strip().lower()
        show_result(rd.set_method(m))
    elif choice == "9":
        v = input(f"  velocidade µs/passo (enter p/ pular): ").strip()
        if v:
            show_result(rd.set_speed(int(v)))
        g = input(f"  gap ms entre movimentos (enter p/ pular): ").strip()
        if g:
            show_result(rd.set_gap(int(g)))
    else:
        print(f"  {C.YL}opção inválida.{C.R}")


def choose_mode():
    print(f"\n{C.B}Modo de operação:{C.R}")
    print(f"   {C.B}1{C.R}) Demo        {C.DIM}sem hardware, serial simulada{C.R}")
    print(f"   {C.B}2{C.R}) Uno dummy   {C.DIM}Arduino Uno com firmware_dummy{C.R}")
    print(f"   {C.B}3{C.R}) Real        {C.DIM}robô acoplado{C.R}")
    m = input(f"  {C.CY}›{C.R} ").strip()
    return {"1": Mode.DEMO, "2": Mode.UNO_DUMMY, "3": Mode.REAL}.get(m, Mode.DEMO)


def main():
    if os.name == "nt":
        os.system("")                          # habilita ANSI no Windows 10+
    mode = choose_mode()
    try:
        rd = Raiden(mode)
    except SerialConnectionError as e:
        print(f"  {C.RD}✗ conexão:{C.R} {e}")
        print(f"  {C.YL}caindo para DEMO.{C.R}")
        rd = Raiden(Mode.DEMO)

    if rd.mode == Mode.REAL:
        print(f"  {C.RD}{C.B}ATENÇÃO:{C.R} modo REAL — os motores vão se mover.")

    while True:
        render_menu(rd)
        try:
            choice = input(f"\n  {C.CY}›{C.R} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  encerrando."); break
        if choice == "0":
            print("  até mais."); break
        try:
            dispatch(rd, choice)
        except ProtocolError as e:
            print(f"  {C.RD}✗ serial/conexão:{C.R} {e}")
        except Exception as e:
            print(f"  {C.RD}✗ inesperado:{C.R} {e}")
    rd.close()


if __name__ == "__main__":
    main()