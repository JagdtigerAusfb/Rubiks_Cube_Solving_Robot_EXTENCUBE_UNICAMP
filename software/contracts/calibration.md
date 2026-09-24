# Guia de Calibração e Ajuste dos Sensores

Mapa dos pontos de ajuste do sensoriamento, por **sintoma** e por **onde mexer**.
Companion de `sensor_map.md`. Regra de ouro: o sintoma diz a camada — não mexa
em tudo de uma vez.

---

## Diagnóstico rápido (sintoma → camada)

| Sintoma observado | Causa provável | Camada | Onde mexer |
|-------------------|----------------|--------|------------|
| Confunde cores **vizinhas** (ex.: R↔O) | referência de cor colada | 2 | recalibrar (`c0*`) |
| Branco vira amarelo / `S(W)` alto | branco satura / balanço ruim | 1 + 2 | `integrationTime`, recalibrar |
| Leitura instável ou `X` intermitente | settle curto / ruído I2C | 1 | `SENSE_SETTLE_MS`, timeout |
| `X` sempre no mesmo sensor | contato/solda | — | **hardware**, não código |
| Azul lê morto (`soma`~0) | pouca luz no escuro | 1 | subir `integrationTime` |
| Cores nos **lugares** trocados (3/3 vira 4/2) | índice de gravação | 5 | `POS` em `sense_complete.cpp` |
| Calibração recusada (`e4`/`e5`) | premissa violada | 4 | recalibrar ou afrouxar limiar |

> **Atenção:** cor nos lugares trocados **NÃO** é calibração — é `POS` (Camada 5).
> Não mexa em parâmetro de sensor para isso.

---

## Camada 1 — Parâmetros do sensor (aquisição óptica)

**Arquivo:** `firmware/src/sensing/scan.cpp` → função `sensingInit()`

```cpp
tcs.integrationTime(33);          // ms — principal ajuste de qualidade
tcs.gain(TCS34725::Gain::X01);    // ganho analógico
```

| Parâmetro | Efeito | Faixa útil | Quando mexer |
|-----------|--------|------------|--------------|
| `integrationTime` | maior = mais luz/estável/brilhante; menor = mais rápido, branco não satura | 24–50 ms | azul morto → subir; branco satura → descer |
| `gain` | X01→X60; maior clareia cores escuras, arrisca saturar claras | X01 (default) | subir só se azul continuar fraco com integração alta |

**Arquivo:** `firmware/src/sensing/sensing.h`

```cpp
#define SENSE_SETTLE_MS 40        // espera após trocar canal do mux
```

- Deve ser **≥ `integrationTime`**. Se subir a integração, suba este junto.
- Sintoma de estar baixo: leitura "contaminada" pelo canal anterior, `X` intermitente.

**Timeout de leitura:** `firmware/src/sensing/detect_color.cpp` → `senseRaw()`
```cpp
if (millis() - t0 > 200) return false;   // ms até desistir e dar 'X'
```

---

## Camada 2 — Referência de cor (gerada pela calibração)

**Arquivo:** `firmware/src/sensing/detect_color.cpp`
**Não editar à mão** — preenchida por `c0*`. Ver/validar pela resposta do `c0*`.

| Variável | O que é | Como conferir (resposta do `c0*`) |
|----------|---------|-----------------------------------|
| `globalRef[6]` | 6 HUEs de referência (W R G Y O B) | 6 primeiros campos |
| `whiteBal[3]` | balanço de branco (wR, wG, wB) — **crítico** | 3 últimos campos |
| `whiteSatThresh` | fronteira branco↔cromáticos | 13º campo |
| `DEFAULT_HUE[6]` | placeholder pré-calibração (editável) | fallback antes do `c0*` |

**Calibração boa (checar na resposta do `c0*`):**
- `S(W)` é a **menor** saturação, com folga (~0.08, não 0).
- `whiteSatThresh` entre `S(W)` e a menor cromática.
- `wR, wG, wB` na mesma ordem de grandeza.
- `S(W)=0` ou `H(W)=0` → calibração do branco falhou; recalibrar.

---

## Camada 3 — Limiares da classificação

**Arquivo:** `firmware/src/sensing/detect_color.cpp` → `senseHsv()` / `classifyHsv()`

```cpp
if (soma < 5) return false;              // leitura morta -> 'X'
if (m.s < whiteSatThresh) return 'W';    // gate de branco (por saturação)
```

- `soma < 5`: subir se leituras válidas escuras estão virando `X`; baixar se ruído passa.

---

## Camada 4 — Auto-validação da calibração

**Arquivo:** `firmware/src/sensing/calibration.cpp` → fim de `calibrateSolved()`

```cpp
if (globalRef[0].s >= 0.5f * minChroma) return 5;   // branco não dessaturou
if (globalRef[c].s < 0.30f) return 5;               // cromática morta
if (wmax > 10.0f * wmin) return 5;                  // reflexo no branco
```

- Calibração boa sendo recusada (`e5`) → afrouxar o limiar correspondente.
- Calibração ruim passando → apertar.

---

## Camada 5 — Índice de gravação (NÃO é calibração)

**Arquivo:** `firmware/src/sensing/sense_complete.cpp` → tabela `POS`

```cpp
const uint8_t POS[6][2][4] = {
    /* U */ { {0,2,4,6}, {1,3,5,7} },
    /* R */ { {0,2,4,6}, {1,3,5,7} },
    /* F */ { {0,2,4,6}, {1,3,5,7} },
    /* D */ { {6,0,2,4}, {7,1,3,5} },
    /* L */ { {0,2,4,6}, {1,3,5,7} },
    /* B */ { {0,2,4,6}, {1,3,5,7} },
};
```

- **Regra invariante:** `centro[k] == quina[k] + 1` (sensores em adesivos adjacentes).
  Se uma face violar isso, o `POS` dela está torto.
- **Passo:** `(início_HOME + 2*k) % 8`. Só o `início` muda por face (U/D podem
  ter início deslocado conforme o posicionamento físico do sensor).
- **Sintoma de erro aqui:** fileira de cima após `A*` (U 90°) aparece **4/2**
  em vez de **3/3** — cores certas, posições trocadas.
- **Teste:** cubo resolvido → `A*` → `r0*`. Cada lateral deve ter exatamente
  **3 casas** trocadas no topo (posições 0,1,2).

---

## Ordem recomendada ao calibrar (do robô zerado)

1. `s0*` — 12 sensores respondem (`111111111111*`). Senão: hardware.
2. Cubo **resolvido** no HOME, sem reflexo. `c0*` — conferir os critérios da Camada 2.
3. `k_0*`..`k_11*` no resolvido — cada face lê a cor certa.
4. `r0*` no resolvido — STATE uniforme (`WWWW...`).
5. `A*` depois `r0*` no resolvido — validar `POS` (3/3, Camada 5).
6. Só então confiar em estados embaralhados.
