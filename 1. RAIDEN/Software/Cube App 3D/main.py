import logging

import pygame
from pygame.locals import (
    DOUBLEBUF, OPENGL, QUIT, KEYDOWN, KMOD_SHIFT,
    K_r, K_l, K_u, K_d, K_f, K_b, K_s, K_x, K_2,
)
from OpenGL.GL import (
    glClearColor, glClear, glMatrixMode, glLoadIdentity,
    glTranslatef, glPushMatrix, glPopMatrix, glRotatef,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_PROJECTION, GL_MODELVIEW,
)
from OpenGL.GLU import gluPerspective

from config import RES, CUBE_STATE_PATH, LOGO_PATH
from robot.controller import RobotController
from cube.rubiks_cube import RubiksCube
from cube.solver import solve_from_file
from ui.hud import draw_hud, draw_axes_corner, load_logo
from ui.settings import open_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_solver(cube: RubiksCube):
    cube.save_to_json()
    res = solve_from_file(CUBE_STATE_PATH)
    if "error" in res:
        logger.error("Solver retornou erro: %s", res["error"])
        return

    cube.robot.send_moves(res["robot_sequence"])
    cube.robot.last_solution = res["solution"]
    cube.robot.last_move_count = res["move_count"]

    for m in res["solution"].split():
        face = m[0]
        times = 3 if "'" in m else (2 if "2" in m else 1)
        cube.move(face, times, send_serial=False)


def main():
    pygame.init()
    pygame.display.set_mode(RES, DOUBLEBUF | OPENGL)
    pygame.display.set_caption("RobotCube 3D - Unicamp Cube")

    robot = RobotController()
    cube = RubiksCube(robot)
    logo_data = load_logo(LOGO_PATH)

    rot_x, rot_y = 30.0, -30.0
    clock = pygame.time.Clock()

    key_map = {K_r: 'R', K_l: 'L', K_u: 'U', K_d: 'D', K_f: 'F', K_b: 'B'}

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return

            if event.type == KEYDOWN and not robot.is_busy:
                mods = pygame.key.get_mods()
                pressed = pygame.key.get_pressed()
                times = 3 if (mods & KMOD_SHIFT) else (2 if pressed[K_2] else 1)

                if event.key in key_map:
                    cube.move(key_map[event.key], times)
                elif event.key == K_s:
                    open_settings(robot)
                elif event.key == K_x:
                    run_solver(cube)

        # Rotação por arrasto do mouse
        if pygame.mouse.get_pressed()[0]:
            rel = pygame.mouse.get_rel()
            rot_y += rel[0] * 0.4
            rot_x += rel[1] * 0.4
        else:
            pygame.mouse.get_rel()

        cube.update_animation()
        robot.check_for_done()

        # Renderização
        glClearColor(0.12, 0.12, 0.14, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, RES[0] / RES[1], 0.1, 50.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0, 0, -10.0)

        glPushMatrix()
        glRotatef(rot_x, 1, 0, 0)
        glRotatef(rot_y, 0, 1, 0)
        cube.draw()
        glPopMatrix()

        draw_axes_corner(rot_x, rot_y)
        draw_hud(robot, logo_data)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
