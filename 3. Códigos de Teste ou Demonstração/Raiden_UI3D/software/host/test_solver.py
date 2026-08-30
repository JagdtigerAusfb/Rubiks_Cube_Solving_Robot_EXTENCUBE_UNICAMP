"""Valida o pipeline do solver com um estado default de scramble conhecido.

Estado gerado por: R U R' U' F2 L D  (a partir do resolvido, HOME branca/cima
verde/frente). O adapter converte a matriz 6x8 -> 54 facelets; Kociemba e M2OP
devolvem a solução. A solução do Kociemba deve ser o inverso do scramble.
Rode de dentro de host/:  python test_solver.py
"""
from solver.main_solver import SolverFlow
from solver.base import state_to_cube_string

# Estado sensoriado (matriz 6x8) após o scramble conhecido.
DEFAULT_STATE = [
    list("BWOGYYRB"),   # U
    list("ORWRGGRO"),   # R
    list("WGGGWBRW"),   # F
    list("YWGWWYYY"),   # D
    list("OOBOGBBO"),   # L
    list("BRYYRROB"),   # B
]

SCRAMBLE = "R U R' U' F2 L D"

def main():
    # 1) adapter: matriz -> facelet string de 54
    cube_string = state_to_cube_string(DEFAULT_STATE)
    print(f"[facelet] {cube_string}")
    assert len(cube_string) == 54, len(cube_string)
    assert all(cube_string.count(f) == 9 for f in "URFDLB"), "cada face deve ter 9"
    print("[ok] adapter gerou 54 facelets, 9 por face")

    # 2) Kociemba: deve resolver e ser coerente
    fk = SolverFlow("kociemba")
    rk = fk.solve_state(DEFAULT_STATE)
    assert "error" not in rk, rk
    print(f"\n[KOCIEMBA]")
    print(f"  solução      : {rk['solution']}   ({rk['move_count']} movs)")
    print(f"  robot_seq    : {rk['robot_sequence']}")
    print(f"  inverted_seq : {rk['inverted_sequence']}")

    # 3) M2OP: mesmo estado, método alternativo
    fm = SolverFlow("m2op")
    rm = fm.solve_state(DEFAULT_STATE)
    assert "error" not in rm, rm
    print(f"\n[M2OP]")
    print(f"  solução   : {rm['solution']}")
    print(f"  move_count: {rm['move_count']}")
    print(f"  robot_seq : {rm['robot_sequence']}")

    print(f"\n>>> Confira no alg.cubing.net: aplique o scramble '{SCRAMBLE}',")
    print(f">>> depois aplique a solução do Kociemba acima. O cubo deve resolver.")

if __name__ == "__main__":
    main()