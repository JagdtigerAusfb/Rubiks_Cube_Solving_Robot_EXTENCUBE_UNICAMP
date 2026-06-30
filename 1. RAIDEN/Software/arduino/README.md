# RAIDEN

**[WORK IN PROGRESS]**

Repositório com todo o material de hardware do **Raiden**, um robô solucionador de Cubo Mágico desenvolvido como projeto de extensão na UNICAMP. O objetivo é resolver o cubo usando 6 motores de passo (um por face), sensores de cor para leitura do estado do cubo, e um Arduino Mega como controlador central.

## Estrutura do repositório

```
1. RAIDEN/
├── 3D Files/              # Modelos 3D da estrutura mecânica do robô (em preparação)
└── PCB/                   # Placas de circuito (projetos KiCad)
    ├── PCB 3 Drivers/
    ├── PCB Drivers + Sensores/
    └── PCB TUPAN/
```

### `3D Files/`
Pasta destinada aos arquivos de modelagem 3D da estrutura mecânica (chassi, suportes dos motores, base, etc.). Por enquanto contém apenas o README original do projeto — os modelos ainda não foram adicionados.

### `PCB/PCB Drivers + Sensores/` — **Placa principal**
Shield para o **Arduino Mega**, responsável por toda a parte de potência e leitura de sensores do robô:

- **6x drivers de motor de passo A4988** (módulos Pololu), um para cada face do cubo
- **12x conectores para sensores de cor TCS34725**
- **1x multiplexador CD74HC4067** para gerenciar as 12 entradas I²C dos sensores
- 2x conectores Jack DC de 12 V (alimentação redundante, recomenda-se usar os dois para evitar queda de tensão e travamento de motores)
- LEDs indicadores (de driver e de alimentação) e botão de reset — ambos opcionais
- Capacitores de desacoplamento nos drivers — **fortemente recomendados**, mesmo sendo opcionais

A pasta inclui o projeto completo do KiCad (esquemático, PCB, footprints customizados), arquivos de fabricação (Gerber, drill, BOM, posições de componentes em `production/`) e o modelo 3D da placa (`.step`). O README específico dessa pasta detalha a pinagem completa dos drivers, sensores e multiplexador, além de avisos importantes sobre os conectores do Arduino e sobre versões do TCS34725 que não devem ser ligadas em 5 V.

### `PCB/PCB 3 Drivers/`
Placa mais simples, com apenas **3 drivers A4988**, feita antes da placa definitiva (Drivers + Sensores) estar pronta. É uma alternativa/protótipo intermediário, não obrigatória para o projeto final — segundo o autor, "use se quiser, ou não, eu não me importo".

### `PCB/PCB TUPAN/`
Placa em estágio inicial de desenvolvimento. Contém apenas o arquivo `.kicad_pcb`, ainda vazio (sem esquemático nem componentes posicionados). Aparentemente é a próxima revisão/placa planejada para o projeto, ainda não iniciada de fato.

## Pinagem de referência (placa Drivers + Sensores)

**Drivers A4988** (pinos DIR / STEP / ENABLE):

| Driver | DIR | STEP | ENABLE |
|---|---|---|---|
| 1 | A0 | A1 | A2 |
| 2 | A3 | A4 | A5 |
| 3 | A6 | A7 | A8 |
| 4 | 53 | 51 | 49 |
| 5 | 43 | 41 | 39 |
| 6 | 29 | 27 | 25 |

Pinos de microstepping (MS) ficam desconectados e RESET/SLEEP são amarrados juntos — isso só funciona porque os drivers usados têm resistores de pull-up/pull-down internos.

**Sensores TCS34725** (pino de controle do LED no Arduino): 13, 12, 11, 10, 9, 8, 14, 15, 16, 17, 18, 19 (sensores 1 a 12, respectivamente).

**Multiplexador CD74HC4067** (seleção): S0=5, S1=4, S2=3, S3=2. Entradas C0–C11 ligadas aos sinais SDA_1 a SDA_12.

Detalhes completos, observações de hardware e ressalvas estão nos READMEs de cada subpasta de PCB.

## Status do projeto

- ✅ Placa "Drivers + Sensores" — projeto completo, com arquivos de fabricação prontos
- ✅ Placa "3 Drivers" — protótipo funcional, opcional
- 🚧 Placa "Tupan" — apenas iniciada
- 🚧 Modelos 3D — ainda não adicionados ao repositório
- 🚧 Vídeo de demonstração e manual do usuário/tutorial de montagem — pendentes (ver `3D Files/README.md`)
