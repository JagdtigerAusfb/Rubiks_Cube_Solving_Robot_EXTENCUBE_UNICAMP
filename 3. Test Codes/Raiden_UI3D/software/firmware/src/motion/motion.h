#ifndef MOTION_H
#define MOTION_H
#include <Arduino.h>

// Primitiva de motor — compartilhada por sensing/ e pelo fluxo de execução.
// Mapeia o alfabeto A–R (contracts/move_alphabet.md) em passos dos 6 A4988.

void motionInit();                         // pinModes + desabilita todos os motores
void motionSetStepDelay(uint16_t us);      // meio-período do pulso STEP (velocidade)
void motionSetMoveGap(uint16_t ms);        // pausa após cada movimento

bool motionIsValid(char c);                // c ∈ 'A'..'R'
void motionExecute(char c);                // UM movimento (usado pelo sensing)

// Sequência de chars A–R com otimização de faces opostas (dois motores
// simultâneos). Retorna o tempo decorrido em microssegundos.
unsigned long motionExecuteSequence(const char* seq, int len);

#endif // MOTION_H
