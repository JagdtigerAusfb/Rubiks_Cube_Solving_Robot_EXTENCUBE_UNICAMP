"""Esqueleto/estrutura da GUI: containers e formatação.

Só desenha. Não decide nada, não chama o host: recebe o objeto de UI e
pinta o que ele diz. Todo número/cor vem de ui_ux/settings.py.

Sistema de coordenadas do HUD: origem no CANTO SUPERIOR ESQUERDO, y para
baixo (glOrtho invertido) — igual a qualquer editor de layout. A conversão
para as coordenadas de janela do OpenGL acontece só dentro de text().
"""

import math

import pygame
from OpenGL.GL import (
    glBegin, glEnd, glVertex2f, glVertex3f, glColor3f, glColor4f,
    glEnable, glDisable, glLineWidth, glViewport,
    glMatrixMode, glLoadIdentity, glPushMatrix, glPopMatrix,
    glTranslatef, glRotatef, glOrtho,
    glTexCoord2f, glBindTexture, glGenTextures, glTexImage2D, glTexParameteri,
    glGetDoublev, glGetIntegerv, glWindowPos2d, glDrawPixels, glBlendFunc,
    GL_QUADS, GL_LINES, GL_LINE_LOOP, GL_TRIANGLE_FAN,
    GL_PROJECTION, GL_MODELVIEW, GL_DEPTH_TEST, GL_TEXTURE_2D, GL_BLEND,
    GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_RGBA, GL_UNSIGNED_BYTE,
    GL_LINEAR, GL_TEXTURE_MIN_FILTER, GL_TEXTURE_MAG_FILTER,
    GL_MODELVIEW_MATRIX, GL_PROJECTION_MATRIX, GL_VIEWPORT,
)
from OpenGL.GLU import gluProject

from app.ui_ux import settings as S

# ----------------------------------------------------------------------
# Fontes e cache de texto (glDrawPixels a cada frame é caro; cacheia)
# ----------------------------------------------------------------------
_fonts = {}
_text_cache = {}
_CACHE_CAP = 900


def _font(size):
    f = _fonts.get(size)
    if f is None:
        f = pygame.font.SysFont(S.FONT_NAME, size, bold=True)
        _fonts[size] = f
    return f


def text_w(s, size):
    return _font(size).size(s)[0]


def fit(s, size, max_w):
    """Trunca com reticências para caber em max_w pixels."""
    if text_w(s, size) <= max_w:
        return s
    while s and text_w(s + "…", size) > max_w:
        s = s[:-1]
    return s + "…"


def wrap(s, size, max_w, max_lines=3):
    """Quebra por palavras; a última linha ganha reticências se sobrar texto."""
    words, lines, cur = s.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if text_w(cand, size) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if not lines:
        return [""]
    consumed = len(" ".join(lines).split())
    if consumed < len(words):
        lines[-1] = fit(lines[-1] + " …", size, max_w)
    return lines


def text(x, y, s, size=S.FS_BODY, color=S.TEXT, align="left", vcenter=None,
         screen_h=None):
    """Escreve s com o canto superior-esquerdo em (x, y) — origem no topo.

    align: left | center | right (x vira a borda/centro correspondente).
    vcenter: se dado, y é ignorado e o texto é centrado verticalmente nele.
    """
    if not s:
        return
    key = (s, size, color)
    item = _text_cache.get(key)
    if item is None:
        surf = _font(size).render(s, True, color)
        data = pygame.image.tostring(surf, "RGBA", True)
        item = (data, surf.get_width(), surf.get_height())
        if len(_text_cache) > _CACHE_CAP:
            _text_cache.clear()
        _text_cache[key] = item
    data, tw, th = item

    if align == "center":
        x -= tw / 2
    elif align == "right":
        x -= tw
    if vcenter is not None:
        y = vcenter - th / 2

    h = screen_h if screen_h is not None else _screen[1]
    glWindowPos2d(int(x), int(h - y - th))
    glDrawPixels(tw, th, GL_RGBA, GL_UNSIGNED_BYTE, data)


# ----------------------------------------------------------------------
# Primitivas
# ----------------------------------------------------------------------
_screen = (S.RES[0], S.RES[1])


def begin_hud(w, h):
    """Prepara projeção ortográfica com origem no topo-esquerdo."""
    global _screen
    _screen = (w, h)
    glViewport(0, 0, w, h)
    glDisable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, w, h, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()


def end_hud():
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)


def _round_poly(x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    pts = []
    corners = [(x + w - r, y + r, -90), (x + w - r, y + h - r, 0),
               (x + r, y + h - r, 90), (x + r, y + r, 180)]
    for cx, cy, a0 in corners:
        for i in range(5):
            a = math.radians(a0 + i * 22.5)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def rect(x, y, w, h, color, alpha=1.0, radius=S.RADIUS):
    glColor4f(*S.gl(color, alpha))
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(x + w / 2, y + h / 2)
    pts = _round_poly(x, y, w, h, radius)
    for px, py in pts:
        glVertex2f(px, py)
    glVertex2f(pts[0][0], pts[0][1])
    glEnd()


def outline(x, y, w, h, color, alpha=1.0, radius=S.RADIUS, width=1.0):
    glColor4f(*S.gl(color, alpha))
    glLineWidth(width)
    glBegin(GL_LINE_LOOP)
    for px, py in _round_poly(x, y, w, h, radius):
        glVertex2f(px, py)
    glEnd()
    glLineWidth(1.0)


def card(x, y, w, h, fill=S.SURFACE, alpha=0.96, border=S.BORDER):
    rect(x, y, w, h, fill, alpha)
    if border:
        outline(x, y, w, h, border, 0.9)


def pill(x, y, label, color, size=S.FS_TINY, pad=8, h=20, filled=False):
    w = text_w(label, size) + pad * 2
    if filled:
        rect(x, y, w, h, color, 1.0, h / 2)
        text(x + pad, y, label, size, S.BG, vcenter=y + h / 2)
    else:
        rect(x, y, w, h, color, 0.18, h / 2)
        outline(x, y, w, h, color, 0.75, h / 2)
        text(x + pad, y, label, size, color, vcenter=y + h / 2)
    return w


def key_chip(x, y, label, active=True, w=24, h=21):
    col = S.ACCENT if active else S.TEXT_FAINT
    rect(x, y, w, h, col, 0.20, 6)
    outline(x, y, w, h, col, 0.65, 6)
    text(x + w / 2, y, label, S.FS_SMALL, col, align="center", vcenter=y + h / 2)
    return w


def dot(x, y, r, color, alpha=1.0):
    glColor4f(*S.gl(color, alpha))
    glBegin(GL_TRIANGLE_FAN)
    glVertex2f(x, y)
    for i in range(13):
        a = math.radians(i * 30)
        glVertex2f(x + r * math.cos(a), y + r * math.sin(a))
    glEnd()


# ----------------------------------------------------------------------
# Logo
# ----------------------------------------------------------------------
def load_logo(path):
    try:
        img = pygame.image.load(path)
        # tostring(..., flipped=True) já entrega as linhas de baixo p/ cima,
        # que é a ordem que o glTexImage2D espera (t=0 na base da textura).
        data = pygame.image.tostring(img, "RGBA", True)
        w, h = img.get_rect().size
        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        return tex, w, h
    except Exception:
        return None, 0, 0


def draw_logo(logo, x, y, max_w=150, alpha=0.9):
    tex, w, h = logo
    if not tex:
        return 0
    scale = max_w / float(w)
    dw, dh = max_w, h * scale
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex)
    glColor4f(1, 1, 1, alpha)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 1); glVertex2f(x, y)                 # topo-esq da imagem
    glTexCoord2f(1, 1); glVertex2f(x + dw, y)
    glTexCoord2f(1, 0); glVertex2f(x + dw, y + dh)
    glTexCoord2f(0, 0); glVertex2f(x, y + dh)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    return dh


# ----------------------------------------------------------------------
# Layout — tudo derivado do tamanho atual da janela (a janela é redimensionável)
# ----------------------------------------------------------------------
def layout(w, h):
    """Deriva todos os retângulos da janela atual (a janela é redimensionável).

    A altura das linhas de comando é calculada a partir do espaço que sobra,
    então o painel inteiro cabe de 700 px a 4K sem corte nem sobreposição.
    """
    compact = h < 830
    pad, gap, m = S.PAD, S.GAP, S.MARGIN
    head_h = 56 if compact else 62
    met_h = 96 if compact else 108
    sol_h = 56 if compact else 64
    sect_extra = 22 + pad                     # título + respiro de cada card
    fixed = head_h + met_h + sol_h + 3 * sect_extra + 6 * gap + 2 * m
    row = int(max(22, min(S.ROW_H, (h - fixed) / 12.0)))   # 2+5+5 linhas

    px = w - S.PANEL_W
    pw = S.PANEL_W - m
    y = m
    L = {"compact": compact, "row": row, "panel_x": px, "panel_w": pw}

    def take(height):
        nonlocal y
        r = (px, y, pw, height)
        y += height + gap
        return r

    L["header"] = take(head_h)
    L["metrics"] = take(met_h)
    L["solution"] = take(sol_h)
    L["flows"] = take(sect_extra + 2 * row)
    L["steps"] = take(sect_extra + 5 * row)
    L["config"] = take(sect_extra + 5 * row)
    L["panel_bottom"] = y

    # Cena 3D: tudo à esquerda do painel, acima do rodapé.
    L["scene"] = (0, 0, px, h - S.FOOTER_H)
    L["footer"] = (0, h - S.FOOTER_H, px, S.FOOTER_H)
    log_w = max(300, min(600, px - 2 * m - 190))   # deixa o gizmo de eixos livre
    log_h = 132 if not compact else 108
    L["log"] = (m, h - S.FOOTER_H - m - log_h, log_w, log_h)
    return L


# ----------------------------------------------------------------------
# Seções do painel lateral
# ----------------------------------------------------------------------
def _section_title(x, y, w, title, hint=None):
    text(x, y, title.upper(), S.FS_TINY, S.TEXT_FAINT)
    if hint:
        text(x + w, y, hint, S.FS_TINY, S.TEXT_FAINT, align="right")
    return y + 18


def draw_header(ui, r):
    x, y, w, h = r
    card(x, y, w, h)
    text(x + S.PAD, y + 10, "RAIDEN", S.FS_TITLE, S.TEXT)
    sub = f"{ui.method} · {ui.port_label}"
    text(x + S.PAD, y + h - 22, fit(sub, S.FS_TINY, w - 130), S.FS_TINY, S.TEXT_DIM)

    col = S.OK if ui.mode == "real" else (S.INFO if ui.mode == "uno_dummy" else S.WARN)
    pw = text_w(ui.mode_label, S.FS_TINY) + 16
    pill(x + w - S.PAD - pw, y + 11, ui.mode_label, col)

    lcol = S.OK if ui.connected else S.ERR
    lbl = "conectado" if ui.connected else "sem link"
    text(x + w - S.PAD, y + h - 26, lbl, S.FS_TINY, lcol, align="right")
    dot(x + w - S.PAD - text_w(lbl, S.FS_TINY) - 8, y + h - 19, 3.5, lcol)


def draw_metrics(ui, r):
    x, y, w, h = r
    card(x, y, w, h)
    cw = (w - 2 * S.PAD) / 3.0
    vals = [
        ("MOVIMENTOS", str(ui.move_count), S.TEXT),
        ("TEMPO", ui.time_label, S.ACCENT if ui.busy else S.TEXT),
        ("ETAPA", ui.step_label, ui.step_color),
    ]
    for i, (lab, val, col) in enumerate(vals):
        cx = x + S.PAD + cw * i
        text(cx, y + 10, lab, S.FS_TINY, S.TEXT_FAINT)
        fs = S.FS_BIG if i < 2 else S.FS_SMALL
        text(cx, y + 29 if i == 2 else y + 26, fit(val, fs, cw - 6), fs, col)
        if i == 1 and ui.time_sub:
            text(cx, y + 54, fit(ui.time_sub, S.FS_TINY, cw - 6),
                 S.FS_TINY, S.TEXT_FAINT)

    # Sensores: 12 quadradinhos = SCAN-MAP (s0*), na ordem do NS lógico.
    sy = y + h - 26
    text(x + S.PAD, sy - 14, "SENSORES", S.FS_TINY, S.TEXT_FAINT)
    sw, sg = 18, 4
    for i in range(12):
        st = ui.sensors[i] if ui.sensors else None
        col = S.SURFACE_HI if st is None else (S.OK if st else S.ERR)
        sx = x + S.PAD + i * (sw + sg)
        rect(sx, sy, sw, 14, col, 0.30 if st is None else 0.85, 3)
        text(sx + sw / 2, sy, str(i), S.FS_TINY,
             S.TEXT_FAINT if st is None else S.BG, align="center", vcenter=sy + 7)


def draw_solution(ui, r):
    x, y, w, h = r
    card(x, y, w, h)
    text(x + S.PAD, y + 9, "SOLUÇÃO", S.FS_TINY, S.TEXT_FAINT)
    if ui.solution:
        lines = wrap(ui.solution, S.FS_SMALL, w - 2 * S.PAD, 2)
        for i, ln in enumerate(lines):
            text(x + S.PAD, y + 25 + i * 16, ln, S.FS_SMALL, S.TEXT)
    else:
        text(x + S.PAD, y + 27, "— nenhuma solução calculada —", S.FS_SMALL, S.TEXT_FAINT)


def _command_rows(ui, r, title, rows, row_h):
    x, y, w, h = r
    card(x, y, w, h)
    yy = _section_title(x + S.PAD, y + 9, w - 2 * S.PAD, title)
    for key, _action, label, hint in rows:
        active = not ui.locked
        hx = key_chip(x + S.PAD, yy + (row_h - 21) / 2, key, active)
        lx = x + S.PAD + hx + 10
        text(lx, yy, label, S.FS_BODY,
             S.TEXT if active else S.TEXT_FAINT, vcenter=yy + row_h / 2)
        # a dica só entra se sobrar espaço depois do rótulo (nunca sobrepõe)
        free = (x + w - S.PAD) - (lx + text_w(label, S.FS_BODY) + 14)
        if hint and free > 52:
            text(x + w - S.PAD, yy, fit(hint, S.FS_TINY, free), S.FS_TINY,
                 S.TEXT_FAINT, align="right", vcenter=yy + row_h / 2)
        yy += row_h


def draw_flows(ui, r, rows, row_h):
    _command_rows(ui, r, "Fluxos", rows, row_h)


def draw_steps(ui, r, rows, row_h):
    _command_rows(ui, r, "Etapas isoladas", rows, row_h)


def draw_config(ui, r, row_h):
    """Painel de configuração — o antigo [S] do Cube3D, agora aqui dentro."""
    x, y, w, h = r
    cfg = ui.config
    card(x, y, w, h, fill=S.SURFACE_ALT if cfg.active else S.SURFACE)
    from app.ui_ux.controls import CONFIG_HINT_ACTIVE, CONFIG_HINT_IDLE
    hint = CONFIG_HINT_ACTIVE if cfg.active else CONFIG_HINT_IDLE
    yy = _section_title(x + S.PAD, y + 9, w - 2 * S.PAD, "Configuração",
                        fit(hint, S.FS_TINY, w * 0.62))
    for i, f in enumerate(cfg.fields):
        sel = cfg.active and i == cfg.index
        ry = yy + i * row_h
        if sel:
            rect(x + 6, ry + 1, w - 12, row_h - 2, S.ACCENT, 0.16, 6)
            outline(x + 6, ry + 1, w - 12, row_h - 2, S.ACCENT, 0.5, 6)
        text(x + S.PAD + 4, ry, f.label, S.FS_SMALL,
             S.TEXT if sel else S.TEXT_DIM, vcenter=ry + row_h / 2)
        val = f.display()
        col = S.ACCENT if sel else S.TEXT
        if cfg.active and sel and f.kind != "enum":
            val += "▏"
        if f.dirty and not sel:
            col = S.WARN
        text(x + w - S.PAD - 4, ry, fit(val, S.FS_SMALL, w * 0.5), S.FS_SMALL,
             col, align="right", vcenter=ry + row_h / 2)


def draw_log(ui, r):
    x, y, w, h = r
    rect(x, y, w, h, S.BG, 0.72)
    outline(x, y, w, h, S.BORDER, 0.55)
    text(x + S.PAD, y + 7, "CONSOLE", S.FS_TINY, S.TEXT_FAINT)
    line_h = 17
    n = max(1, int((h - 26) // line_h))
    lines = ui.log[-n:]
    for i, (level, msg) in enumerate(lines):
        ly = y + 24 + i * line_h
        col = S.LEVEL_COLOR.get(level, S.TEXT_DIM)
        dot(x + S.PAD + 3, ly + 8, 3.0, col)
        text(x + S.PAD + 14, ly, fit(msg, S.FS_SMALL, w - 2 * S.PAD - 18),
             S.FS_SMALL, S.TEXT if level in ("ok", "info") else col)


def draw_footer(ui, r):
    x, y, w, h = r
    rect(x, y, w, h, S.SURFACE, 0.92, 0)
    glColor4f(*S.gl(S.BORDER, 0.8))
    glBegin(GL_LINES)
    glVertex2f(x, y); glVertex2f(x + w, y)
    glEnd()
    avail = w - 2 * S.MARGIN
    text(x + S.MARGIN, y + 8, fit(ui.footer_left, S.FS_SMALL, avail),
         S.FS_SMALL, S.TEXT_DIM)
    text(x + S.MARGIN, y + 25, fit(ui.footer_right, S.FS_TINY, avail),
         S.FS_TINY, S.TEXT_FAINT)


def draw_busy_bar(ui, r, t):
    """Barra fina animada no topo da cena enquanto a worker está ocupada."""
    x, y, w, _h = r
    rect(x, y, w, 3, S.SURFACE_HI, 0.9, 0)
    seg = w * 0.22
    pos = (t * 0.45) % 1.0
    sx = x - seg + pos * (w + seg)
    rect(max(x, sx), y, min(seg, x + w - max(x, sx)), 3, S.ACCENT, 1.0, 0)


def draw_prompt(ui, w, h):
    """Overlay de entrada de texto (executar sequência)."""
    p = ui.prompt
    if not p:
        return
    rect(0, 0, w, h, S.BG, 0.62, 0)
    bw, bh = min(720, w - 80), 132
    bx, by = (w - bw) / 2, (h - bh) / 2
    card(bx, by, bw, bh, fill=S.SURFACE_ALT, alpha=0.99, border=S.ACCENT)
    text(bx + S.PAD * 2, by + 16, p.title, S.FS_BODY, S.TEXT)
    text(bx + S.PAD * 2, by + 38, p.hint, S.FS_TINY, S.TEXT_DIM)
    fx, fy, fw, fh = bx + S.PAD * 2, by + 58, bw - S.PAD * 4, 34
    rect(fx, fy, fw, fh, S.BG, 0.9, 6)
    outline(fx, fy, fw, fh, S.ACCENT, 0.8, 6)
    text(fx + 10, fy, fit(p.text + "▏", S.FS_BODY, fw - 20), S.FS_BODY,
         S.TEXT, vcenter=fy + fh / 2)
    text(bx + bw - S.PAD * 2, by + bh - 24, "ENTER executa · ESC cancela",
         S.FS_TINY, S.TEXT_FAINT, align="right")


# ----------------------------------------------------------------------
# Gizmo de eixos (cores do cubo = dado do cubo, permitido aqui)
# ----------------------------------------------------------------------
_AXIS_COLORS = {
    'U': (1.0, 1.0, 1.0), 'F': (0.05, 0.75, 0.28), 'L': (1.0, 0.48, 0.05),
    'D': (1.0, 0.85, 0.05), 'R': (0.90, 0.12, 0.15), 'B': (0.10, 0.32, 0.90),
}
_AXIS_VECS = {'R': (1, 0, 0), 'L': (-1, 0, 0), 'U': (0, 1, 0),
              'D': (0, -1, 0), 'F': (0, 0, 1), 'B': (0, 0, -1)}


def draw_axes_corner(rot_x, rot_y, scene_w, scene_h, screen_h):
    """Indicador de orientação no canto inferior esquerdo da cena."""
    aspect = scene_w / float(max(1, scene_h))
    half_h = math.tan(math.radians(22.5)) * 6.0
    half_w = half_h * aspect
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glTranslatef(half_w * 0.72, -half_h * 0.56, -6.0)
    glRotatef(rot_x, 1, 0, 0)
    glRotatef(rot_y, 0, 1, 0)
    glDisable(GL_DEPTH_TEST)
    glLineWidth(3.0)

    s = 0.52
    glBegin(GL_LINES)
    for face, vec in _AXIS_VECS.items():
        glColor3f(*_AXIS_COLORS[face])
        glVertex3f(0, 0, 0)
        glVertex3f(vec[0] * s, vec[1] * s, vec[2] * s)
    glEnd()
    glLineWidth(1.0)

    modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
    projection = glGetDoublev(GL_PROJECTION_MATRIX)
    viewport = glGetIntegerv(GL_VIEWPORT)
    off = s + 0.16
    for face, vec in _AXIS_VECS.items():
        try:
            wx, wy, wz = gluProject(vec[0] * off, vec[1] * off, vec[2] * off,
                                    modelview, projection, viewport)
            if 0.0 <= wz <= 1.0:
                text(wx, screen_h - wy, face, S.FS_TINY,
                     tuple(int(c * 255) for c in _AXIS_COLORS[face]),
                     align="center", vcenter=screen_h - wy, screen_h=screen_h)
        except Exception:
            pass

    glEnable(GL_DEPTH_TEST)
    glPopMatrix()
