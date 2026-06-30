import re

import pygame
from OpenGL.GL import (
    glBegin, glEnd, glVertex2f, glVertex3f, glColor3f, glColor4f,
    glEnable, glDisable, glLineWidth,
    glMatrixMode, glLoadIdentity, glPushMatrix, glPopMatrix,
    glTranslatef, glRotatef, glOrtho,
    glTexCoord2f, glBindTexture, glGenTextures, glTexImage2D, glTexParameteri,
    glGetDoublev, glGetIntegerv,
    glWindowPos2d, glDrawPixels,
    glBlendFunc,
    GL_QUADS, GL_LINES, GL_PROJECTION, GL_MODELVIEW,
    GL_DEPTH_TEST, GL_TEXTURE_2D, GL_BLEND,
    GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA,
    GL_RGBA, GL_UNSIGNED_BYTE,
    GL_LINEAR, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER,
    GL_MODELVIEW_MATRIX, GL_PROJECTION_MATRIX,
    GL_VIEWPORT,
)
from OpenGL.GLU import gluProject

from config import RES

# ------------------------------------------------------------------
# Cache de fontes — evita recriar a fonte a cada frame
# ------------------------------------------------------------------
_font_cache: dict = {}


def _get_font(size: int) -> pygame.font.Font:
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont('Consolas', size, bold=True)
    return _font_cache[size]


# ------------------------------------------------------------------
# Utilitários de texto
# ------------------------------------------------------------------

def draw_text_hud(x, y, text, size, center_x=None, center_y=None):
    font = _get_font(size)
    surface = font.render(text, True, (255, 255, 255, 255))
    tw, th = surface.get_size()
    render_x = x if center_x is None else center_x - (tw / 2)
    render_y = y if center_y is None else center_y - (th / 2)
    data = pygame.image.tostring(surface, "RGBA", True)
    glWindowPos2d(int(render_x), int(render_y))
    glDrawPixels(tw, th, GL_RGBA, GL_UNSIGNED_BYTE, data)


# ------------------------------------------------------------------
# Carregamento de logo
# ------------------------------------------------------------------

def load_logo(path: str):
    try:
        img = pygame.image.load(path)
        img = pygame.transform.flip(img, False, True)
        img_data = pygame.image.tostring(img, "RGBA", True)
        w, h = img.get_rect().size
        tex_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return tex_id, w, h
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Falha ao carregar logo: %s", e)
        return None, 0, 0


# ------------------------------------------------------------------
# HUD principal
# ------------------------------------------------------------------

def draw_hud(robot, logo_tex):
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, RES[0], RES[1], 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    # Logo
    if logo_tex[0]:
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, logo_tex[0])
        glColor3f(1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(20, 20)
        glTexCoord2f(1, 0); glVertex2f(240, 20)
        glTexCoord2f(1, 1); glVertex2f(240, 220)
        glTexCoord2f(0, 1); glVertex2f(20, 220)
        glEnd()
        glDisable(GL_TEXTURE_2D)

    # Painéis superiores
    box_w, box_h = 380, 70
    gap = 12
    margin_right = 20
    x_start = RES[0] - box_w - margin_right
    x_end   = RES[0] - margin_right
    center_x = (x_start + x_end) / 2

    def draw_panel(y_offset, color, label, value, is_solution=False):
        gl_y_bottom = y_offset + box_h
        glColor3f(*color)
        glBegin(GL_QUADS)
        glVertex2f(x_start, y_offset)
        glVertex2f(x_end,   y_offset)
        glVertex2f(x_end,   gl_y_bottom)
        glVertex2f(x_start, gl_y_bottom)
        glEnd()

        text_y_center = y_offset + (box_h / 2)

        if is_solution:
            sol_text = f"{label}: {value}" if value else f"{label}: --"
            lines = re.findall(r'.{1,35}(?:\s|$)', sol_text)[:3]
            start_y = text_y_center - ((len(lines) - 1) * 9)
            for i, line in enumerate(lines):
                line_y = start_y + (i * 18)
                draw_text_hud(0, 0, line.strip(), 16,
                              center_x=center_x,
                              center_y=RES[1] - line_y)
        else:
            draw_text_hud(0, 0, f"{label}: {value}", 22,
                          center_x=center_x,
                          center_y=RES[1] - text_y_center)

        return y_offset + box_h + gap

    y = 20
    sol_val = robot.last_solution if robot.last_solution else "--"
    y = draw_panel(y, (0.1, 0.2, 0.3), "SOLUTION", sol_val, is_solution=True)

    moves_val = robot.last_move_count if robot.last_move_count != "--" else "--"
    y = draw_panel(y, (0.2, 0.2, 0.3), "MOVES", moves_val)

    if robot.is_busy:
        t_color, t_val = (0.8, 0.2, 0.2), "BUSY..."
    elif not robot.ser:
        t_color, t_val = (0.4, 0.4, 0.4), "OFFLINE"
    else:
        t_color, t_val = (0.2, 0.5, 0.3), f"{robot.last_solve_time}s"

    draw_panel(y, t_color, "TIMER", t_val)

    # Painel inferior
    glColor4f(0, 0, 0, 0.6)
    glBegin(GL_QUADS)
    glVertex2f(0,       RES[1] - 60)
    glVertex2f(RES[0],  RES[1] - 60)
    glVertex2f(RES[0],  RES[1])
    glVertex2f(0,       RES[1])
    glEnd()

    p_s = robot.port if robot.ser else "DISCONNECTED"
    draw_text_hud(25, 35, f"PORT: {p_s} | SPEED: {robot.speed} | DELAY: {robot.delay}ms", 18)
    draw_text_hud(25, 10, "[S] Config  [X] Resolver  [R,L,U,D,F,B] Moves  [2] Double  [Shift] Inverse", 14)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)


# ------------------------------------------------------------------
# Indicador de eixos no canto
# ------------------------------------------------------------------

def draw_axes_corner(rot_x, rot_y):
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glTranslatef(-3.2, -1, -6.0)
    glRotatef(rot_x, 1, 0, 0)
    glRotatef(rot_y, 0, 1, 0)
    glDisable(GL_DEPTH_TEST)
    glLineWidth(3.0)

    s = 0.7
    glBegin(GL_LINES)
    glColor3f(1.0, 1.0, 1.0); glVertex3f(0, 0, 0); glVertex3f(0,  s,  0)  # U
    glColor3f(0.0, 1.0, 0.0); glVertex3f(0, 0, 0); glVertex3f(0,  0,  s)  # F
    glColor3f(1.0, 0.5, 0.0); glVertex3f(0, 0, 0); glVertex3f(-s, 0,  0)  # L
    glColor3f(1.0, 1.0, 0.0); glVertex3f(0, 0, 0); glVertex3f(0, -s,  0)  # D
    glColor3f(1.0, 0.0, 0.0); glVertex3f(0, 0, 0); glVertex3f(s,  0,  0)  # R
    glColor3f(0.0, 0.0, 1.0); glVertex3f(0, 0, 0); glVertex3f(0,  0, -s)  # B
    glEnd()
    glLineWidth(1.0)

    modelview  = glGetDoublev(GL_MODELVIEW_MATRIX)
    projection = glGetDoublev(GL_PROJECTION_MATRIX)
    viewport   = glGetIntegerv(GL_VIEWPORT)

    l_off = s + 0.1
    labels = [
        ("R (RIGHT)", ( l_off, 0,     0)),
        ("F (FRONT)", ( 0,     0,     l_off)),
        ("U (UP)",    ( 0,     l_off, 0)),
        ("L (LEFT)",  (-l_off, 0,     0)),
        ("D (DOWN)",  ( 0,    -l_off, 0)),
        ("B (BACK)",  ( 0,     0,    -l_off)),
    ]

    for label, pos in labels:
        try:
            win_x, win_y, win_z = gluProject(pos[0], pos[1], pos[2], modelview, projection, viewport)
            if 0.0 <= win_z <= 1.0:
                draw_text_hud(0, 0, label, 16, center_x=win_x, center_y=win_y)
        except Exception:
            pass

    glEnable(GL_DEPTH_TEST)
    glPopMatrix()
