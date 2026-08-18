#include <Arduino.h>
#include "motion/motion.h"
#include "sensing/sensing.h" 

static const uint32_t BAUD = 115200;   // deve casar com host/app/communication/embedded.py
static const char TERM = '*';

static char rx[400];                    // Vetor RX Obs: cabe M2OP (200–300 movimentos) + folga
static int  rxLen = 0;

static void handleCommand(char* cmd, int n) {
    if (n <= 0) { Serial.print("e0*"); return; }

    // --- Comandos de subsistema  --- //
     if (cmd[0] == 'c' && cmd[1] == '0') {           // CALIBRATE
        int rc = calibrateSolved();
        if (rc == 4) { Serial.print("e4*"); return; }
        if (rc == 5) { Serial.print("e5*"); return; }
        for (uint8_t c = 0; c < NUM_COLORS; c++) { Serial.print(globalRef[c].h, 1); Serial.print('_'); }
        for (uint8_t c = 0; c < NUM_COLORS; c++) { Serial.print(globalRef[c].s, 3); Serial.print('_'); }
        Serial.print(whiteSatThresh, 3); Serial.print('_');
        Serial.print(whiteBal[0], 0); Serial.print('_');
        Serial.print(whiteBal[1], 0); Serial.print('_');
        Serial.print(whiteBal[2], 0);
        Serial.print(TERM);
        return;
    }
    if (cmd[0] == 's' && cmd[1] == '0') {           // SCAN
        bool status[NUM_SENSORS];
        sensingScan(status);
        for (uint8_t i = 0; i < NUM_SENSORS; i++)
            Serial.print(status[i] ? '1' : '0');
        Serial.print(TERM);
        return;
    }
    if (cmd[0] == 'k' && cmd[1] == '_') {           // KOLOR: lê 1 sensor lógico
        int ns = atoi(cmd + 2);
        if (ns < 0 || ns >= NUM_SENSORS) { Serial.print("e3*"); return; }
        char col = detectColorLogical((uint8_t)ns);
        Serial.print(col); Serial.print(TERM);      // ex.: W*  (ou X* se inválida)
        return;
    }
    if (cmd[0] == 'r' && cmd[1] == '0') {           // SENSE
        int bad = senseComplete();
        if (bad > 0) { Serial.print("e6*"); return; }     // leitura incompleta
        for (uint8_t f = 0; f < 6; f++)                    // STATE: 48 chars,
            for (uint8_t p = 0; p < 8; p++)                // ordem canônica URFDLB,
                Serial.print(scramble[f][p]);              // posição 0..7 por face
        Serial.print(TERM);
        return;
    }

    // --- Config opcional (stress test de velocidade) ---
    if (cmd[0] == 'v' && cmd[1] == '_') { motionSetStepDelay(atoi(cmd + 2)); Serial.print("d*"); return; }
    if (cmd[0] == 'g' && cmd[1] == '_') { motionSetMoveGap(atoi(cmd + 2));   Serial.print("d*"); return; }

    // --- Caso geral: sequência de 1..N movimentos A–R ---
    for (int i = 0; i < n; i++)
        if (!motionIsValid(cmd[i])) { Serial.print("e1*"); return; }

    unsigned long us = motionExecuteSequence(cmd, n);
    Serial.print("d_");                 // 'd' + arg opcional com o tempo (host pode ignorar)
    Serial.print(us / 1000000.0, 3);
    Serial.print(TERM);
}

void setup() {
    Serial.begin(BAUD);
    motionInit();
    sensingInit();
    detectColorLoadDefaults(); 
    Serial.print("READY*");
}

void loop() {
    while (Serial.available()) {
        char ch = (char)Serial.read();
        if (ch == '\r' || ch == '\n') continue;
        if (ch == TERM) {
            rx[rxLen] = '\0';
            handleCommand(rx, rxLen);
            rxLen = 0;
        } else if (rxLen < (int)sizeof(rx) - 1) {
            rx[rxLen++] = ch;
        } else {
            rxLen = 0;
            Serial.print("e2*");        // overflow de linha
        }
    }
}