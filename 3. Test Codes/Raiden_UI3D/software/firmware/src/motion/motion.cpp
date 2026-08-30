#include "motion.h"

// --- Pinos por motor (índice 0..5): U, R, F, D, L, B ---------------------
struct MotorPins { uint8_t dir; uint8_t step; uint8_t enable; };
static const MotorPins MOTORS[6] = {
    {45, 44, A11},  // 0 = U
    {43, 42, A12},  // 1 = R
    {49, 48, A15},  // 2 = F
    {51, 50, A14},  // 3 = D
    {A0, A1, A13},  // 4 = L
    {47, 46, A10},  // 5 = B
};

// --- LUT de movimentos: índice = char - 'A' (0..17) ----------------------
// Cada char roteia para o motor da SUA face (contracts/move_alphabet.md),
// usando os índices físicos do array MOTORS (0=U 1=R 2=F 3=D 4=L 5=B).
// 50 passos = 90°, 100 passos = 180°. dir HIGH = anti-horário (').
struct MoveEntry { uint8_t motor; uint8_t dir; uint16_t steps; };
static const MoveEntry MOVES[18] = {
    {0, LOW, 50}, {0, HIGH, 50}, {0, LOW, 100},  // A B C -> U  U'  U2  (motor 0)
    {3, LOW, 50}, {3, HIGH, 50}, {3, LOW, 100},  // D E F -> D  D'  D2  (motor 3)
    {4, LOW, 50}, {4, HIGH, 50}, {4, LOW, 100},  // G H I -> L  L'  L2  (motor 4)
    {1, LOW, 50}, {1, HIGH, 50}, {1, LOW, 100},  // J K L -> R  R'  R2  (motor 1)
    {2, LOW, 50}, {2, HIGH, 50}, {2, LOW, 100},  // M N O -> F  F'  F2  (motor 2)
    {5, LOW, 50}, {5, HIGH, 50}, {5, LOW, 100},  // P Q R -> B  B'  B2  (motor 5)
};

static uint16_t stepDelayUs = 1000;
static uint16_t moveGapMs   = 10;

void motionSetStepDelay(uint16_t us) { stepDelayUs = us; }
void motionSetMoveGap(uint16_t ms)   { moveGapMs = ms; }
bool motionIsValid(char c)           { return c >= 'A' && c <= 'R'; }

void motionInit() {
    for (uint8_t i = 0; i < 6; i++) {
        pinMode(MOTORS[i].enable, OUTPUT);
        digitalWrite(MOTORS[i].enable, HIGH);   // A4988 enable é ativo-baixo: HIGH = desligado
        pinMode(MOTORS[i].dir,  OUTPUT);
        pinMode(MOTORS[i].step, OUTPUT);
    }
}

static void driveSingle(const MoveEntry& m) {
    digitalWrite(MOTORS[m.motor].enable, LOW);
    digitalWrite(MOTORS[m.motor].dir, m.dir);
    for (uint16_t i = 0; i < m.steps; i++) {
        digitalWrite(MOTORS[m.motor].step, HIGH);
        delayMicroseconds(stepDelayUs);
        digitalWrite(MOTORS[m.motor].step, LOW);
        delayMicroseconds(stepDelayUs);
    }
    digitalWrite(MOTORS[m.motor].enable, HIGH);
}

static void drivePair(const MoveEntry& a, const MoveEntry& b) {
    digitalWrite(MOTORS[a.motor].enable, LOW);
    digitalWrite(MOTORS[b.motor].enable, LOW);
    digitalWrite(MOTORS[a.motor].dir, a.dir);
    digitalWrite(MOTORS[b.motor].dir, b.dir);
    uint16_t maxSteps = max(a.steps, b.steps);
    for (uint16_t i = 0; i < maxSteps; i++) {
        if (i < a.steps) digitalWrite(MOTORS[a.motor].step, HIGH);
        if (i < b.steps) digitalWrite(MOTORS[b.motor].step, HIGH);
        delayMicroseconds(stepDelayUs);
        if (i < a.steps) digitalWrite(MOTORS[a.motor].step, LOW);
        if (i < b.steps) digitalWrite(MOTORS[b.motor].step, LOW);
        delayMicroseconds(stepDelayUs);
    }
    digitalWrite(MOTORS[a.motor].enable, HIGH);
    digitalWrite(MOTORS[b.motor].enable, HIGH);
}

// Faces fisicamente opostas: (U,D)=(0,3), (R,L)=(1,4), (F,B)=(2,5).
static bool areOpposite(char x, char y) {
    if (!motionIsValid(x) || !motionIsValid(y)) return false;
    uint8_t a = MOVES[x - 'A'].motor, b = MOVES[y - 'A'].motor;
    uint8_t lo = min(a, b), hi = max(a, b);
    return (lo == 0 && hi == 3) || (lo == 1 && hi == 4) || (lo == 2 && hi == 5);
}

void motionExecute(char c) {
    if (!motionIsValid(c)) return;
    driveSingle(MOVES[c - 'A']);
    delay(moveGapMs);
}

unsigned long motionExecuteSequence(const char* seq, int len) {
    unsigned long t0 = micros();
    for (int i = 0; i < len; i++) {
        if (!motionIsValid(seq[i])) continue;
        if (i + 1 < len && areOpposite(seq[i], seq[i + 1])) {
            drivePair(MOVES[seq[i] - 'A'], MOVES[seq[i + 1] - 'A']);
            delay(moveGapMs);
            i++;                                 // consumiu o par
        } else {
            driveSingle(MOVES[seq[i] - 'A']);
            delay(moveGapMs);
        }
    }
    return micros() - t0;
}