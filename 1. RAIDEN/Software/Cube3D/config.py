import os

BASE_DIR = os.path.dirname(__file__)

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR   = os.path.join(BASE_DIR, "data")

LOGO_PATH       = os.path.join(ASSETS_DIR, "logo_semfundo.png")
CUBE_STATE_PATH = os.path.join(DATA_DIR, "cube_state.json")

RES = (1400, 750)

COLOR_MAP = {
    'U': (1.0, 1.0, 1.0),
    'D': (1.0, 1.0, 0.0),
    'F': (0.0, 1.0, 0.0),
    'B': (0.0, 0.0, 1.0),
    'L': (1.0, 0.5, 0.0),
    'R': (1.0, 0.0, 0.0),
    '.': (0.2, 0.2, 0.2),
}

# Mapeamento inverso: cor RGB → char de face.
# Usa arredondamento para evitar problemas de ponto flutuante.
def _build_rgb_to_char():
    result = {}
    for char, rgb in COLOR_MAP.items():
        key = tuple(round(v, 6) for v in rgb)
        result[key] = char
    return result

RGB_TO_CHAR = _build_rgb_to_char()

def color_to_char(rgb_tuple):
    """Converte uma tupla RGB para o char de face correspondente."""
    key = tuple(round(v, 6) for v in rgb_tuple)
    return RGB_TO_CHAR.get(key, 'U')

# Tabela de movimentos Kociemba → código serial do robô
MOVE_TABLE = {
    "U1": "A", "U3": "B", "U2": "C",
    "R1": "D", "R3": "E", "R2": "F",
    "F1": "G", "F3": "H", "F2": "I",
    "D1": "J", "D3": "K", "D2": "L",
    "L1": "M", "L3": "N", "L2": "O",
    "B1": "P", "B3": "Q", "B2": "R",
}

# Ordem de leitura das faces para get_state_string / load_from_json
FACE_SCAN_ORDER = [
    # (face_key, axis_index, layer_value, iter_axes)
    # Cada entrada: face, lista de (x,y,z) na ordem de leitura
    # Definida diretamente nas funções que a usam — ver cube/rubiks_cube.py
]
