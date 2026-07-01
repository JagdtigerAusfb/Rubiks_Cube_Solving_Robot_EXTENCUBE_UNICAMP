"""Shared utilities used by every solver module."""

from config import MOVE_TABLE

_INVERSE_MAP = {
    "U": "U'", "U'": "U", "U2": "U2",
    "R": "R'", "R'": "R", "R2": "R2",
    "F": "F'", "F'": "F", "F2": "F2",
    "L": "L'", "L'": "L", "L2": "L2",
    "B": "B'", "B'": "B", "B2": "B2",
    "D": "D'", "D'": "D", "D2": "D2",
}


def count_moves(solution: str) -> int:
    """Returns the number of moves in a space-separated solution string."""
    return len(solution.strip().split()) if solution.strip() else 0


def invert_moves(sequence: str) -> str:
    """Returns the inverse of a move sequence (reversed order, each move inverted)."""
    moves = sequence.split()
    return " ".join(_INVERSE_MAP[m] for m in reversed(moves))


def to_robot_sequence(solution: str) -> str:
    """Converts a Kociemba solution string to the robot's serial character sequence."""
    return "".join(MOVE_TABLE[m] for m in solution.split() if m in MOVE_TABLE)


def build_result(solution: str) -> dict:
    """Packages a solution string into the standard result dict used by all solvers."""
    inverted = invert_moves(solution)
    return {
        "solution":          solution,
        "move_count":        count_moves(solution),
        "robot_sequence":    to_robot_sequence(solution),
        "inverted_sequence": to_robot_sequence(inverted),
    }
