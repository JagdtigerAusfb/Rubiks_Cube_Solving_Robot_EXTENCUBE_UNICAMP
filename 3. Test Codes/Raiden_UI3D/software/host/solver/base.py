"""Fundação compartilhada do subsistema solver.

Reúne o que ambos os métodos (kociemba, m2op) dependem, sem criar arquivos
novos: o espelho do move_alphabet (MOVE_TABLE), os utilitários de sequência
(antigo utils.py), o adapter matriz 6x8 -> cube_string de 54 facelets, e a
interface Strategy que main_solver usa para tratar os métodos como iguais.
"""

from abc import ABC, abstractmethod

# ---------------------------------------------------------------------------
# Espelho Python do move_alphabet.md (notação de cubo -> char serial A..R).
# Fonte única no host para a tradução; o firmware espelha em protocol.h.
# ---------------------------------------------------------------------------
# Ordem do contrato: U, D, L, R, F, B (NÃO é a ordem URFDLB do estado).
# Espelha 1:1 a LUT de firmware/src/motion/motion.cpp (índice = char - 'A').
MOVE_TABLE = {
    "U": "A", "U'": "B", "U2": "C",
    "D": "D", "D'": "E", "D2": "F",
    "L": "G", "L'": "H", "L2": "I",
    "R": "J", "R'": "K", "R2": "L",
    "F": "M", "F'": "N", "F2": "O",
    "B": "P", "B'": "Q", "B2": "R",
}

_INVERSE_MAP = {
    "U": "U'", "U'": "U", "U2": "U2",
    "R": "R'", "R'": "R", "R2": "R2",
    "F": "F'", "F'": "F", "F2": "F2",
    "L": "L'", "L'": "L", "L2": "L2",
    "B": "B'", "B'": "B", "B2": "B2",
    "D": "D'", "D'": "D", "D2": "D2",
}

# ---------------------------------------------------------------------------
# Utilitários de sequência (conteúdo preservado do antigo utils.py)
# ---------------------------------------------------------------------------
def count_moves(solution: str) -> int:
    """Número de movimentos numa solução separada por espaços."""
    return len(solution.strip().split()) if solution.strip() else 0


def invert_moves(sequence: str) -> str:
    """Inverso de uma sequência (ordem revertida, cada movimento invertido)."""
    moves = sequence.split()
    return " ".join(_INVERSE_MAP[m] for m in reversed(moves))


def to_robot_sequence(solution: str) -> str:
    """Converte a solução (notação de cubo) na sequência de chars A..R do robô."""
    return "".join(MOVE_TABLE[m] for m in solution.split() if m in MOVE_TABLE)


def build_result(solution: str) -> dict:
    """Empacota a solução no dict-padrão usado por todos os métodos."""
    inverted = invert_moves(solution)
    return {
        "solution":          solution,
        "move_count":        count_moves(solution),
        "robot_sequence":    to_robot_sequence(solution),
        "inverted_sequence": to_robot_sequence(inverted),
    }

# ---------------------------------------------------------------------------
# Adapter: matriz de estado 6x8 (do main_sensor) -> cube_string 54 facelets.
# ---------------------------------------------------------------------------
# Cor (cube_state.md) -> letra de face que o Kociemba/M2OP esperam.
# HOME: U=Branca R=Vermelha F=Verde D=Amarela L=Laranja B=Azul.
_COLOR_TO_FACE = {"W": "U", "R": "R", "G": "F", "Y": "D", "O": "L", "B": "B"}

# Posição horária (0..7) -> índice na grade row-major 3x3 (centro = 4).
#   nossa ordem:  0 1 2 / 7 . 3 / 6 5 4      row-major: 0 1 2 / 3 4 5 / 6 7 8
_CW_TO_ROWMAJOR = [0, 1, 2, 5, 8, 7, 6, 3]

# Ordem das faces = ordem da matriz = ordem do facelet string (URFDLB).
_FACE_LETTERS = "URFDLB"


def state_to_cube_string(state) -> str:
    """Converte a matriz 6x8 (state[face][pos], cores W/R/G/Y/O/B) na string de
    54 facelets em ordem URFDLB row-major, com os 6 centros fixos inseridos.

    Levanta ValueError se a matriz estiver malformada ou tiver cor inválida.
    """
    if len(state) != 6 or any(len(f) != 8 for f in state):
        raise ValueError("matriz de estado deve ser 6x8")

    faces = []
    for f in range(6):
        grid = [None] * 9
        grid[4] = _FACE_LETTERS[f]                 # centro fixo da face
        for pos in range(8):
            color = state[f][pos]
            if color not in _COLOR_TO_FACE:
                raise ValueError(f"cor inválida '{color}' em face {f} pos {pos}")
            grid[_CW_TO_ROWMAJOR[pos]] = _COLOR_TO_FACE[color]
        faces.append("".join(grid))
    return "".join(faces)

# ---------------------------------------------------------------------------
# Interface Strategy — Kociemba e M2OP a implementam; main_solver os trata igual.
# ---------------------------------------------------------------------------
class Solver(ABC):
    """Contrato comum dos métodos de solução."""

    name: str = "solver"

    @abstractmethod
    def solve(self, cube_string: str) -> dict:
        """Recebe a string de 54 facelets e devolve o dict-padrão (build_result)
        ou {"error": <msg>}."""
        raise NotImplementedError