#include "sensing.h"

TCS34725 tcs;                                 // instância única compartilhada

// NS lógico (2*face+pos) -> canal físico (fiação real, imutável).
const uint8_t MUX_CHANNEL[NUM_SENSORS] = {2,3, 4,5, 6,7, 10,11, 8,9, 0,1};

void sensingInit() {
    Wire.begin();
    pinMode(MUX_SEL_0, OUTPUT); pinMode(MUX_SEL_1, OUTPUT);
    pinMode(MUX_SEL_2, OUTPUT); pinMode(MUX_SEL_3, OUTPUT);
    pinMode(LED_PIN, OUTPUT); digitalWrite(LED_PIN, HIGH);   // LEDs ligados (conjunto)

    // Configura cada sensor físico uma vez (integração + ganho como no driver validado).
    for (uint8_t ch = 0; ch < NUM_SENSORS; ch++) {
        muxSelect(ch);
        delay(5);
        if (tcs.attach(Wire)) {
            tcs.integrationTime(50);
            tcs.gain(TCS34725::Gain::X01);
        }
    }
}

void muxSelect(uint8_t ch) {
    digitalWrite(MUX_SEL_0,  ch       & 0x01);
    digitalWrite(MUX_SEL_1, (ch >> 1) & 0x01);
    digitalWrite(MUX_SEL_2, (ch >> 2) & 0x01);
    digitalWrite(MUX_SEL_3, (ch >> 3) & 0x01);
}

// Self-check por CANAL FÍSICO (0..11). status[i] = canal físico i respondeu.
uint8_t sensingScan(bool status[NUM_SENSORS]) {
    uint8_t fails = 0;
    for (uint8_t ch = 0; ch < NUM_SENSORS; ch++) {
        muxSelect(ch);
        delay(5);
        bool ok = tcs.attach(Wire);   // presença via re-attach
        status[ch] = ok;
        if (!ok) fails++;
    }
    return fails;
}