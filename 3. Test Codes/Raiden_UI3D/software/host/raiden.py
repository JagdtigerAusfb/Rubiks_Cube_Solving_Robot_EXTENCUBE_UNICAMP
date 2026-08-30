"""Ponto de entrada do sistema Raiden.
Rode de dentro de host/:

    python raiden.py                  # GUI 3D (padrão)
    python raiden.py --mode demo      # GUI sem hardware (serial simulada)
    python raiden.py --port COM5      # força a porta
    python raiden.py --terminal       # menu de terminal antigo (main_raiden)

A GUI e o terminal são duas peles do MESMO sistema: ambos compõem os
mesmos flows (sensor/solver/execution) através da classe Raiden.
"""

import argparse
import logging

from app.main_raiden import Mode


def _parse():
    p = argparse.ArgumentParser(description="Raiden — solucionador de cubo mágico")
    p.add_argument("--terminal", action="store_true",
                   help="usa o menu de terminal em vez da GUI 3D")
    p.add_argument("--mode", choices=[Mode.DEMO, Mode.UNO_DUMMY, Mode.REAL],
                   default=Mode.REAL,
                   help="modo de operação da GUI (padrão: real, cai para demo "
                        "se não achar a placa)")
    p.add_argument("--port", default=None, help="porta serial (ex.: COM5, /dev/ttyACM0)")
    p.add_argument("--method", choices=["kociemba", "m2op"], default="kociemba",
                   help="método do solver")
    p.add_argument("-v", "--verbose", action="store_true", help="logging em DEBUG")
    return p.parse_args()


def main():
    args = _parse()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.terminal:
        from app.main_raiden import main as terminal_main
        terminal_main()
        return

    from app.ui_ux.main_ui import run
    run(mode=args.mode, port=args.port, method=args.method)


if __name__ == "__main__":
    main()
