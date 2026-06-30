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
Folder intended for the mechanical structure's 3D modeling files (chassis, motor mounts, base, etc.). See **[PCB/README.md](3D/README.md)** for details on the files.

### `PCB/`
KiCad projects for the robot's Printed Circuit Board desgins. See **[PCB/README.md](PCB/README.md)** for board details and pinout.

### `Software/`
All the code that runs the robot: the Arduino firmware and Python files. See **[Software/README.md](Software/README.md)** for details.
