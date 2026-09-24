#ifndef SENSING_H
#define SENSING_H
#include <Arduino.h>
#include <Wire.h>
#include "TCS34725.h"                 // lib única (hideakitai)

#define NUM_SENSORS   12
#define NUM_COLORS    6

// Pinos de seleção do mux 74HC4067 (S0..S3). TODO(hw): confirmar.
#define MUX_SEL_0 11
#define MUX_SEL_1 10
#define MUX_SEL_2 9
#define MUX_SEL_3 8

// LEDs individuais — UM GPIO por sensor, indexado por CANAL FÍSICO do mux
// (o LED fica no mesmo módulo TCS34725 que o SDA daquele canal).
extern const uint8_t LED_GPIO[NUM_SENSORS];

void ledOn(uint8_t ns);      // acende o LED do sensor lógico ns
void ledOff(uint8_t ns);     // apaga o LED do sensor lógico ns
void ledAllOff();            // apaga todos

#define SENSE_SETTLE_MS 50            // acomodação após trocar canal (~1 integração)

// Indireção NS lógico (2*face+pos, ordem de contrato) -> canal físico do mux.
extern const uint8_t MUX_CHANNEL[NUM_SENSORS];
// Char de cor por índice (ordem de contrato por face): 0=W 1=R 2=G 3=Y 4=O 5=B.
extern const char COLOR_CHAR[NUM_COLORS];

struct Hsv { float h, s, v; };

extern TCS34725 tcs;                  // instância única (definida em scan.cpp)

// Referência GLOBAL de cor (aplicada a todos os sensores) e matriz de estado.
extern Hsv  globalRef[NUM_COLORS];    // definidos em detect_color.cpp
extern float whiteBal[3]; // resposta do sensor ao branco (von Kries)
extern float whiteSatThresh; // fronteira de saturação branco<->cromáticos
extern char scramble[6][8];
extern const char    FACE_TURN[6];       // N' de cada face (ordem U,R,F,D,L,B)
extern const uint8_t POS[6][2][4];       // [face][papel:0=quina,1=centro][passo] -> índice 0..7


// ---- Fundação ----
void    sensingInit();
void    muxSelect(uint8_t physicalChannel);
uint8_t sensingScan(bool status[NUM_SENSORS]);

// ---- Driver de cor ----
void detectColorLoadDefaults();               // placeholder de globalRef (pré-calibração)
bool senseHsv(uint8_t ns, Hsv &out);          // leitura crua: mux+read+rgb->hsv; false se inválida
char detectColorLogical(uint8_t ns);          // senseHsv + classificação -> W/R/G/Y/O/B/X
// Igual ao detectColorLogical, mas devolve também a razão R/O do adesivo
// (usada pela resolução por peça no sense_complete).
char detectColorLogicalRO(uint8_t ns, float &ratio);
bool senseRaw(uint8_t ns, float &r, float &g, float &b);   // leitura CRUA (sem balanço)

// ---- Calibração ----
int calibrateSolved();                       // 12 leituras (cubo resolvido) -> globalRef

// ---- Sensoriamento ----
int senseComplete();

#endif // SENSING_H