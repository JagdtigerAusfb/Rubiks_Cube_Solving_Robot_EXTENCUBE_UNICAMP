"""Configurações e parâmetros da GUI — fonte única do visual e das medidas.

Nenhum número mágico espalhado pelo hud/main_ui: cor, fonte, espaçamento,
tempo de animação e teclas moram aqui.

Princípio de cor: as 6 cores do cubo são reservadas EXCLUSIVAMENTE para
dado do cubo (adesivos e gizmo de eixos). Todo o restante do painel usa a
paleta neutra + um único acento violeta.
"""

import os

# ----------------------------------------------------------------------
# Caminhos
# ----------------------------------------------------------------------
UI_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(UI_DIR, "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo_semfundo.png")

# ----------------------------------------------------------------------
# Janela
# ----------------------------------------------------------------------
WINDOW_TITLE = "RAIDEN · Robô Solucionador de Cubo Mágico"
RES = (1460, 880)
MIN_RES = (1080, 700)
FPS = 60

# ----------------------------------------------------------------------
# Paleta (0-255; use gl() para converter para float do OpenGL)
# ----------------------------------------------------------------------
BG = (16, 17, 22)
SURFACE = (25, 27, 35)
SURFACE_ALT = (33, 36, 47)
SURFACE_HI = (44, 48, 62)
BORDER = (52, 57, 73)
TEXT = (232, 234, 242)
TEXT_DIM = (139, 146, 168)
TEXT_FAINT = (95, 101, 120)
ACCENT = (124, 108, 255)
ACCENT_DIM = (68, 60, 130)
OK = (74, 201, 132)
WARN = (238, 186, 74)
ERR = (233, 90, 95)
INFO = (86, 164, 240)

LEVEL_COLOR = {"ok": OK, "err": ERR, "warn": WARN, "info": INFO}


def gl(color, alpha=None):
    """(r,g,b) 0-255 -> tupla float 0-1 para o OpenGL."""
    r, g, b = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
    return (r, g, b) if alpha is None else (r, g, b, alpha)


# ----------------------------------------------------------------------
# Tipografia
# ----------------------------------------------------------------------
FONT_NAME = "consolas,dejavusansmono,menlo,couriernew,monospace"
FS_TITLE = 24
FS_BIG = 26
FS_BODY = 16
FS_SMALL = 14
FS_TINY = 12

# ----------------------------------------------------------------------
# Layout do painel lateral
# ----------------------------------------------------------------------
PANEL_W = 400          # largura da aba lateral
MARGIN = 14
PAD = 12               # respiro interno dos cards
GAP = 9                # espaço entre cards
RADIUS = 9
ROW_H = 30             # linha de comando / campo de config
FOOTER_H = 46          # barra de atalhos embaixo da cena 3D
LOG_MIN_LINES = 3
LOG_MAX_LINES = 40

# ----------------------------------------------------------------------
# Cena 3D
# ----------------------------------------------------------------------
CAM_START = (28.0, -34.0)      # (rot_x, rot_y) iniciais
CAM_DIST = -10.5               # translação em z
CAM_NEAR = 1.0                 # plano próximo: longe de 0 = profundidade precisa
CAM_FAR = 40.0
CUBIE_SIZE = 0.99        # corpo do cubie (0.99 = quase encostando no vizinho)
STICKER_SIZE = 0.84      # adesivo, embutido na face do corpo
STICKER_LIFT = 0.012     # folga do adesivo sobre o corpo (evita z-fighting)
DRAG_SENS = 0.4

# Cores dos adesivos por letra de face (dado do cubo — não usar na UI).
COLOR_MAP = {
    'U': (1.00, 1.00, 1.00),   # branca
    'R': (0.90, 0.12, 0.15),   # vermelha
    'F': (0.05, 0.75, 0.28),   # verde
    'D': (1.00, 0.85, 0.05),   # amarela
    'L': (1.00, 0.48, 0.05),   # laranja
    'B': (0.10, 0.32, 0.90),   # azul
    '.': (0.15, 0.16, 0.20),   # desconhecido / ainda não sensoriado
}
BODY_COLOR = (0.04, 0.04, 0.05)   # 'plástico' do cubie

# Animação
ANIM_DEG_PER_SEC = 460.0       # velocidade do giro no cubo 3D
REVEAL_STEP_S = 0.045          # intervalo entre adesivos no sensoriamento
REVEAL_FACE_PAUSE_S = 0.12     # respiro ao trocar de face
CAM_EASE = 5.0                 # suavização do reenquadramento automático

# Enquadramento automático por face durante o sensoriamento (rot_x, rot_y).
CAM_FACE_TARGET = {
    0: (74.0, -30.0),    # U
    1: (16.0, -74.0),    # R
    2: (16.0, -14.0),    # F
    3: (-74.0, -30.0),   # D
    4: (16.0, 74.0),     # L
    5: (16.0, 166.0),    # B
}

# ----------------------------------------------------------------------
# Defaults operacionais (espelham os do host)
# ----------------------------------------------------------------------
DEFAULT_SPEED_US = 850
DEFAULT_GAP_MS = 10
