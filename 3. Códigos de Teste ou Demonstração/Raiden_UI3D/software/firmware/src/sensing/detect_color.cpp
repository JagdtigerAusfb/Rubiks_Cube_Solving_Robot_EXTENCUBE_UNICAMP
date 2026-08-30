#include "sensing.h"

const char COLOR_CHAR[NUM_COLORS] = {'W','R','G','Y','O','B'};

Hsv  globalRef[NUM_COLORS];           // referência global
float whiteBal[3];                    // referência de branco por canal
float whiteSatThresh = 0.15;
char scramble[6][8];                  // "vetorzão": 48 adesivos -> payload STATE

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
    whiteSatThresh = 0.15;
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

// Leitura CRUA de um sensor lógico (mux + read), sem balanço nem normalização.
bool senseRaw(uint8_t ns, float &r, float &g, float &b) {
    if (ns >= NUM_SENSORS) return false;
    muxSelect(MUX_CHANNEL[ns]);
    delay(SENSE_SETTLE_MS);
    unsigned long t0 = millis();
    while (!tcs.available())
        if (millis() - t0 > 200) return false;
    auto col = tcs.color();
    r = col.r; g = col.g; b = col.b;
    if (r + g + b < 5) return false;             // leitura morta/escura
    return true;
}

// Leitura crua de um sensor lógico -> HSV (normalizada por cromaticidade).
// Mesma transformação usada na classificação (consistência calibração<->leitura).
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

static char classifyHsv(const Hsv &m) {
    if (m.s < whiteSatThresh) return 'W';        // branco por saturação (agora confiável)
    uint8_t best = 1; float bd = distHue(m.h, globalRef[1].h);
    for (uint8_t c = 2; c < NUM_COLORS; c++) {
        float dc = distHue(m.h, globalRef[c].h);
        if (dc < bd) { bd = dc; best = c; }
    }
    return COLOR_CHAR[best];
}

char detectColorLogical(uint8_t ns) {
    Hsv m;
    if (!senseHsv(ns, m)) return 'X';
    return classifyHsv(m);
}