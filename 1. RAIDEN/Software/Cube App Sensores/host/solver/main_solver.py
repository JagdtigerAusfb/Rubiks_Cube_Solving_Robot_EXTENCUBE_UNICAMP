"""Orquestra a busca da solução (regras do jogo do solver).

Recebe a matriz de estado 6x8 do main_sensor, converte para a string de 54
facelets (adapter em base), seleciona o método (Strategy) e devolve o
resultado. NÃO implementa algoritmo — apenas arquiteta os métodos.
"""

import logging

from solver.base import state_to_cube_string
from solver.methods.kociemba import KociembaSolver
from solver.methods.m2op import M2OPSolver

logger = logging.getLogger(__name__)

# Registro dos métodos disponíveis (intercambiáveis via nome).
_METHODS = {
    KociembaSolver.name: KociembaSolver,   # "kociemba"
    M2OPSolver.name:     M2OPSolver,       # "m2op"
}
DEFAULT_METHOD = "kociemba"


class SolverFlow:
    """Ponte entre o estado do sensor e os métodos de solução."""

    def __init__(self, method: str = DEFAULT_METHOD):
        if method not in _METHODS:
            raise ValueError(f"método desconhecido: {method!r} "
                             f"(disponíveis: {list(_METHODS)})")
        self._solver = _METHODS[method]()

    @property
    def method(self) -> str:
        return self._solver.name

    def solve_state(self, state) -> dict:
        """Matriz 6x8 -> dict de solução (ou {'error': ...})."""
        try:
            cube_string = state_to_cube_string(state)
        except ValueError as e:
            return {"error": f"estado inválido: {e}"}
        return self._solver.solve(cube_string)

    def solve_cube_string(self, cube_string: str) -> dict:
        """Atalho para quando já se tem a string de 54 facelets (teste/CLI)."""
        return self._solver.solve(cube_string)