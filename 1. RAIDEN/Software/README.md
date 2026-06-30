# RAIDEN — Software

**[WORK IN PROGRESS]**

This folder contains all the software for our first Rubik's Cube solving robot: the **Raiden**, the Arduino firmware that drives the motors, and two separate Python applications used to control the robot from a PC.

## Repository structure

```
Software/
├── arduino/        # Firmware that runs on the Arduino Mega
├── Cube3D/         # OpenGL 3D viewer + manual/serial control app
└── CubeApp/        # PyQt6 GUI with camera-based cube scanning (main application)
```

### `arduino/arduino.ino`
Firmware for the **Arduino Mega**, controlling the 6 A4988 stepper drivers (one per face: U, R, F, D, L, B). It listens on serial (9600 baud) for a simple text protocol:

- `<START>` — begins a new move sequence
- `<SPEED:n>` — sets the step pulse delay in microseconds
- `<DELAY:n>` — sets the delay between moves in milliseconds
- One line per move, using a single-letter code (`A`–`R`, 3 codes per face: CW, CCW, 180°)
- `<END>` — executes the buffered sequence and replies `DONE <seconds>` when finished

As an optimization, opposite faces (e.g. U/D, F/B, L/R) detected as consecutive moves are driven **simultaneously** (`executarDuplo`) instead of sequentially, reducing total solve time. The `.ino` file must be uploaded manually through the Arduino IDE — it is not flashed automatically by the PC software.

### `Cube3D/`
A OpenGL/Pygame application that renders an interactive 3D Rubik's Cube on screen and can drive the physical robot over serial. This application was made for demonstration purposes and can be used to directly control the motors using a keyboard.

- `main.py` — window/render loop, keyboard controls for manual face rotations
- `cube/rubiks_cube.py` — cube data model and 3D rendering of each cubie
- `cube/solver.py` — wraps the `kociemba` solver and converts its output into the robot's serial move codes
- `robot/controller.py` — serial connection handling (auto-detects COM port) and move dispatch, mirroring the Arduino protocol above
- `ui/hud.py`, `ui/settings.py` — on-screen HUD/overlay and a Tkinter settings window for serial port/speed
- `config.py` — paths, color map, and the Kociemba → robot move-code lookup table
- `data/cube_state.json` — last saved cube state

This appears to be the earlier/prototype tool, used for visualizing and testing moves before the full GUI was built.

### `CubeApp/` — main application
A PyQt6 desktop app that scans the physical cube with a webcam, solves it, and sends the solution to the robot. Pages are stacked in a `QStackedWidget` and flow as:

1. **`ui/cover.py`** — home/control panel: choose solver, set robot speed/delay, trigger solve & send
2. **`ui/calibration.py`** — lets the user position a 3×3 ROI (region of interest) grid over the cube face in the camera feed
3. **`ui/color_calib.py`** — captures reference color samples (HSV/Lab/RGB) for each of the 6 face colors, in the order defined by `COLOR_ORDER`
4. **`ui/capture.py`** — scans all 6 faces using the calibrated ROIs/colors and writes the result to `data/cube_state.json`

Supporting modules:

- `vision/camera.py` — OpenCV ↔ Qt frame conversion and ROI grid overlay
- `vision/classifier.py` — extracts mean HSV/Lab/RGB per cell and classifies it against the calibrated reference colors (nearest-neighbor via Euclidean distance)
- `solver/kociemba.py` — standard two-phase Kociemba solve
- `solver/m2op.py` — alternative M2/OP (blind-solving method) solver
- `solver/utils.py` — shared helpers: move counting, move inversion, and conversion to the robot's serial sequence
- `robot/controller.py` — same role as in `Cube3D`, but reads serial parameters (baud rate, timeouts, init delay) from `config.py`
- `config.py` — paths, color↔face mapping (`COLOR_TO_FACE`), Kociemba→robot `MOVE_TABLE`, and UI/serial defaults (e.g. `SERIAL_INIT_DELAY = 3` — required for the Arduino's DTR reset)

## Requirements

- **Arduino IDE** (or equivalent) to upload `arduino/arduino.ino`
- **Python 3.x**
- On Windows, **Microsoft Visual C++ Build Tools 14+** (required by some packages)

Python dependencies (install with pip):

```
pip install PyQt6 opencv-python numpy pyserial kociemba pygame PyOpenGL PyOpenGL-accelerate
```

| Library | Used for |
|---|---|
| `PyQt6` | GUI windows, layouts and widgets (`CubeApp`) |
| `opencv-python` | Camera capture and color-space conversion (BGR/HSV/Lab) |
| `numpy` | Array math and color-distance calculations |
| `pyserial` | Serial communication with the Arduino over USB |
| `kociemba` | Two-phase Rubik's Cube solving algorithm |
| `pygame` | Window/event loop for `Cube3D` |
| `PyOpenGL` / `PyOpenGL-accelerate` | 3D cube rendering in `Cube3D` |

Credit: solving logic built on top of the open-source [muodov/kociemba](https://github.com/muodov/kociemba) Python module.

## Running it

1. Open `arduino/arduino.ino` in the Arduino IDE and upload it to the Arduino Mega.
2. Install the Python dependencies listed above.
3. Run the main application:
   ```
   python CubeApp/main.py
   ```
4. Calibrate the ROI grid and reference colors (first run only), scan the cube, then solve and send the solution to the robot from the cover page.

`Cube3D/main.py` can be run the same way for the 3D-viewer/manual-control tool, but it expects `data/cube_state.json` to already contain a valid cube state (set externally or via the JSON file).

## Status / notes

- `CubeApp` is the actively developed, full-featured application (camera scanning + two solving methods).
- `Cube3D` looks like an earlier prototype/visualization tool and may be unmaintained going forward.
- `__pycache__` folders are compiled artifacts and are not needed to run or understand the code — safe to delete.
