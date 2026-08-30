"""Kociemba two-phase solver — wrapper (conteúdo preservado)."""

import logging

import kociemba                                   # biblioteca externa (pip)

from solver.base import Solver, build_result

logger = logging.getLogger(__name__)


class KociembaSolver(Solver):
    """Método de produção (~20 movimentos)."""

    name = "kociemba"

    def solve(self, cube_string: str) -> dict:
        try:
            logger.info("Solving with Kociemba — state: %s", cube_string)
            solution = kociemba.solve(cube_string)      # <-- núcleo intocado
            logger.info("Kociemba solution (%d moves): %s",
                        len(solution.split()), solution)
            return build_result(solution)
        except Exception as exc:
            logger.exception("Kociemba solver failed")
            return {"error": str(exc)}