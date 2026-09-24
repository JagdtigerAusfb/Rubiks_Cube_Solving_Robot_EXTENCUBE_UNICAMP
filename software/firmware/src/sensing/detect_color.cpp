#include "sensing.h"

#define RO_RATIO_THRESH 11.0f    // (r-g-b)/b sobre RGB CRU: < 6 = vermelho, >= 6 = laranja

const char COLOR_CHAR[NUM_COLORS] = {'W','R','G','Y','O','B'};

Hsv   globalRef[NUM_COLORS];          // referência global
float whiteBal[3];                    // referência de branco por canal
float whiteSatThresh = 0.2;
char  scramble[6][8];                 // "vetorzão": 48 adesivos -> payload STATE

// HUEs validados na bancada — usados só como PLACEHOLDER até a calibração.
static const float DEFAULT_HUE[NUM_COLORS] = {
    /*W*/ 101.0, /*R*/ 1.88, /*G*/ 128.0, /*Y*/ 60.0, /*O*/ 7.0, /*B*/ 199.0
};

void detectColorLoadDefaults() {
    whiteBal[0] = whiteBal[1] = whiteBal[2] = 1.0;   // balanço neutro até calibrar
    for (uint8_t c = 0; c < NUM_COLORS; c++) {
        globalRef[c].h = DEFAULT_HUE[c];
        globalRef[c].s = 0; globalRef[c].v = 0;
    }
    whiteSatThresh = 0.2;
}

static void rgbToHsv(float r, float g, float b, float &h, float &s, float &v) {
    float maxc = max(r, max(g, b)), minc = min(r, min(g, b)), d = maxc - minc;
    v = maxc;
    if (maxc == 0) { s = 0; h = 0; return; }
    s = d / maxc;
    if (d == 0) h = 0;
    else if (maxc == r) h = 60.0 * fmod(((g - b) / d), 6);
    else if (maxc == g) h = 60.0 * (((b - r) / d) + 2);
    else                h = 60.0 * (((r - g) / d) + 4);
    if (h < 0) h += 360.0;
}

static float distHue(float a, float b) {
    float dd = fabs(a - b);
    return min(dd, 360.0f - dd);
}

// Leitura CRUA de um sensor lógico (mux + LED individual + read).
/*
bool senseRaw(uint8_t ns, float &r, float &g, float &b) {
    if (ns >= NUM_SENSORS) return false;
    muxSelect(MUX_CHANNEL[ns]);
    ledOn(ns);                      // acende SÓ este LED; vizinhos apagados
    delay(50);
    delay(SENSE_SETTLE_MS);         // luz estabiliza + integração sob luz nova
    tcs.color();                    // descarta 1 leitura (integrou durante a subida do LED)
    unsigned long t0 = millis();
    bool ok = false;
    while (millis() - t0 <= 300) {
        if (tcs.available()) { ok = true; break; }
    }
    if (ok) { auto col = tcs.color(); r = col.r; g = col.g; b = col.b; }
    ledOff(ns);                     // apaga antes de sair
    if (!ok || (r + g + b) < 5) return false;
    delay(50);
    return true;
}
*/

bool senseRaw(uint8_t ns, float &r, float &g, float &b) {
    if (ns >= NUM_SENSORS) return false;
    muxSelect(MUX_CHANNEL[ns]);
    ledOn(ns);
    delay(50);
    delay(SENSE_SETTLE_MS);
    tcs.color();                    // descarta 1 leitura
    unsigned long t0 = millis();
    bool ok = false;
    while (millis() - t0 <= 300) {
        if (tcs.available()) { ok = true; break; }
    }
    if (ok) { auto col = tcs.color(); r = col.r; g = col.g; b = col.b; }
    ledOff(ns);

    // --- DBG: RGB cru + razão R/O, nas MESMAS condições de operação ---
    if (ok) {
        float divB = (b < 1.0f) ? 1.0f : b;
        float ratio = (r - g - b) / divB;
        Serial.print("  [DBG ns="); Serial.print(ns);
        Serial.print(" ch="); Serial.print(MUX_CHANNEL[ns]);
        Serial.print(" rgb="); Serial.print((int)r); Serial.print(",");
        Serial.print((int)g); Serial.print(","); Serial.print((int)b);
        Serial.print(" soma="); Serial.print((int)(r + g + b));
        Serial.print(" ratioRO="); Serial.println(ratio, 2);   // <-- a razão do desempate
    } else {
        Serial.print("  [DBG ns="); Serial.print(ns);
        Serial.print(" ch="); Serial.print(MUX_CHANNEL[ns]);
        Serial.println(" -> TIMEOUT]");
    }

    delay(50);
    if (!ok || (r + g + b) < 5) return false;
    return true;
}

/*
bool senseRaw(uint8_t ns, float &r, float &g, float &b) {
    if (ns >= NUM_SENSORS) return false;
    muxSelect(MUX_CHANNEL[ns]);
    delay(SENSE_SETTLE_MS);
    unsigned long t0 = millis();
    while (!tcs.available()) {
        if (millis() - t0 > 200) {
            Serial.print("  [DBG ns="); Serial.print(ns);
            Serial.print(" ch="); Serial.print(MUX_CHANNEL[ns]);
            Serial.println(" -> TIMEOUT available]");   // <-- sensor nao respondeu
            return false;
        }
    }
    auto col = tcs.color();
    r = col.r; g = col.g; b = col.b;
    Serial.print("  [DBG ns="); Serial.print(ns);
    Serial.print(" ch="); Serial.print(MUX_CHANNEL[ns]);
    Serial.print(" rgb="); Serial.print((int)r); Serial.print(",");
    Serial.print((int)g); Serial.print(","); Serial.print((int)b);
    Serial.print(" soma="); Serial.println((int)(r+g+b));       // <-- leu, mas valor?
    if (r + g + b < 5) return false;
    return true;
}
*/

// Leitura -> HSV (normalizada por cromaticidade, sobre RGB BALANCEADO).
// Assinatura de 2 args PRESERVADA: é a que o calibration.cpp usa. NÃO alterar.
bool senseHsv(uint8_t ns, Hsv &out) {
    float r, g, b;
    if (!senseRaw(ns, r, g, b)) return false;
    r /= whiteBal[0]; g /= whiteBal[1]; b /= whiteBal[2];   // von Kries
    float soma = r + g + b;
    if (soma < 1e-6) return false;
    r /= soma; g /= soma; b /= soma;
    rgbToHsv(r, g, b, out.h, out.s, out.v);
    return true;
}

// Variante para a classificação: mesmo HSV do senseHsv, mas devolve TAMBÉM o
// RGB CRU (antes do balanço) para o desempate R/O por razão de canais.
static bool senseHsvRGB(uint8_t ns, Hsv &out, float &rc, float &gc, float &bc) {
    float r, g, b;
    if (!senseRaw(ns, r, g, b)) return false;
    rc = r; gc = g; bc = b;                                 // guarda o CRU
    r /= whiteBal[0]; g /= whiteBal[1]; b /= whiteBal[2];   // von Kries
    float soma = r + g + b;
    if (soma < 1e-6) return false;
    r /= soma; g /= soma; b /= soma;
    rgbToHsv(r, g, b, out.h, out.s, out.v);
    return true;
}

// Classifica por hue; desempata R/O pela razão sobre RGB CRU (r,g,b crus).
static char classifyHsv(const Hsv &m, float r, float g, float b) {
    if (m.s < whiteSatThresh) return 'W';

    uint8_t best = 1; float bd = distHue(m.h, globalRef[1].h);
    for (uint8_t c = 2; c < NUM_COLORS; c++) {
        float dc = distHue(m.h, globalRef[c].h);
        if (dc < bd) { bd = dc; best = c; }
    }
    char cor = COLOR_CHAR[best];

    // Desempate R/O: hue quase não separa (~19°); a razão de canais separa.
    // Vermelho: razão baixa. Laranja: razão alta (reflete menos azul).
    if (cor == 'R' || cor == 'O') {
        float divB = (b < 1.0f) ? 1.0f : b;          // evita div/0
        float ratio = (r - g - b) / divB;
        cor = (ratio < RO_RATIO_THRESH) ? 'R' : 'O';
    }
    return cor;
}

char detectColorLogical(uint8_t ns) {
    Hsv m;
    float rc, gc, bc;
    if (!senseHsvRGB(ns, m, rc, gc, bc)) return 'X';
    return classifyHsv(m, rc, gc, bc);
}

char detectColorLogicalRO(uint8_t ns, float &ratio) {
    Hsv m;
    float rc, gc, bc;
    ratio = 0.0f;
    if (!senseHsvRGB(ns, m, rc, gc, bc)) return 'X';
    float divB = (bc < 1.0f) ? 1.0f : bc;
    ratio = (rc - gc - bc) / divB;
    return classifyHsv(m, rc, gc, bc);
}