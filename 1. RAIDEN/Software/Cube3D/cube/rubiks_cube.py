import json
import logging
import os

from OpenGL.GL import (
    glPushMatrix, glPopMatrix, glTranslatef, glRotatef,
    glBegin, glEnd, glColor3fv, glVertex3f, GL_QUADS,
)

from config import COLOR_MAP, CUBE_STATE_PATH, color_to_char

logger = logging.getLogger(__name__)


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
        size = 0.96
        faces = [
            ('U', [(0.5, 0.5, 0.5), (-0.5, 0.5, 0.5), (-0.5, 0.5, -0.5), (0.5, 0.5, -0.5)]),
            ('D', [(0.5, -0.5, -0.5), (-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (0.5, -0.5, 0.5)]),
            ('F', [(0.5, 0.5, 0.5), (0.5, -0.5, 0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, 0.5)]),
            ('B', [(-0.5, 0.5, -0.5), (-0.5, -0.5, -0.5), (0.5, -0.5, -0.5), (0.5, 0.5, -0.5)]),
            ('L', [(-0.5, 0.5, 0.5), (-0.5, -0.5, 0.5), (-0.5, -0.5, -0.5), (-0.5, 0.5, -0.5)]),
            ('R', [(0.5, 0.5, -0.5), (0.5, -0.5, -0.5), (0.5, -0.5, 0.5), (0.5, 0.5, 0.5)]),
        ]
        glBegin(GL_QUADS)
        for face_id, verts in faces:
            color = self.colors.get(face_id, COLOR_MAP['.'])
            glColor3fv(color)
            for v in verts:
                glVertex3f(v[0] * size, v[1] * size, v[2] * size)
        glEnd()
        glPopMatrix()


# Ordem de varredura das faces — compartilhada por get_state_string e load_from_json
# Cada entrada: (face_key, lista_de_(x,y,z))
def _build_scan_order():
    order = []
    # U: y=+1, varre z então x
    order.append(('U', [(x, 1, z) for z in [-1, 0, 1] for x in [-1, 0, 1]]))
    # R: x=+1, varre y então z
    order.append(('R', [(1, y, z) for y in [1, 0, -1] for z in [1, 0, -1]]))
    # F: z=+1, varre y então x
    order.append(('F', [(x, y, 1) for y in [1, 0, -1] for x in [-1, 0, 1]]))
    # D: y=-1, varre z então x
    order.append(('D', [(x, -1, z) for z in [1, 0, -1] for x in [-1, 0, 1]]))
    # L: x=-1, varre y então z
    order.append(('L', [(-1, y, z) for y in [1, 0, -1] for z in [-1, 0, 1]]))
    # B: z=-1, varre y então x
    order.append(('B', [(x, y, -1) for y in [1, 0, -1] for x in [1, 0, -1]]))
    return order

FACE_SCAN_ORDER = _build_scan_order()


class RubiksCube:
    def __init__(self, robot):
        self.robot = robot
        self.cubies = [
            Cubie((x, y, z))
            for x in [-1, 0, 1]
            for y in [-1, 0, 1]
            for z in [-1, 0, 1]
        ]
        self.queue = []
        self.is_animating = False
        self.anim_angle = 0
        self.anim_speed = 15
        self.current_move = None
        self.target_visual_angle = 0
        self.load_from_json()

    # ------------------------------------------------------------------
    # Movimentos
    # ------------------------------------------------------------------

    def move(self, face, times=1, send_serial=True):
        from config import MOVE_TABLE
        if send_serial:
            char_move = MOVE_TABLE.get(f"{face}{times}")
            if char_move:
                self.robot.send_moves(char_move)
        self.queue.append({'face': face, 'times': times})

    def update_animation(self):
        if not self.is_animating and self.queue:
            self.current_move = self.queue.pop(0)
            self.is_animating = True
            self.anim_angle = 0
            t = self.current_move['times']
            self.target_visual_angle = 180 if t == 2 else (90 if t == 1 else -90)

        if self.is_animating:
            step = self.anim_speed
            if self.target_visual_angle < 0:
                self.anim_angle -= step
                if self.anim_angle <= self.target_visual_angle:
                    self.finish_move()
            else:
                self.anim_angle += step
                if self.anim_angle >= self.target_visual_angle:
                    self.finish_move()

    def finish_move(self):
        for _ in range(self.current_move['times']):
            self.rotate_layer_logical(self.current_move['face'])
        self.is_animating = False
        self.anim_angle = 0
        self.save_to_json()

    # ------------------------------------------------------------------
    # Rotação lógica
    # ------------------------------------------------------------------

    _FACE_MAPPING = {
        'R': ('x',  1, -1),
        'L': ('x', -1,  1),
        'U': ('y',  1, -1),
        'D': ('y', -1,  1),
        'F': ('z',  1, -1),
        'B': ('z', -1,  1),
    }

    def rotate_layer_logical(self, face):
        axis, layer_val, direction = self._FACE_MAPPING[face]
        ax_idx = "xyz".index(axis)
        for c in self.cubies:
            if round(c.pos[ax_idx]) == layer_val:
                x, y, z = c.pos
                if axis == 'x':
                    c.pos[1], c.pos[2] = -direction * z, direction * y
                elif axis == 'y':
                    c.pos[0], c.pos[2] = direction * z, -direction * x
                elif axis == 'z':
                    c.pos[0], c.pos[1] = -direction * y, direction * x
                self._rotate_cubie_colors(c, axis, direction)

    def _rotate_cubie_colors(self, cubie, axis, direction):
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
    # Renderização
    # ------------------------------------------------------------------

    def draw(self):
        anim_params = None
        if self.is_animating:
            axis_name, layer_val, direction = self._FACE_MAPPING[self.current_move['face']]
            ax_idx = "xyz".index(axis_name)
            anim_params = (ax_idx, self.anim_angle * direction, layer_val)
        for c in self.cubies:
            c.draw(anim_params)

    # ------------------------------------------------------------------
    # Utilitários
    # ------------------------------------------------------------------

    def get_cubie_at(self, x, y, z):
        target = [round(x), round(y), round(z)]
        for c in self.cubies:
            if [round(p) for p in c.pos] == target:
                return c
        return None

    def get_state_string(self):
        result = ""
        for face_key, positions in FACE_SCAN_ORDER:
            for (x, y, z) in positions:
                c = self.get_cubie_at(x, y, z)
                if c:
                    color = c.colors.get(face_key, COLOR_MAP['.'])
                    result += color_to_char(color)
                else:
                    result += 'U'
        return result

    def save_to_json(self):
        state = self.get_state_string()
        try:
            with open(CUBE_STATE_PATH, 'w') as f:
                json.dump({"cube_string": state}, f)
        except OSError as e:
            logger.error("Falha ao salvar estado do cubo: %s", e)

    def load_from_json(self):
        default = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
        s = default

        if os.path.exists(CUBE_STATE_PATH):
            try:
                with open(CUBE_STATE_PATH, 'r') as f:
                    data = json.load(f)
                s = data.get("cube_string", default)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Não foi possível carregar cube_state.json: %s", e)

        if len(s) != 54:
            logger.warning("Estado inválido no JSON (tamanho %d), usando padrão.", len(s))
            s = default

        idx = 0
        for face_key, positions in FACE_SCAN_ORDER:
            for (x, y, z) in positions:
                cubie = self.get_cubie_at(x, y, z)
                if cubie:
                    cubie.colors[face_key] = COLOR_MAP[s[idx]]
                idx += 1
