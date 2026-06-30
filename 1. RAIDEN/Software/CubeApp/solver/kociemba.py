"""Kociemba two-phase solver wrapper."""

import json
import logging

import kociemba

from solver.utils import build_result

logger = logging.getLogger(__name__)


def solve_from_file(json_path: str) -> dict:
    """Loads cube state from *json_path* and returns a result dict.

    Returns a dict with keys ``solution``, ``move_count``, ``robot_sequence``,
    and ``inverted_sequence`` on success, or ``{"error": <message>}`` on failure.
    """
    try:
        with open(json_path) as f:
            state = json.load(f)["cube_string"]

        logger.info("Solving with Kociemba — state: %s", state)
        solution = kociemba.solve(state)
        logger.info("Kociemba solution (%d moves): %s", len(solution.split()), solution)
        return build_result(solution)

    except FileNotFoundError:
        logger.warning("Cube state file not found: %s", json_path)
        return {"error": "Cube state file not found. Capture the cube first."}
    except Exception as exc:
        logger.exception("Kociemba solver failed")
        return {"error": str(exc)}
