"""Comunicação para fora, com a UI/UX — o adapter mundo interno <-> tela.

Traduz nas DUAS direções, e é o único lugar que sabe as duas linguagens:

    interno                                   UI (cubo 3D)
    -------                                   ------------
    matriz 6x8 (URFDLB, horário)      ->      54 facelets row-major
    solução "R U2 F'"                 ->      [(face, voltas), ...]
    chars A-R do robô                 ->      [(face, voltas), ...]
    (face, voltas) de um giro manual  ->      char A-R para a serial

Nada de tabela nova aqui: MOVE_TABLE e o adapter de estado vêm de
solver/base.py, que é a fonte única do host. Este módulo só reexporta e
inverte, para a GUI não precisar importar o subsistema solver.
"""

from solver.base import MOVE_TABLE, state_to_cube_string

# ----------------------------------------------------------------------
# Estado do cubo
# ----------------------------------------------------------------------
FACE_ORDER = "URFDLB"                      # ordem de contrato (cube_state.md)
SOLVED_FACELETS = "".join(f * 9 for f in FACE_ORDER)

# Posição horária (0..7) -> índice row-major 3x3. Espelha solver/base.py:
#   nossa ordem:  0 1 2 / 7 . 3 / 6 5 4      row-major: 0 1 2 / 3 4 5 / 6 7 8
CW_TO_ROWMAJOR = [0, 1, 2, 5, 8, 7, 6, 3]


def state_to_facelets(state) -> str:
    """Matriz 6x8 sensoriada -> string de 54 facelets que a UI 3D consome."""
    return state_to_cube_string(state)


def sense_reveal_order():
    """Ordem em que a UI 'revela' os adesivos, imitando o sensoriamento.

    Devolve [(face_idx, rowmajor_idx), ...]: para cada face na ordem de
    contrato, primeiro o centro (fixo, não sensoriado) e depois as 8
    posições no sentido horário a partir do topo-esquerdo.
    """
    order = []
    for f in range(6):
        order.append((f, 4))                       # centro fixo
        for pos in range(8):
            order.append((f, CW_TO_ROWMAJOR[pos]))
    return order


# ----------------------------------------------------------------------
# Movimentos
# ----------------------------------------------------------------------
# char serial -> notação de cubo (inverso de MOVE_TABLE, sem duplicar tabela)
CHAR_TO_MOVE = {char: move for move, char in MOVE_TABLE.items()}

# Convenção da animação 3D: 1 = 90° horário, 2 = 180°, 3 = 90° anti-horário.
_SUFFIX_TO_TURNS = {"": 1, "2": 2, "'": 3}
_TURNS_TO_SUFFIX = {1: "", 2: "2", 3: "'"}


def move_to_visual(move: str):
    """'R2' -> ('R', 2) | \"U'\" -> ('U', 3) | 'F' -> ('F', 1)."""
    return move[0], _SUFFIX_TO_TURNS[move[1:]]


def visual_to_move(face: str, turns: int) -> str:
    """('U', 3) -> \"U'\" — notação de cubo a partir do giro visual."""
    return f"{face}{_TURNS_TO_SUFFIX[turns]}"


def visual_to_char(face: str, turns: int):
    """('U', 3) -> 'B' — char serial de um giro manual feito na UI."""
    return MOVE_TABLE.get(visual_to_move(face, turns))


def solution_to_visual(solution: str):
    """'R U2 F\\'' -> [('R',1), ('U',2), ('F',3)] para animar no cubo 3D."""
    return [move_to_visual(m) for m in solution.split() if m and m[0] in "URFDLB"]


def robot_sequence_to_visual(sequence: str):
    """'DFG...' (chars A-R) -> [(face, voltas), ...] na mesma ordem.

    Ignora chars fora do alfabeto (o host já valida antes de enviar).
    """
    out = []
    for ch in sequence.upper():
        move = CHAR_TO_MOVE.get(ch)
        if move:
            out.append(move_to_visual(move))
    return out
