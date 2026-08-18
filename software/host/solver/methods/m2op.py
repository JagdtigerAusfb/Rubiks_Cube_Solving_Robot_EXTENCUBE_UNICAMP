"""M2/OP blind-solving method — wrapper (algoritmo preservado)."""

import logging

from solver.base import Solver, build_result, count_moves, to_robot_sequence, invert_moves

logger = logging.getLogger(__name__)


class M2OPSolver(Solver):
    """Método de autoria (~200 movimentos)."""

    name = "m2op"

    def solve(self, cube_string: str) -> dict:
        try:
            logger.info("Solving with M2/OP — state: %s", cube_string)
            result = _solver_m2op(cube_string)          # <-- núcleo intocado
            logger.info("M2/OP solution (%s moves): %s",
                        result.get("move_count"), result.get("solution"))
            return result
        except Exception as exc:
            logger.exception("M2/OP solver failed")
            return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Core M2/OP algorithm — logic preserved exactly from the original
# ---------------------------------------------------------------------------

def _solver_m2op(state: str) -> dict:
    # Validate cube string
    for face in "URFDLB":
        if state.count(face) != 9:
            return {"error": "Error. Probably cubestring is invalid"}

    # ------------------------------------------------------------------
    # EDGE reading
    # ------------------------------------------------------------------

    def certas_flips_edges(edges_list, map_edges_list):
        counter = 11
        flips   = []
        certas  = []

        checks = [
            (0,  "UB"), (2,  "UR"), (4,  "UF"), (6,  "UL"),
            (8,  "LF"), (10, "LD"), (12, "LB"), (14, "FR"),
            (18, "RB"), (20, "RD"), (22, "BD"),
        ]
        # DF/FD increments counter instead of decrementing
        df_check = (16, "DF")

        def _test(idx, label):
            i0, i1 = map_edges_list[idx][1]
            found = edges_list[i0] + edges_list[i1]
            if found == label:
                counter_delta = 1 if label == "DF" else -1
                certas.extend([label, label[::-1]])
                return counter_delta, None
            if found == label[::-1]:
                counter_delta = 1 if label == "DF" else -1
                flips.append(label)
                return counter_delta, None
            return 0, None

        nonlocal_counter = [counter]
        for idx, label in checks + [df_check]:
            i0, i1 = map_edges_list[idx][1]
            found = edges_list[i0] + edges_list[i1]
            sign = 1 if label == "DF" else -1
            if found == label:
                nonlocal_counter[0] += sign
                certas.extend([label, label[::-1]])
            elif found == label[::-1]:
                nonlocal_counter[0] += sign
                flips.append(label)

        return certas, flips, nonlocal_counter[0]

    def test_buffer_1(piece, certas, flips, solved_edges_list):
        flips_true = [f for pair in flips for f in (pair, pair[::-1])]
        inc = -2
        while True:
            inc += 2
            if (piece in certas) or (piece in flips_true):
                piece = solved_edges_list[inc][0]
            else:
                return piece

    def adicionar_flips_1(flips, solved_edges_list, hist_edges):
        for piece in flips:
            for j in range(len(solved_edges_list)):
                if solved_edges_list[j][0] == piece or solved_edges_list[j][0] == piece[::-1]:
                    hist_edges += solved_edges_list[j][1]
        return hist_edges

    # Edge positions in the state string
    edge_indices = [1, 3, 5, 7, 10, 12, 14, 16, 19, 21, 23, 25, 28, 30, 32, 34, 37, 39, 41, 43, 46, 48, 50, 52]
    edges_list = [state[i] for i in edge_indices]

    solved_edges_list = [
        ['UB', 'A'], ['UR', 'B'], ['UF', 'C'], ['UL', 'D'],
        ['LU', 'E'], ['LF', 'F'], ['LD', 'G'], ['LB', 'H'],
        ['FU', 'I'], ['FR', 'J'], ['FD', 'K'], ['FL', 'L'],
        ['RU', 'M'], ['RB', 'N'], ['RD', 'O'], ['RF', 'P'],
        ['BU', 'Q'], ['BL', 'R'], ['BD', 'S'], ['BR', 'T'],
        ['DF', 'U'], ['DR', 'V'], ['DB', 'W'], ['DL', 'X'],
    ]

    map_edges_list = [
        ['UB', (0, 20)], ['BU', (20, 0)], ['UR', (2, 4)],  ['RU', (4, 2)],
        ['UF', (3, 8)],  ['FU', (8, 3)],  ['UL', (1, 16)], ['LU', (16, 1)],
        ['LF', (18, 9)], ['FL', (9, 18)], ['LD', (19, 13)],['DL', (13, 19)],
        ['LB', (17, 22)],['BL', (22, 17)],['FR', (10, 5)], ['RF', (5, 10)],
        ['DF', (12, 11)],['FD', (11, 12)],['RB', (6, 21)], ['BR', (21, 6)],
        ['RD', (7, 14)], ['DR', (14, 7)], ['BD', (23, 15)],['DB', (15, 23)],
    ]

    certas, flips, counter = certas_flips_edges(edges_list, map_edges_list)

    if len(certas) == 24:
        hist_edges = []
    else:
        ciclos   = 0
        continuar = True
        hist_edges = []
        buffer   = "DF"
        buffer   = test_buffer_1(buffer, certas, flips, solved_edges_list)
        certas.extend(["DF", "FD"])
        target   = ""

        while counter > 0:
            if buffer not in ("DF", "FD"):
                for j in range(len(solved_edges_list)):
                    if solved_edges_list[j][0] == buffer:
                        hist_edges += solved_edges_list[j][1]
                        counter -= 1
                        break

            for k in range(len(map_edges_list)):
                if map_edges_list[k][0] == buffer:
                    target    = edges_list[map_edges_list[k][1][0]] + edges_list[map_edges_list[k][1][1]]
                    continuar = True
                    break

            while continuar and counter > 0:
                for j in range(len(solved_edges_list)):
                    if solved_edges_list[j][0] == target:
                        hist_edges += solved_edges_list[j][1]
                        counter -= 1
                        break

                if counter != 0:
                    for k in range(len(map_edges_list)):
                        if map_edges_list[k][0] == target:
                            certas.append(target)
                            certas.append(target[::-1])
                            target = edges_list[map_edges_list[k][1][0]] + edges_list[map_edges_list[k][1][1]]
                            break

                    if target not in certas:
                        continuar = True
                    else:
                        continuar = False
                        ciclos   += 1
                        counter  += 1
                        buffer    = test_buffer_1(target, certas, flips, map_edges_list)

        flips = [item for item in flips if item not in {"FD", "DF"}]
        hist_edges = adicionar_flips_1(flips, solved_edges_list, hist_edges)

    # Parity
    if len(hist_edges) % 2 != 0:
        hist_edges.append("PARIDADE")
    else:
        hist_edges.append("NO PARIDADE")

    # ------------------------------------------------------------------
    # CORNER reading
    # ------------------------------------------------------------------

    def certas_flips_corners(corners_list, map_corners_list):
        counter  = 7
        flips_h  = []
        flips_ah = []
        certas   = []

        corner_checks = [
            (0,  "ULB", +1), (3,  "UBR", -1), (6,  "URF", -1),
            (9,  "UFL", -1), (12, "DLF", -1), (15, "DFR", -1),
            (18, "DRB", -1), (21, "DBL", -1),
        ]

        for idx, label, sign in corner_checks:
            i0, i1, i2 = map_corners_list[idx][1]
            found = corners_list[i0] + corners_list[i1] + corners_list[i2]
            rot_ah = label[2] + label[0] + label[1]   # anti-horário
            rot_h  = label[1] + label[2] + label[0]   # horário
            if found == label:
                counter += sign
                certas.extend([label, rot_ah, rot_h])
            elif found == rot_ah:
                counter += sign
                flips_ah.append(rot_ah)
            elif found == rot_h:
                counter += sign
                flips_h.append(rot_h)

        return certas, flips_ah, flips_h, counter

    def rotacoes_horarias(piece):
        return [piece[i:] + piece[:i] for i in range(len(piece))]

    def test_buffer_2(piece, certas, flips_ah, flips_h, solved_corners_list):
        rotacoes_ah = [rot for p in flips_ah for rot in rotacoes_horarias(p)]
        rotacoes_h  = [rot for p in flips_h  for rot in rotacoes_horarias(p)]
        inc = -3
        while True:
            inc += 3
            if piece in (certas + rotacoes_ah + rotacoes_h):
                piece = solved_corners_list[inc][0]
            else:
                return piece

    def adicionar_flips_2(flips_ah, flips_h, solved_corners_list, hist_corners):
        def rot_ah(p): return p[2] + p[0] + p[1]
        def rot_h(p):  return p[1] + p[2] + p[0]

        for piece in flips_ah:
            for nome, alg in solved_corners_list:
                if nome == piece:
                    hist_corners += alg
                if nome == rot_ah(piece):
                    hist_corners += alg

        for piece in flips_h:
            for nome, alg in solved_corners_list:
                if nome == piece:
                    hist_corners += alg
            for nome, alg in solved_corners_list:
                if nome == rot_h(piece):
                    hist_corners += alg

        return hist_corners

    corner_indices = [0,2,6,8,9,11,15,17,18,20,24,26,27,29,33,35,36,38,42,44,45,47,51,53]
    corners_list = [state[i] for i in corner_indices]

    solved_corners_list = [
        ['ULB','A'],['UBR','B'],['URF','C'],['UFL','D'],
        ['LBU','E'],['LUF','F'],['LFD','G'],['LDB','H'],
        ['FLU','I'],['FUR','J'],['FRD','K'],['FDL','L'],
        ['RFU','M'],['RUB','N'],['RBD','O'],['RDF','P'],
        ['BRU','Q'],['BUL','R'],['BLD','S'],['BDR','T'],
        ['DLF','U'],['DFR','V'],['DRB','W'],['DBL','X'],
    ]

    map_corners_list = [
        ['ULB',(0,16,21)], ['LBU',(16,21,0)], ['BUL',(21,0,16)],
        ['UBR',(1,20,5)],  ['RUB',(5,1,20)],  ['BRU',(20,5,1)],
        ['URF',(3,4,9)],   ['FUR',(9,3,4)],   ['RFU',(4,9,3)],
        ['UFL',(2,8,17)],  ['FLU',(8,17,2)],  ['LUF',(17,2,8)],
        ['DLF',(12,19,10)],['FDL',(10,12,19)],['LFD',(19,10,12)],
        ['DFR',(13,11,6)], ['FRD',(11,6,13)], ['RDF',(6,13,11)],
        ['DRB',(15,7,22)], ['BDR',(22,15,7)], ['RBD',(7,22,15)],
        ['DBL',(14,23,18)],['BLD',(23,18,14)],['LDB',(18,14,23)],
    ]

    certas, flips_ah, flips_h, counter = certas_flips_corners(corners_list, map_corners_list)

    if len(certas) == 24:
        hist_corners = []
    else:
        ciclos    = 0
        continuar = True
        hist_corners = []
        buffer    = "ULB"
        buffer    = test_buffer_2(buffer, certas, flips_ah, flips_h, map_corners_list)
        certas.extend(["ULB", "LBU", "BUL"])
        target    = ""

        while counter > 0:
            if buffer not in ("ULB", "LBU", "BUL"):
                for j in range(len(solved_corners_list)):
                    if solved_corners_list[j][0] == buffer:
                        hist_corners += solved_corners_list[j][1]
                        counter -= 1
                        break

            for k in range(len(map_corners_list)):
                if map_corners_list[k][0] == buffer:
                    target = (corners_list[map_corners_list[k][1][0]]
                             + corners_list[map_corners_list[k][1][1]]
                             + corners_list[map_corners_list[k][1][2]])
                    continuar = True
                    break

            while continuar and counter > 0:
                for j in range(len(solved_corners_list)):
                    if solved_corners_list[j][0] == target:
                        hist_corners += solved_corners_list[j][1]
                        counter -= 1
                        break

                if counter != 0:
                    for k in range(len(map_corners_list)):
                        if map_corners_list[k][0] == target:
                            certas.extend([
                                target[0]+target[1]+target[2],
                                target[2]+target[0]+target[1],
                                target[1]+target[2]+target[0],
                            ])
                            target = (corners_list[map_corners_list[k][1][0]]
                                     + corners_list[map_corners_list[k][1][1]]
                                     + corners_list[map_corners_list[k][1][2]])
                            break

                    if target not in certas:
                        continuar = True
                    else:
                        continuar = False
                        ciclos   += 1
                        counter  += 1
                        buffer    = test_buffer_2(target, certas, flips_ah, flips_h, map_corners_list)

        remove = {"ULB", "LBU", "BUL"}
        flips_h  = [x for x in flips_h  if x not in remove]
        flips_ah = [x for x in flips_ah if x not in remove]
        hist_corners = adicionar_flips_2(flips_ah, flips_h, solved_corners_list, hist_corners)

    # ------------------------------------------------------------------
    # Generate and simplify the final sequence
    # ------------------------------------------------------------------

    alg_Y       = "R U' R' U' R U R' F' R U R' U' R' F R"
    alg_paridade = "U' L2 U L2 R2 D' L2 D"

    M2_odd = {
        'A':"L2 R2",'B':"R' U R U' L2 R2 D R' D' R",'C':"U2 L R' F2 L R'",
        'D':"L U' L' U L2 R2 D' L D L'",'E':"B L' B' L2 R2 F L F'",'F':"B L2 B' L2 R2 F L2 F'",
        'G':"B L B' L2 R2 F L' F'",'H':"L' B L B' L2 R2 F L' F' L",
        'I':"D L R' F R2 F' L' R U R2 U' D' L2 R2",'J':"U R U' L2 R2 D R' D'",
        'L':"U' L' U L2 R2 D' L D",'M':"B' R B L2 R2 F' R' F",
        'N':"R B' R' B L2 R2 F' R F R'",'O':"B' R' B L2 R2 F' R F",
        'P':"B' R2 B L2 R2 F' R2 F",'Q':"B' R B U R2 U' L2 R2 D R2 D' F' R' F",
        'R':"U' L U L2 R2 D' L' D",'S':"L2 R2 U D R2 D' L R' B R2 B' L' R U'",
        'T':"U R' U' L2 R2 D R D'",'V':"U R2 U' L2 R2 D R2 D'",
        'W':"L' R B2 L' R D2",'X':"U' L2 U L2 R2 D' L2 D",
    }

    M2_even = {
        'A':"L2 R2",'B':"R' D R D' L2 R2 U R' U' R",'C':"L' R F2 L' R U2",
        'D':"L D' L' D L2 R2 U' L U L'",'E':"F L' F' L2 R2 B L B'",'F':"F L2 F' L2 R2 B L2 B'",
        'G':"F L F' L2 R2 B L' B'",'H':"L' F L F' L2 R2 B L' B' L",
        'I':"L2 R2 D U R2 U' L R' F R2 F' L' R D'",'J':"D R D' L2 R2 U R' U'",
        'L':"D' L' D L2 R2 U' L U",'M':"F' R F L2 R2 B' R' B",
        'N':"R F' R' F L2 R2 B' R B R'",'O':"F' R' F L2 R2 B' R B",
        'P':"F' R2 F L2 R2 B' R2 B",'Q':"F' R F D R2 D' L2 R2 U R2 U' B' R' B",
        'R':"D' L D L2 R2 U' L' U",'S':"U L R' B R2 B' L' R D R2 D' U' L2 R2",
        'T':"D R' D' L2 R2 U R U'",'V':"D R2 D' L2 R2 U R2 U'",
        'W':"D2 L R' B2 L R'",'X':"D' L2 D L2 R2 U' L2 U",
    }

    OP_table = {
        'B':"R D' Y D R'",'C':"F Y F'",'D':"F R' Y R F'",'F':"F2 Y F2",
        'G':"D2 R Y R' D2",'H':"D2 Y D2",'I':"F' D Y D' F",'J':"F2 D Y D' F2",
        'K':"F D Y D' F'",'L':"D Y D'",'M':"R' Y R",'N':"R2 Y R2",
        'O':"R Y R'",'P':"Y",'Q':"R' F Y F' R",'S':"D' R Y R' D",
        'T':"D' Y D",'U':"F' Y F",'V':"D' F' Y F D",'W':"D2 F' Y F D2",'X':"D F' Y F D'",
    }

    def _generate_solution(hist_edges, hist_corners):
        seq = []
        for i, letra in enumerate(hist_edges):
            if letra in ("PARIDADE", "NO PARIDADE"):
                continue
            seq.append(M2_even[letra] if (i + 1) % 2 == 0 else M2_odd[letra])

        if hist_edges and hist_edges[-1] == "PARIDADE":
            seq.append(alg_paridade)

        for letra in hist_corners:
            seq.append(OP_table[letra].replace("Y", alg_Y))

        return " ".join(seq)

    def _simplify(seq_str: str) -> str:
        moves = seq_str.split()
        groups = [{'R', 'L'}, {'U', 'D'}, {'F', 'B'}]

        def commute(a, b):
            return any(a in g and b in g for g in groups)

        def to_val(m):
            if len(m) == 1: return 1
            return -1 if m[1] == "'" else 2

        def from_val(base, val):
            val %= 4
            if val == 0: return None
            return base if val == 1 else base + "2" if val == 2 else base + "'"

        i = 0
        while i < len(moves):
            j = i + 1
            while j < len(moves):
                if moves[i][0] == moves[j][0]:
                    if all(commute(moves[k][0], moves[i][0]) for k in range(i + 1, j)):
                        novo = from_val(moves[i][0], to_val(moves[i]) + to_val(moves[j]))
                        moves.pop(j)
                        moves.pop(i)
                        if novo:
                            moves.insert(i, novo)
                        i = -1
                        break
                j += 1
            i += 1

        return " ".join(moves)

    hist = hist_edges + hist_corners
    raw_solution  = _generate_solution(hist_edges, hist_corners)
    final_solution = _simplify(raw_solution)
    return build_result(final_solution)
