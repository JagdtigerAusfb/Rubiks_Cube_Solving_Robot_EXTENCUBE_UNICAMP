#include "sensing.h"
#include "../motion/motion.h"

// N' (anti-horário) de cada face — ordem canônica U,R,F,D,L,B.
// Contrato: U'=B  R'=K  F'=N  D'=E  L'=H  B'=Q
const char FACE_TURN[6] = {'B','K','N','E','H','Q'};

// POS[face][papel][passo] -> índice canônico 0..7 onde gravar.
// papel: 0=quina, 1=centro. Regra: (início_HOME + 2*passo) % 8.
const uint8_t POS[6][2][4] = {
    /* U */ { {4,6,0,2}, {5,7,1,3} },
    /* R */ { {0,2,4,6}, {1,3,5,7} },
    /* F */ { {0,2,4,6}, {1,3,5,7} },
    /* D */ { {6,0,2,4}, {7,1,3,5} },
    /* L */ { {0,2,4,6}, {1,3,5,7} },
    /* B */ { {0,2,4,6}, {1,3,5,7} },
};

// Lê cada face inteira (8 casas) usando SÓ rotações da própria face, antes de
// passar à próxima. 4x N' por face devolve o cubo ao embaralhamento original.
int senseComplete() {
    int invalid = 0;
    for (uint8_t f = 0; f < 6; f++) {
        uint8_t nsQ = 2 * f;         // quina  = NS lógico 2f
        uint8_t nsC = 2 * f + 1;     // centro = NS lógico 2f+1
        for (uint8_t k = 0; k < 4; k++) {
            char cq = detectColorLogical(nsQ);
            char cc = detectColorLogical(nsC);
            if (cq == 'X') invalid++;
            if (cc == 'X') invalid++;
            scramble[f][ POS[f][0][k] ] = cq;
            scramble[f][ POS[f][1][k] ] = cc;
            motionExecute(FACE_TURN[f]);   // N' 90°; após 4x, face restaurada
        }
    }
    return invalid;
}