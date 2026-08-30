"""Orquestra a GUI.

Composition root da interface: abre a janela, instancia o cubo 3D, o
Controller (que fala com o Raiden numa thread worker) e o painel lateral;
depois roda o loop de render consumindo o barramento de eventos.

Divisão de trabalho por thread:
  - worker  : serial, sensoriamento, solver, execução  -> publica eventos
  - render  : 60 fps, desenha, lê teclado              -> consome eventos

Nada de serial acontece nesta thread; nada de desenho acontece na worker.
"""

import logging
import time

import pygame
from pygame.locals import (
    DOUBLEBUF, OPENGL, RESIZABLE, QUIT, KEYDOWN, VIDEORESIZE,
    KMOD_SHIFT, KMOD_CTRL,
)
from OpenGL.GL import (
    glClearColor, glClear, glMatrixMode, glLoadIdentity, glViewport,
    glTranslatef, glPushMatrix, glPopMatrix, glRotatef, glEnable,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, GL_PROJECTION, GL_MODELVIEW,
    GL_DEPTH_TEST,
)
from OpenGL.GLU import gluPerspective

from app.communication.inner import BUS, Topic
from app.communication.outer import (
    state_to_facelets, sense_reveal_order, robot_sequence_to_visual,
)
from app.main_raiden import Mode
from app.ui_ux import hud
from app.ui_ux import settings as S
from app.ui_ux.controls import (
    Controller, ConfigPanel, Prompt, FLOWS, STEPS, MOVE_KEYS, NUMBER_ACTIONS,
    FOOTER_LEFT, FOOTER_RIGHT,
    A_CONFIG, A_METHOD, A_EXEC_SEQ, A_QUIT,
)

logger = logging.getLogger(__name__)

MODE_LABEL = {Mode.DEMO: "DEMO", Mode.UNO_DUMMY: "UNO DUMMY", Mode.REAL: "REAL"}
STEP_LABEL = {
    "scan": "Scan", "calibrate": "Calibração", "sense": "Sensoriamento",
    "solve": "Solução", "execute": "Execução", "set_speed": "Velocidade",
    "set_gap": "Pausa", "method": "Método",
}


class RaidenUI:
    def __init__(self, mode=Mode.REAL, port=None, method="kociemba"):
        pygame.init()
        pygame.display.set_caption(S.WINDOW_TITLE)
        self.w, self.h = S.RES
        self._set_mode(self.w, self.h)

        from app.ui_ux.cube3d import VisualCube
        self.cube = VisualCube()
        self.cube.on_move_done = self._on_move_done

        self.bus = BUS
        self.config = ConfigPanel(mode, port or "", method,
                                  S.DEFAULT_SPEED_US, S.DEFAULT_GAP_MS)
        self.controller = Controller(self.bus, mode, port, method,
                                     speed=S.DEFAULT_SPEED_US,
                                     gap=S.DEFAULT_GAP_MS)

        # --- estado apresentado ---
        self.mode = mode
        self.method = method
        self.port = port or ""
        self.connected = False
        self.busy = False
        self.sensors = None
        self.solution = None
        self.moves_total = 0
        self.moves_done = 0
        self.exec_time = None
        self.log = []
        self.prompt = None
        self.step_label = "—"
        self.step_color = S.TEXT_DIM
        self._t0 = None
        self._elapsed = 0.0
        self._stop_pending = False

        # --- câmera ---
        self.rot_x, self.rot_y = S.CAM_START
        self.cam_auto = False
        self._drag = False

        self.running = True
        self._subscribe()
        self._push_log("info", "Interface pronta. [1] prepara · [2] resolve e executa.")

    # ------------------------------------------------------------------
    # Janela
    # ------------------------------------------------------------------
    def _set_mode(self, w, h):
        self.w = max(w, S.MIN_RES[0])
        self.h = max(h, S.MIN_RES[1])
        pygame.display.set_mode((self.w, self.h), DOUBLEBUF | OPENGL | RESIZABLE)
        self.logo = hud.load_logo(S.LOGO_PATH)
        glEnable(GL_DEPTH_TEST)

    # ------------------------------------------------------------------
    # Eventos do barramento
    # ------------------------------------------------------------------
    def _subscribe(self):
        self.bus.subscribe(Topic.LOG, lambda p: self._push_log(*p))
        self.bus.subscribe(Topic.BUSY, self._on_busy)
        self.bus.subscribe(Topic.STEP, self._on_step)
        self.bus.subscribe(Topic.STATE, self._on_state)
        self.bus.subscribe(Topic.SOLUTION, self._on_solution)
        self.bus.subscribe(Topic.EXEC_START, self._on_exec_start)
        self.bus.subscribe(Topic.RUN, self._on_run)
        self.bus.subscribe(Topic.LINK, self._on_link)

    def _push_log(self, level, msg):
        self.log.append((level, msg))
        if len(self.log) > 200:
            del self.log[:100]

    def _on_run(self, _=None):
        """Zera e dispara o cronômetro do ciclo (começou o sensoriamento)."""
        self._t0 = time.monotonic()
        self._elapsed = 0.0
        self._stop_pending = False
        self.exec_time = None

    def _on_busy(self, busy):
        """O cronômetro NÃO acompanha 'ocupado' — só o ciclo do cubo.

        Ele nasce no r0* (sensoriamento). O fim é pedido aqui (o job da
        worker acabou), mas só efetivado em _update, quando o cubo 3D
        terminar de mostrar o que aconteceu — senão, em DEMO, o firmware
        responde em milissegundos e o contador zera antes de o usuário ver
        qualquer coisa.
        """
        self.busy = busy
        if not busy and self._t0 is not None:
            self._stop_pending = True

    def _on_step(self, res):
        self.step_label = STEP_LABEL.get(res.step, res.step)
        self.step_color = S.OK if res.ok else S.ERR
        if res.step == "scan" and isinstance(res.data, list):
            self.sensors = res.data
        elif res.step == "execute" and res.ok and isinstance(res.data, (int, float)):
            self.exec_time = float(res.data)

    def _on_state(self, state):
        """Estado sensoriado: acende os adesivos aos poucos, face a face."""
        try:
            facelets = state_to_facelets(state)
        except ValueError as e:
            self._push_log("err", f"Estado inválido para a UI: {e}")
            return
        self.cube.begin_reveal(facelets, sense_reveal_order())
        self.cam_auto = True
        self.solution = None
        self.moves_total = self.moves_done = 0

    def _on_solution(self, data):
        self.solution = data.get("solution")
        self.moves_total = int(data.get("move_count", 0))
        self.moves_done = 0

    def _on_exec_start(self, seq):
        """Enfileira o replay dos giros — sem cortar a revelação em curso.

        Se o firmware respondeu antes de a UI terminar de acender os
        adesivos (o caso do DEMO), a fila espera: primeiro o cubo aparece
        sensoriado, depois ele se resolve.
        """
        moves = robot_sequence_to_visual(seq)
        self.moves_total = len(moves) or self.moves_total
        self.moves_done = 0
        self.cube.enqueue_many(moves)

    def _on_link(self, info):
        self.mode = info.get("mode", self.mode)
        self.port = info.get("port") or ""
        self.connected = bool(info.get("connected"))
        self.method = info.get("method", self.method)
        self.config.field("mode").value = self.mode
        self.config.field("method").value = self.method

    def _on_move_done(self, face, turns):
        self.moves_done += 1

    # ------------------------------------------------------------------
    # Propriedades lidas pelo hud
    # ------------------------------------------------------------------
    @property
    def mode_label(self):
        return MODE_LABEL.get(self.mode, str(self.mode).upper())

    @property
    def port_label(self):
        if self.mode == Mode.DEMO:
            return "serial simulada"
        return self.port or "porta automática"

    @property
    def move_count(self):
        if self.cube.queue or self.cube.is_animating:
            return f"{self.moves_done}/{self.moves_total}"
        return str(self.moves_total) if self.moves_total else "--"

    @property
    def time_label(self):
        """Ciclo completo: início do sensoriamento -> fim da execução."""
        if self._t0 is not None:
            return f"{time.monotonic() - self._t0:.1f}s"
        if self._elapsed > 0.0:
            return f"{self._elapsed:.2f}s"
        return "--"

    @property
    def time_sub(self):
        """Detalhe: quanto disso foi motor, segundo o d_<seg>* do firmware."""
        if self.exec_time is not None:
            return f"motores {self.exec_time:.2f}s"
        return ""

    @property
    def locked(self):
        return self.busy

    footer_left = FOOTER_LEFT
    footer_right = FOOTER_RIGHT

    # ------------------------------------------------------------------
    # Teclado
    # ------------------------------------------------------------------
    def _on_key(self, event):
        if self.prompt is not None:
            return self._key_prompt(event)
        if self.config.active:
            return self._key_config(event)

        key = event.key
        action = NUMBER_ACTIONS.get(key)

        if key == pygame.K_ESCAPE or action == A_QUIT:
            self.running = False
            return
        if action == A_CONFIG or key == pygame.K_s:
            self.config.active = True
            return
        if action == A_METHOD:
            f = self.config.field("method")
            f.cycle(1)
            self.controller.apply_field(f)
            return
        if action == A_EXEC_SEQ:
            seq = self.controller.last_solution_sequence()
            self.prompt = Prompt("Executar sequência",
                                 "chars do alfabeto A–R (contracts/move_alphabet.md)",
                                 seq)
            return
        if action:
            self.controller.dispatch(action)
            return

        if key == pygame.K_c:
            self.cube.reset_solved()
            self.moves_total = self.moves_done = 0
            self.solution = None
            self._push_log("info", "Cubo virtual reposicionado (resolvido).")
            return

        if key in MOVE_KEYS:
            mods = pygame.key.get_mods()
            turns = 3 if (mods & KMOD_SHIFT) else (2 if (mods & KMOD_CTRL) else 1)
            face = MOVE_KEYS[key]
            self.cube.enqueue(face, turns)
            self.controller.manual_move(face, turns)

    def _flush_config(self):
        """Aplica o que foi digitado nos campos de ajuste (método/vel/pausa)."""
        for f in self.config.pending():
            self.controller.apply_field(f)

    def _key_config(self, event):
        cfg = self.config
        key = event.key
        if key == pygame.K_ESCAPE:
            self._flush_config()          # nada se perde por não dar ENTER
            cfg.active = False
            cfg.revert({"mode": self.mode, "method": self.method,
                        "port": self.port})
        elif key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
            self._flush_config()          # sair do campo já aplica
            cfg.move(-1 if key == pygame.K_UP else 1)
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            cfg.current.cycle(-1 if key == pygame.K_LEFT else 1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.controller.apply_field(cfg.current)
        elif key == pygame.K_BACKSPACE:
            cfg.current.backspace()
        elif event.unicode and event.unicode.isprintable():
            cfg.current.type_char(event.unicode)

    def _key_prompt(self, event):
        p = self.prompt
        key = event.key
        if key == pygame.K_ESCAPE:
            self.prompt = None
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            seq = p.text.strip().upper()
            self.prompt = None
            if not seq:
                self._push_log("warn", "Sequência vazia — nada a executar.")
                return
            bad = [c for c in seq if not ("A" <= c <= "R")]
            if bad:
                self._push_log("err", f"Chars fora de A–R: {''.join(sorted(set(bad)))}")
                return
            self.controller.execute_sequence(seq)
        elif key == pygame.K_BACKSPACE:
            p.text = p.text[:-1]
        elif event.unicode and event.unicode.isalpha():
            p.text += event.unicode.upper()

    # ------------------------------------------------------------------
    # Loop
    # ------------------------------------------------------------------
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == VIDEORESIZE:
                self._set_mode(event.w, event.h)
            elif event.type == KEYDOWN:
                self._on_key(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if event.pos[0] < self.w - S.PANEL_W:
                    self._drag = True
                    pygame.mouse.get_rel()
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._drag = False

    def _update(self, dt):
        self.bus.drain()
        # Fecha o cronômetro quando a worker acabou E o cubo 3D parou de
        # revelar/girar — o ciclo termina no que durar mais.
        if self._stop_pending and not self.cube.busy and self._t0 is not None:
            self._elapsed = time.monotonic() - self._t0
            self._t0 = None
            self._stop_pending = False
        if self._drag:
            dx, dy = pygame.mouse.get_rel()
            if dx or dy:
                self.rot_y += dx * S.DRAG_SENS
                self.rot_x += dy * S.DRAG_SENS
                self.cam_auto = False
        self.cube.update(dt)

        if self.cam_auto and self.cube.revealing and self.cube.reveal_face is not None:
            tx, ty = S.CAM_FACE_TARGET[self.cube.reveal_face]
            k = min(1.0, S.CAM_EASE * dt)
            self.rot_x += (tx - self.rot_x) * k
            self.rot_y += (self._shortest(self.rot_y, ty)) * k
        elif self.cam_auto and not self.cube.revealing:
            tx, ty = S.CAM_START
            k = min(1.0, (S.CAM_EASE * 0.5) * dt)
            self.rot_x += (tx - self.rot_x) * k
            self.rot_y += (self._shortest(self.rot_y, ty)) * k
            if abs(tx - self.rot_x) < 0.5:
                self.cam_auto = False

    @staticmethod
    def _shortest(cur, target):
        """Delta angular mais curto (evita a câmera dar a volta pelo caminho longo)."""
        d = (target - cur) % 360.0
        return d - 360.0 if d > 180.0 else d

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------
    def _draw(self, t):
        L = hud.layout(self.w, self.h)
        glViewport(0, 0, self.w, self.h)
        glClearColor(*S.gl(S.BG), 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # --- cena 3D (viewport à esquerda do painel, acima do rodapé) ---
        sx, sy, sw, sh = L["scene"]
        sh = max(1, sh)
        glViewport(0, self.h - sh, sw, sh)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, sw / float(sh), S.CAM_NEAR, S.CAM_FAR)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0, 0, S.CAM_DIST)

        glPushMatrix()
        glRotatef(self.rot_x, 1, 0, 0)
        glRotatef(self.rot_y, 0, 1, 0)
        self.cube.draw()
        glPopMatrix()

        hud.draw_axes_corner(self.rot_x, self.rot_y, sw, sh, self.h)

        # --- HUD ---
        hud.begin_hud(self.w, self.h)
        hud.draw_logo(self.logo, S.MARGIN, S.MARGIN, max_w=132)
        if self.busy:
            hud.draw_busy_bar(self, (0, 0, sw, 3), t)

        hud.draw_header(self, L["header"])
        hud.draw_metrics(self, L["metrics"])
        hud.draw_solution(self, L["solution"])
        hud.draw_flows(self, L["flows"], FLOWS, L["row"])
        hud.draw_steps(self, L["steps"], STEPS, L["row"])
        hud.draw_config(self, L["config"], L["row"])
        hud.draw_log(self, L["log"])
        hud.draw_footer(self, L["footer"])
        hud.draw_prompt(self, self.w, self.h)
        hud.end_hud()

        pygame.display.flip()

    def run(self):
        clock = pygame.time.Clock()
        t = 0.0
        while self.running:
            dt = clock.tick(S.FPS) / 1000.0
            t += dt
            self._handle_events()
            self._update(dt)
            self._draw(t)
        self.controller.shutdown()
        pygame.quit()


def run(mode=Mode.REAL, port=None, method="kociemba"):
    """Ponto de entrada da GUI (chamado por raiden.py)."""
    RaidenUI(mode=mode, port=port, method=method).run()
