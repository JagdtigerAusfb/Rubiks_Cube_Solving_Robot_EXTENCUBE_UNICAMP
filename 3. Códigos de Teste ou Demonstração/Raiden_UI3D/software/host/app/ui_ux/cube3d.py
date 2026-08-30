"""Cubo 3D da GUI — modelo puramente VISUAL (herdado do Cube3D).

Não fala serial, não resolve nada, não persiste estado: apenas desenha o
cubo e anima o que a UI mandar. Quem manda é o main_ui, a partir dos
eventos publicados pelo barramento (estado sensoriado, solução executada,
giro manual do teclado).

Dois modos de "assistir":
  - REVELAÇÃO: recebe a matriz 6x8 do sense e acende os 48 adesivos aos
    poucos, face a face, na ordem de contrato (o cubo sendo sensoriado);
  - ANIMAÇÃO: consome uma fila de giros (face, voltas) enquanto o robô
    executa a sequência (o cubo sendo resolvido).
"""

from OpenGL.GL import (
    glPushMatrix, glPopMatrix, glTranslatef, glRotatef,
    glBegin, glEnd, glColor3fv, glColor3f, glVertex3f,
    glEnable, glDisable, glPolygonOffset,
    GL_QUADS, GL_POLYGON_OFFSET_FILL,
)

from app.communication.outer import SOLVED_FACELETS
from app.ui_ux.settings import (
    COLOR_MAP, CUBIE_SIZE, STICKER_SIZE, STICKER_LIFT, BODY_COLOR,
    ANIM_DEG_PER_SEC, REVEAL_STEP_S, REVEAL_FACE_PAUSE_S,
)

# Faces do cubie: (id, eixo normal, sinal). Os quads são gerados a partir
# disso — corpo escuro em toda a face, adesivo embutido e menor. É esse
# embutimento que impede ver a cor da face vizinha na quina.
_FACES = [('U', 1, 1), ('D', 1, -1), ('F', 2, 1),
          ('B', 2, -1), ('L', 0, -1), ('R', 0, 1)]


def _quad(axis, sign, plane, half):
    """4 vértices do quadrado perpendicular a `axis`, no plano sign*plane."""
    u, v = [i for i in (0, 1, 2) if i != axis]
    pts = []
    for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        p = [0.0, 0.0, 0.0]
        p[axis] = sign * plane
        p[u] = du * half
        p[v] = dv * half
        pts.append(tuple(p))
    return pts


_BODY_QUADS = [(f, _quad(ax, sg, CUBIE_SIZE / 2.0, CUBIE_SIZE / 2.0))
               for f, ax, sg in _FACES]
_STICKER_QUADS = {
    f: _quad(ax, sg, CUBIE_SIZE / 2.0 + STICKER_LIFT, STICKER_SIZE / 2.0)
    for f, ax, sg in _FACES
}
# Face -> (eixo, valor da camada externa): serve para saber se aquela face do
# cubie está virada para fora do cubo (só essas ganham adesivo).
_OUTER = {f: (ax, sg) for f, ax, sg in _FACES}


def _build_scan_order():
    """(face, [(x,y,z) x9]) row-major, na ordem URFDLB dos 54 facelets."""
    return [
        ('U', [(x, 1, z) for z in (-1, 0, 1) for x in (-1, 0, 1)]),
        ('R', [(1, y, z) for y in (1, 0, -1) for z in (1, 0, -1)]),
        ('F', [(x, y, 1) for y in (1, 0, -1) for x in (-1, 0, 1)]),
        ('D', [(x, -1, z) for z in (1, 0, -1) for x in (-1, 0, 1)]),
        ('L', [(-1, y, z) for y in (1, 0, -1) for z in (-1, 0, 1)]),
        ('B', [(x, y, -1) for y in (1, 0, -1) for x in (1, 0, -1)]),
    ]


FACE_SCAN_ORDER = _build_scan_order()


class Cubie:
    def __init__(self, position):
        self.pos = list(position)
        self.colors = {}

    def draw(self, anim_params=None):
        glPushMatrix()
        if anim_params:
            ax_idx, angle, layer_val = anim_params
            if round(self.pos[ax_idx]) == layer_val:
                rot_v = [0, 0, 0]
                rot_v[ax_idx] = 1
                glRotatef(angle, *rot_v)

        glTranslatef(*self.pos)

        # 1) corpo escuro inteiro — é o que aparece nas frestas
        glColor3f(*BODY_COLOR)
        glBegin(GL_QUADS)
        for _face_id, verts in _BODY_QUADS:
            for v in verts:
                glVertex3f(*v)
        glEnd()

        # 2) adesivos, só nas faces viradas para fora do cubo.
        # Adesivo e corpo são quase coplanares: sem o polygon offset o
        # z-buffer alterna entre os dois e aparecem listras (z-fighting).
        glEnable(GL_POLYGON_OFFSET_FILL)
        glPolygonOffset(-1.0, -1.0)
        glBegin(GL_QUADS)
        for face_id, (axis, sign) in _OUTER.items():
            if round(self.pos[axis]) != sign:
                continue                      # face interna: sem adesivo
            glColor3fv(self.colors.get(face_id, COLOR_MAP['.']))
            for v in _STICKER_QUADS[face_id]:
                glVertex3f(*v)
        glEnd()
        glDisable(GL_POLYGON_OFFSET_FILL)
        glPopMatrix()


class VisualCube:
    """Estado visual do cubo + fila de animação + revelação do sensoriamento."""

    _FACE_MAPPING = {
        'R': ('x',  1, -1),
        'L': ('x', -1,  1),
        'U': ('y',  1, -1),
        'D': ('y', -1,  1),
        'F': ('z',  1, -1),
        'B': ('z', -1,  1),
    }

    def __init__(self):
        self.cubies = [Cubie((x, y, z))
                       for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)]
        self.queue = []
        self.is_animating = False
        self.anim_angle = 0.0
        self.target_visual_angle = 0.0
        self.current_move = None
        self.on_move_done = None          # callback(face, turns) — contador
        # revelação
        self._reveal = []                 # [(t, face_key, (x,y,z), rgb), ...]
        self._reveal_i = 0
        self._reveal_t = 0.0
        self.revealing = False
        self.reveal_face = None           # índice 0..5 da face em revelação
        self.load_facelets(SOLVED_FACELETS)

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------
    def get_cubie_at(self, x, y, z):
        target = [round(x), round(y), round(z)]
        for c in self.cubies:
            if [round(p) for p in c.pos] == target:
                return c
        return None

    def load_facelets(self, s: str):
        """Aplica 54 facelets (row-major URFDLB) direto, sem animação."""
        if len(s) != 54:
            return False
        idx = 0
        for face_key, positions in FACE_SCAN_ORDER:
            for (x, y, z) in positions:
                cubie = self.get_cubie_at(x, y, z)
                if cubie:
                    cubie.colors[face_key] = COLOR_MAP.get(s[idx], COLOR_MAP['.'])
                idx += 1
        return True

    def blank(self):
        """Apaga todos os adesivos (cubo 'ainda não lido')."""
        for c in self.cubies:
            for face_key in _OUTER:
                c.colors[face_key] = COLOR_MAP['.']

    def reset_solved(self):
        self.cancel()
        self.load_facelets(SOLVED_FACELETS)

    def cancel(self):
        """Aborta fila de giros e revelação em curso."""
        self.queue.clear()
        self.is_animating = False
        self.anim_angle = 0.0
        self.current_move = None
        self.revealing = False
        self.reveal_face = None
        self._reveal = []

    # ------------------------------------------------------------------
    # Revelação (o cubo sendo sensoriado)
    # ------------------------------------------------------------------
    def begin_reveal(self, facelets: str, order):
        """Acende os 54 adesivos aos poucos, na ordem dada pelo adapter.

        order: [(face_idx, rowmajor_idx), ...] — ver outer.sense_reveal_order.
        """
        if len(facelets) != 54:
            return False
        self.cancel()
        self.blank()
        t = 0.0
        last_face = None
        self._reveal = []
        for face_idx, rm in order:
            if face_idx != last_face:
                t += REVEAL_FACE_PAUSE_S
                last_face = face_idx
            face_key, positions = FACE_SCAN_ORDER[face_idx]
            rgb = COLOR_MAP.get(facelets[face_idx * 9 + rm], COLOR_MAP['.'])
            self._reveal.append((t, face_idx, face_key, positions[rm], rgb))
            t += REVEAL_STEP_S
        self._reveal_i = 0
        self._reveal_t = 0.0
        self.revealing = True
        self.reveal_face = self._reveal[0][1] if self._reveal else None
        return True

    def _update_reveal(self, dt):
        self._reveal_t += dt
        while self._reveal_i < len(self._reveal):
            t, face_idx, face_key, pos, rgb = self._reveal[self._reveal_i]
            if t > self._reveal_t:
                break
            cubie = self.get_cubie_at(*pos)
            if cubie:
                cubie.colors[face_key] = rgb
            self.reveal_face = face_idx
            self._reveal_i += 1
        if self._reveal_i >= len(self._reveal):
            self.revealing = False
            self.reveal_face = None

    # ------------------------------------------------------------------
    # Giros (o cubo sendo resolvido)
    # ------------------------------------------------------------------
    def enqueue(self, face: str, turns: int = 1):
        if face in self._FACE_MAPPING:
            self.queue.append({'face': face, 'times': int(turns)})

    def enqueue_many(self, moves):
        for face, turns in moves:
            self.enqueue(face, turns)

    @property
    def busy(self) -> bool:
        return self.is_animating or bool(self.queue) or self.revealing

    def update(self, dt: float):
        if self.revealing:
            self._update_reveal(dt)
            return

        if not self.is_animating and self.queue:
            self.current_move = self.queue.pop(0)
            self.is_animating = True
            self.anim_angle = 0.0
            t = self.current_move['times']
            self.target_visual_angle = 180.0 if t == 2 else (90.0 if t == 1 else -90.0)

        if self.is_animating:
            step = ANIM_DEG_PER_SEC * dt
            if self.target_visual_angle < 0:
                self.anim_angle -= step
                if self.anim_angle <= self.target_visual_angle:
                    self._finish_move()
            else:
                self.anim_angle += step
                if self.anim_angle >= self.target_visual_angle:
                    self._finish_move()

    def _finish_move(self):
        face, times = self.current_move['face'], self.current_move['times']
        for _ in range(times):
            self._rotate_layer_logical(face)
        self.is_animating = False
        self.anim_angle = 0.0
        self.current_move = None
        if self.on_move_done:
            self.on_move_done(face, times)

    def _rotate_layer_logical(self, face):
        axis, layer_val, direction = self._FACE_MAPPING[face]
        ax_idx = "xyz".index(axis)
        for c in self.cubies:
            if round(c.pos[ax_idx]) == layer_val:
                x, y, z = c.pos
                if axis == 'x':
                    c.pos[1], c.pos[2] = -direction * z, direction * y
                elif axis == 'y':
                    c.pos[0], c.pos[2] = direction * z, -direction * x
                else:
                    c.pos[0], c.pos[1] = -direction * y, direction * x
                self._rotate_cubie_colors(c, axis, direction)

    @staticmethod
    def _rotate_cubie_colors(cubie, axis, direction):
        cycles = {
            'x': ['U', 'F', 'D', 'B'],
            'y': ['F', 'R', 'B', 'L'],
            'z': ['U', 'L', 'D', 'R'],
        }
        cycle = cycles[axis]
        if direction == -1:
            cycle = cycle[::-1]
        old = cubie.colors.copy()
        for i in range(4):
            src, dst = cycle[i], cycle[(i + 1) % 4]
            if src in old:
                cubie.colors[dst] = old[src]
            elif dst in cubie.colors:
                del cubie.colors[dst]

    # ------------------------------------------------------------------
    def draw(self):
        anim_params = None
        if self.is_animating and self.current_move:
            axis_name, layer_val, direction = self._FACE_MAPPING[self.current_move['face']]
            ax_idx = "xyz".index(axis_name)
            anim_params = (ax_idx, self.anim_angle * direction, layer_val)
        for c in self.cubies:
            c.draw(anim_params)
