#include "sensing.h"

// Média circular de HUEs — robusta ao wrap 0/360 (ex.: vermelho ~1.9°).
static float circMeanHue(const float *h, uint8_t n) {
    float sx = 0, sy = 0;
    for (uint8_t i = 0; i < n; i++) { float r = h[i]*DEG_TO_RAD; sx += cos(r); sy += sin(r); }
    float m = atan2(sy, sx) * RAD_TO_DEG;
    if (m < 0) m += 360.0;
    return m;
}

// Calibração simplificada: cubo RESOLVIDO em HOME, SEM movimento.
// Sensor lógico ns está na face ns/2, que (resolvido) mostra a cor de índice
// ns/2. Cada cor recebe 2 amostras (os 2 sensores da face); média circular
// preenche globalRef, aplicado a todos os sensores.
int calibrateSolved() {
    // FASE 1 — balanço de branco a partir da face branca (ns 0,1), em valores CRUS.
    float wr = 0, wg = 0, wb = 0; uint8_t kw = 0;
    for (uint8_t p = 0; p < 2; p++) {
        float r, g, b;
        if (senseRaw(0 + p, r, g, b)) { wr += r; wg += g; wb += b; kw++; }
    }
    if (kw == 0) return 4;                                    // sem leitura na face branca
    whiteBal[0] = wr / kw; whiteBal[1] = wg / kw; whiteBal[2] = wb / kw;
    for (uint8_t i = 0; i < 3; i++) if (whiteBal[i] < 1e-6) return 4;

    // FASE 2 — com o balanço ativo, hue e saturação de cada cor no espaço balanceado.
    for (uint8_t c = 0; c < NUM_COLORS; c++) {
        float hues[2], ssum = 0; uint8_t k = 0;
        for (uint8_t p = 0; p < 2; p++) {
            Hsv m;
            if (senseHsv(2 * c + p, m)) { hues[k] = m.h; ssum += m.s; k++; }
        }
        if (k == 0) return 4;                                // face sem leitura válida
        globalRef[c].h = circMeanHue(hues, k);
        globalRef[c].s = ssum / k;
        globalRef[c].v = 0;
    }

    // Limiar: entre S(branco balanceado) e o cromático menos saturado.
    float minChroma = globalRef[1].s;
    for (uint8_t c = 2; c < NUM_COLORS; c++)
        if (globalRef[c].s < minChroma) minChroma = globalRef[c].s;
    whiteSatThresh = 0.5f * (globalRef[0].s + minChroma);

    // --- Auto-validação das premissas (ver sensor_map.md) ---
    // (1) branco deve ser o menos saturado, com folga sobre o menor cromático.
    if (globalRef[0].s >= 0.5f * minChroma) return 5;        // branco não dessaturou
    // (2) toda cromática precisa de saturação viva (nenhuma cor morta).
    for (uint8_t c = 1; c < NUM_COLORS; c++)
        if (globalRef[c].s < 0.30f) return 5;                // cromática fraca/morta
    // (3) whiteBal coerente: canais na mesma ordem (nenhum destoante ~10x).
    float wmin = whiteBal[0], wmax = whiteBal[0];
    for (uint8_t i = 1; i < 3; i++) { wmin = min(wmin, whiteBal[i]); wmax = max(wmax, whiteBal[i]); }
    if (wmax > 10.0f * wmin) return 5;                       // reflexo na face branca

    return 0;                                                // calibração boa
}