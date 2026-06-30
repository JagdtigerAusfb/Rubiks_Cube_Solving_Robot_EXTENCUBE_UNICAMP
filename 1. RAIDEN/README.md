# RAIDEN

**[WORK IN PROGRESS]**

Repository with all the material for **Raiden**, a Rubik's Cube solving robot developed as an extension project at UNICAMP. The goal is to solve the cube using 6 stepper motors (one per face), color sensors to read the cube's state, and an Arduino Mega as the central controller.

## Repository structure

```
1. RAIDEN/
├── 3D Files/              # 3D models of the robot's mechanical structure (in preparation)
├── PCB/                   # Circuit boards (KiCad projects)
│   ├── PCB 3 Drivers/
│   ├── PCB Drivers + Sensores/
│   └── PCB TUPAN/
└── Software/              # Arduino firmware and PC control applications
    ├── arduino/
    ├── Cube3D/
    └── CubeApp/
```

### `3D Files/`
Folder intended for the mechanical structure's 3D modeling files (chassis, motor mounts, base, etc.). For now it only contains the project's original README — the models have not been added yet.

### `PCB/`
KiCad projects for the robot's electronics: the main driver/sensor shield, an earlier 3-driver prototype, and a new board still in early development. See **[PCB/README.md](PCB/README.md)** for board details and pinout.

### `Software/`
All the code that runs the robot: the Arduino firmware (motor driving over serial) and two PC applications — `Cube3D`, an OpenGL viewer/manual control tool, and `CubeApp`, the main PyQt6 app that scans the cube with a camera, solves it, and sends the solution to the robot. See **[Software/README.md](Software/README.md)** for details.
