# RAIDEN

**[WORK IN PROGRESS]**

Repository with all the hardware material for **Raiden**, a Rubik's Cube solving robot developed as an extension project at UNICAMP. The goal is to solve the cube using 6 stepper motors (one per face), color sensors to read the cube's state, and an Arduino Mega as the central controller.

## Repository structure

```
1. RAIDEN/
├── 3D Files/              # 3D models of the robot's mechanical structure (in preparation)
└── PCB/                   # Circuit boards (KiCad projects)
    ├── PCB 3 Drivers/
    ├── PCB Drivers + Sensores/
    └── PCB TUPAN/
```

### `3D Files/`
Folder intended for the mechanical structure's 3D modeling files (chassis, motor mounts, base, etc.). For now it only contains the project's original README — the models have not been added yet.

### `PCB/PCB Drivers + Sensores/` — **Main board**
Shield for the **Arduino Mega**, responsible for all the power delivery and sensor reading in the robot:

- **6x A4988 stepper motor drivers** (Pololu modules), one for each face of the cube
- **12x connectors for TCS34725 color sensors**
- **1x CD74HC4067 multiplexer** to manage the 12 I²C sensor inputs
- 2x 12 V DC jack connectors (redundant power supply; using both is recommended to avoid voltage drops and motor stalling)
- Indicator LEDs (per driver and per power rail) and a reset button — both optional
- Decoupling capacitors on the drivers — **strongly recommended**, even though optional

The folder includes the complete KiCad project (schematic, PCB, custom footprints), fabrication files (Gerber, drill, BOM, component positions in `production/`), and the board's 3D model (`.step`). The folder's own README details the full pinout for the drivers, sensors and multiplexer, along with important warnings about the Arduino connectors and about TCS34725 versions that must not be connected to 5 V.

### `PCB/PCB 3 Drivers/`
A simpler board with only **3 A4988 drivers**, made before the definitive board (Drivers + Sensores) was finished. It's an intermediate alternative/prototype, not required for the final project — according to the author, "use it if you want, or don't, I don't care."

### `PCB/PCB TUPAN/`
Board in an early stage of development. Contains only the `.kicad_pcb` file, still empty (no schematic and no placed components). It appears to be the next planned revision/board for the project, not yet actually started.

## Reference pinout (Drivers + Sensores board)

**A4988 drivers** (DIR / STEP / ENABLE pins):

| Driver | DIR | STEP | ENABLE |
|---|---|---|---|
| 1 | A0 | A1 | A2 |
| 2 | A3 | A4 | A5 |
| 3 | A6 | A7 | A8 |
| 4 | 53 | 51 | 49 |
| 5 | 43 | 41 | 39 |
| 6 | 29 | 27 | 25 |

Microstepping pins (MS) are left disconnected, and RESET/SLEEP are tied together — this only works because the drivers used have internal pull-up/pull-down resistors.

**TCS34725 sensors** (LED control pin on the Arduino): 13, 12, 11, 10, 9, 8, 14, 15, 16, 17, 18, 19 (sensors 1 through 12, respectively).

**CD74HC4067 multiplexer** (selection): S0=5, S1=4, S2=3, S3=2. Inputs C0–C11 connected to signals SDA_1 through SDA_12.

Full details, hardware notes and caveats are in each PCB subfolder's own README.
