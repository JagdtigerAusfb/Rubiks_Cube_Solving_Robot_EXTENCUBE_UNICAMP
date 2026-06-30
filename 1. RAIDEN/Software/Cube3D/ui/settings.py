import logging

import pygame

logger = logging.getLogger(__name__)


def open_settings(robot):
    """Abre a janela de configurações da conexão serial."""
    import tkinter as tk

    root = tk.Tk()
    root.title("Configurations")

    tk.Label(root, text="Port COM:").grid(row=0, column=0, padx=10, pady=5)
    port_entry = tk.Entry(root)
    port_entry.insert(0, robot.port if robot.port else "")
    port_entry.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(root, text="Speed:").grid(row=1, column=0, padx=10, pady=5)
    speed_entry = tk.Entry(root)
    speed_entry.insert(0, str(robot.speed))
    speed_entry.grid(row=1, column=1, padx=10, pady=5)

    tk.Label(root, text="Delay (ms):").grid(row=2, column=0, padx=10, pady=5)
    delay_entry = tk.Entry(root)
    delay_entry.insert(0, str(robot.delay))
    delay_entry.grid(row=2, column=1, padx=10, pady=5)

    def apply():
        p = port_entry.get().strip()
        if p and p != robot.port:
            success = robot.connect(p)
            if not success:
                logger.warning("Falha ao conectar na porta %s", p)

        try:
            robot.speed = int(speed_entry.get())
        except ValueError:
            logger.warning("Valor de speed inválido, mantendo %d", robot.speed)

        try:
            robot.delay = int(delay_entry.get())
        except ValueError:
            logger.warning("Valor de delay inválido, mantendo %d", robot.delay)

        root.destroy()
        pygame.event.clear()

    tk.Button(root, text="OK", command=apply).grid(row=3, column=0, columnspan=2, pady=10)

    # Centraliza a janela na tela
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w // 2) - (w // 2)
    y = (screen_h // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")

    root.mainloop()
