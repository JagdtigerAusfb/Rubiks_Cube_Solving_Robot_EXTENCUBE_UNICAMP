#include "sensing.h"
#include "../motion/motion.h"

// N' (anti-horário) de cada face — ordem canônica U,R,F,D,L,B.
const char FACE_TURN[6] = {'B','K','N','E','H','Q'};

// POS[face][papel][passo] -> índice canônico 0..7 onde gravar.
const uint8_t POS[6][2][4] = {
    /* U */ { {0,2,4,6}, {1,3,5,7} },
    /* R */ { {0,2,4,6}, {1,3,5,7} },
    /* F */ { {0,2,4,6}, {1,3,5,7} },
    /* D */ { {6,0,2,4}, {7,1,3,5} },
    /* L */ { {0,2,4,6}, {1,3,5,7} },
    /* B */ { {0,2,4,6}, {1,3,5,7} },
};

// Razão R/O de cada adesivo lido (mesma indexação do scramble).
static float roRatio[6][8];

// ---------------------------------------------------------------------------
// Peças do cubo na indexação {face, pos horária}. Geradas das definições do
// Kociemba. Quinas em ordem horária (a quiralidade fixa a 3ª cor).
// ---------------------------------------------------------------------------
static const uint8_t CORNER_FP[8][3][2] = {
    { {0,4}, {1,0}, {2,2} },   // W-R-G
    { {0,6}, {2,0}, {4,2} },   // W-G-O
    { {0,0}, {4,0}, {5,2} },   // W-O-B
    { {0,2}, {5,0}, {1,2} },   // W-B-R
    { {3,2}, {2,4}, {1,6} },   // Y-G-R
    { {3,0}, {4,4}, {2,6} },   // Y-O-G
    { {3,6}, {5,4}, {4,6} },   // Y-B-O
    { {3,4}, {1,4}, {5,6} },   // Y-R-B
};
static const char CORNER_COL[8][3] = {
    {'W','R','G'}, {'W','G','O'}, {'W','O','B'}, {'W','B','R'},
    {'Y','G','R'}, {'Y','O','G'}, {'Y','B','O'}, {'Y','R','B'},
};
static const uint8_t EDGE_FP[12][2][2] = {
    { {0,3}, {1,1} }, { {0,5}, {2,1} }, { {0,7}, {4,1} }, { {0,1}, {5,1} },
    { {3,3}, {1,5} }, { {3,1}, {2,5} }, { {3,7}, {4,5} }, { {3,5}, {5,5} },
    { {2,3}, {1,7} }, { {2,7}, {4,3} }, { {5,3}, {4,7} }, { {5,7}, {1,3} },
};

static inline bool isRO(char c) { return c == 'R' || c == 'O'; }

// Quinas: com as 2 cores confiáveis e suas posições, a quiralidade determina
// se a 3ª é R ou O. Não usa a razão.
static void resolveCorners() {
    for (uint8_t i = 0; i < 8; i++) {
        char col[3]; int8_t amb = -1; uint8_t nAmb = 0;
        for (uint8_t k = 0; k < 3; k++) {
            col[k] = scramble[CORNER_FP[i][k][0]][CORNER_FP[i][k][1]];
            if (isRO(col[k])) { amb = k; nAmb++; }
        }
        if (nAmb != 1) continue;                     // quina sem ambiguidade (ou leitura estranha)
        bool done = false;
        for (uint8_t t = 0; t < 8 && !done; t++) {
            for (uint8_t rot = 0; rot < 3 && !done; rot++) {
                bool ok = true;
                for (uint8_t k = 0; k < 3; k++) {
                    if ((int8_t)k == amb) continue;
                    if (CORNER_COL[t][(k + rot) % 3] != col[k]) { ok = false; break; }
                }
                char cand = CORNER_COL[t][(amb + rot) % 3];
                if (ok && isRO(cand)) {
                    scramble[CORNER_FP[i][amb][0]][CORNER_FP[i][amb][1]] = cand;
                    done = true;
                }
            }
        }
    }
}

// Arestas: cada cor confiável (W,Y,G,B) aparece em 2 arestas R/O, uma com R e
// outra com O. Entre as duas, a de maior razão é laranja.
static void resolveEdges() {
    const char PARTNER[4] = {'W','Y','G','B'};
    for (uint8_t p = 0; p < 4; p++) {
        uint8_t fs[2], ps[2], n = 0;
        for (uint8_t e = 0; e < 12; e++) {
            uint8_t f0 = EDGE_FP[e][0][0], q0 = EDGE_FP[e][0][1];
            uint8_t f1 = EDGE_FP[e][1][0], q1 = EDGE_FP[e][1][1];
            char a = scramble[f0][q0], b = scramble[f1][q1];
            if (isRO(a) && b == PARTNER[p]) { if (n < 2) { fs[n] = f0; ps[n] = q0; } n++; }
            else if (isRO(b) && a == PARTNER[p]) { if (n < 2) { fs[n] = f1; ps[n] = q1; } n++; }
        }
        if (n != 2) continue;                        // grupo inconsistente: não mexe
        bool firstIsO = roRatio[fs[0]][ps[0]] > roRatio[fs[1]][ps[1]];
        scramble[fs[0]][ps[0]] = firstIsO ? 'O' : 'R';
        scramble[fs[1]][ps[1]] = firstIsO ? 'R' : 'O';
    }
}

// Lê cada face inteira usando só rotações da própria face; ao final, resolve
// R/O por peça (quiralidade das quinas + pares de arestas).
int senseComplete() {
    int invalid = 0;
    for (uint8_t f = 0; f < 6; f++) {
        uint8_t nsQ = 2 * f;
        uint8_t nsC = 2 * f + 1;
        for (uint8_t k = 0; k < 4; k++) {
            float rq, rcen;
            char cq = detectColorLogicalRO(nsQ, rq);
            char cc = detectColorLogicalRO(nsC, rcen);
            if (cq == 'X') invalid++;
            if (cc == 'X') invalid++;
            scramble[f][ POS[f][0][k] ] = cq;
            scramble[f][ POS[f][1][k] ] = cc;
            roRatio[f][ POS[f][0][k] ] = rq;
            roRatio[f][ POS[f][1][k] ] = rcen;
            motionExecute(FACE_TURN[f]);
            _delay_ms(100);
        }
    }
    if (invalid == 0) {
        resolveCorners();
        resolveEdges();
    }
    return invalid;
}