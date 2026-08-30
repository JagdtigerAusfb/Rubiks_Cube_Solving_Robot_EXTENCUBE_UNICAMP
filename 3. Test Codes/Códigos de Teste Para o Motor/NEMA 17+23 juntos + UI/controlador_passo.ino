/* ============================================================================
   controlador_passo.ino
   ----------------------------------------------------------------------------
   Sketch UNICO para os dois motores. Grave o MESMO codigo nos dois Arduinos:
   o perfil do driver (A4988 ou DM556) e enviado pelo PC via serial.

   LIGACAO
   -------
   A4988 (NEMA17)                 DM556 (NEMA23, ligacao anodo comum +5V)
     STEP  -> D3                    PUL+ -> +5V do Arduino
     DIR   -> D4                    PUL- -> D3
     ENABLE-> D5                    DIR+ -> +5V do Arduino
     GND   -> GND                   DIR- -> D4
     (ENABLE ativo em LOW)          ENA+ -> +5V do Arduino
                                    ENA- -> D5
                                    (com anodo comum, pino HIGH = motor LIGADO)

   Por isso existe o parametro ENAPOL: o nivel logico do pino D5 que HABILITA
   o motor. A4988 -> ENAPOL 0 ; DM556 anodo comum -> ENAPOL 1.

   PROTOCOLO (linhas ASCII terminadas em \n, 115200 baud)
   ------------------------------------------------------
     ID                  -> identificacao
     CFG <chave> <valor> -> altera um parametro
     EN <0|1>            -> desabilita / habilita o driver
     START               -> inicia o ciclo (repeticoes x passos com pausa)
     MOVE <passos> <dir> -> um movimento avulso (nao mexe na config)
     STOP                -> para imediatamente
     ZERO                -> zera o contador de posicao
     ST                  -> pede o status

   Chaves de CFG:
     MICRO   microstep configurado no driver (1,2,4,8,16,...)  [so informativo]
     SPR     passos inteiros por volta do motor (normalmente 200)
     VEL     velocidade alvo em passos/s
     VELI    velocidade inicial da rampa em passos/s
     ACC     aceleracao em passos/s^2 (0 = sem rampa)
     PASSOS  passos por movimento
     PAUSA   pausa entre movimentos em ms
     REP     numero de movimentos (0 = infinito)
     DIR     0 ou 1
     INVDIR  1 inverte o sentido no pino DIR
     ENAPOL  nivel do pino ENABLE que HABILITA o motor (0 ou 1)
     ALT     1 = alterna a direcao a cada movimento

   Respostas: "OK ...", "ERR ...", "EV ..." (eventos) e "ST ..." (status).
   ============================================================================ */

// ------------------------------ pinos ---------------------------------------
const uint8_t PIN_STEP = 3;
const uint8_t PIN_DIR  = 4;
const uint8_t PIN_ENA  = 5;

// largura do pulso. A4988 exige >1us, DM556 exige >2.5us. 5us atende os dois.
const uint16_t PULSO_US = 5;

// ------------------------------ estado --------------------------------------
enum Estado : uint8_t { PARADO = 0, MOVENDO = 1, PAUSANDO = 2 };

struct Cfg {
  uint16_t micro        = 1;
  uint16_t passosVolta  = 200;
  float    vel          = 400.0;   // passos/s
  float    velIni       = 100.0;   // passos/s
  float    acel         = 2000.0;  // passos/s^2 (0 = sem rampa)
  uint32_t passosMov    = 200;
  uint32_t pausaMs      = 500;
  uint32_t repeticoes   = 0;       // 0 = infinito
  bool     dir          = true;
  bool     invDir       = false;
  bool     nivelHabilita = LOW;    // A4988 por padrao
  bool     alterna      = false;
};

Cfg cfg;

Estado   estado        = PARADO;
bool     habilitado    = false;
bool     cicloAtivo    = false;   // veio de START (respeita repeticoes/pausa)
bool     pulsoAlto     = false;
bool     dirAtual      = true;

uint32_t passosRestantes = 0;
uint32_t movFeitos       = 0;
long     posicao         = 0;

float         velAtual = 100.0;
unsigned long periodo  = 10000;   // us entre passos

unsigned long tPulso  = 0;
unsigned long tPasso  = 0;
unsigned long tPausa  = 0;

char    buf[72];
uint8_t bufLen = 0;

// ------------------------------ utilidades ----------------------------------
void aplicarEnable() {
  digitalWrite(PIN_ENA, habilitado ? cfg.nivelHabilita : !cfg.nivelHabilita);
}

void aplicarDir(bool d) {
  dirAtual = d;
  digitalWrite(PIN_DIR, (d ^ cfg.invDir) ? HIGH : LOW);
  delayMicroseconds(10);          // tempo de acomodacao exigido pelo DM556
}

void pararMotor(const __FlashStringHelper *motivo) {
  estado = PARADO;
  cicloAtivo = false;
  passosRestantes = 0;
  pulsoAlto = false;
  digitalWrite(PIN_STEP, LOW);
  Serial.print(F("EV PARADO "));
  Serial.println(motivo);
}

void iniciarMovimento(uint32_t passos, bool d) {
  if (passos == 0) return;
  if (!habilitado) { habilitado = true; aplicarEnable(); delay(5); }
  aplicarDir(d);
  passosRestantes = passos;
  velAtual = (cfg.acel > 0.0) ? cfg.velIni : cfg.vel;
  if (velAtual < 1.0) velAtual = 1.0;
  periodo = (unsigned long)(1000000.0 / velAtual);
  tPasso = micros();
  pulsoAlto = false;
  estado = MOVENDO;
}

void enviarStatus() {
  Serial.print(F("ST est="));   Serial.print((uint8_t)estado);
  Serial.print(F(" pos="));     Serial.print(posicao);
  Serial.print(F(" rest="));    Serial.print(passosRestantes);
  Serial.print(F(" mov="));     Serial.print(movFeitos);
  Serial.print(F(" vel="));     Serial.print((unsigned long)velAtual);
  Serial.print(F(" en="));      Serial.print(habilitado ? 1 : 0);
  Serial.print(F(" dir="));     Serial.println(dirAtual ? 1 : 0);
}

// ------------------------------ parser --------------------------------------
void configurar(const char *k, const char *v) {
  float f = atof(v);
  long  n = atol(v);

  if      (!strcmp(k, "MICRO"))  cfg.micro       = (uint16_t)max(1L, n);
  else if (!strcmp(k, "SPR"))    cfg.passosVolta = (uint16_t)max(1L, n);
  else if (!strcmp(k, "VEL"))    cfg.vel         = max(1.0f, f);
  else if (!strcmp(k, "VELI"))   cfg.velIni      = max(1.0f, f);
  else if (!strcmp(k, "ACC"))    cfg.acel        = max(0.0f, f);
  else if (!strcmp(k, "PASSOS")) cfg.passosMov   = (uint32_t)max(0L, n);
  else if (!strcmp(k, "PAUSA"))  cfg.pausaMs     = (uint32_t)max(0L, n);
  else if (!strcmp(k, "REP"))    cfg.repeticoes  = (uint32_t)max(0L, n);
  else if (!strcmp(k, "DIR"))    cfg.dir         = (n != 0);
  else if (!strcmp(k, "INVDIR")) cfg.invDir      = (n != 0);
  else if (!strcmp(k, "ALT"))    cfg.alterna     = (n != 0);
  else if (!strcmp(k, "ENAPOL")) { cfg.nivelHabilita = (n != 0); aplicarEnable(); }
  else { Serial.print(F("ERR chave ")); Serial.println(k); return; }

  if (cfg.velIni > cfg.vel) cfg.velIni = cfg.vel;

  Serial.print(F("OK CFG ")); Serial.print(k);
  Serial.print(' ');          Serial.println(v);
}

void processarLinha(char *linha) {
  char *cmd = strtok(linha, " ");
  if (!cmd) return;
  for (char *p = cmd; *p; ++p) *p = toupper(*p);

  if (!strcmp(cmd, "ID")) {
    Serial.println(F("OK ID controlador_passo v1"));
  }
  else if (!strcmp(cmd, "CFG")) {
    char *k = strtok(NULL, " ");
    char *v = strtok(NULL, " ");
    if (!k || !v) { Serial.println(F("ERR CFG")); return; }
    for (char *p = k; *p; ++p) *p = toupper(*p);
    configurar(k, v);
  }
  else if (!strcmp(cmd, "EN")) {
    char *v = strtok(NULL, " ");
    habilitado = (v && atol(v) != 0);
    if (!habilitado) pararMotor(F("desabilitado"));
    aplicarEnable();
    Serial.print(F("OK EN ")); Serial.println(habilitado ? 1 : 0);
  }
  else if (!strcmp(cmd, "START")) {
    if (cfg.passosMov == 0) { Serial.println(F("ERR passos=0")); return; }
    movFeitos = 0;
    cicloAtivo = true;
    iniciarMovimento(cfg.passosMov, cfg.dir);
    Serial.println(F("EV RODANDO"));
  }
  else if (!strcmp(cmd, "MOVE")) {
    char *a = strtok(NULL, " ");
    char *b = strtok(NULL, " ");
    if (!a) { Serial.println(F("ERR MOVE")); return; }
    uint32_t p = (uint32_t)max(0L, atol(a));
    bool d = b ? (atol(b) != 0) : cfg.dir;
    cicloAtivo = false;
    movFeitos = 0;
    iniciarMovimento(p, d);
    Serial.println(F("EV MOVENDO"));
  }
  else if (!strcmp(cmd, "STOP")) {
    pararMotor(F("comando"));
  }
  else if (!strcmp(cmd, "ZERO")) {
    posicao = 0;
    Serial.println(F("OK ZERO"));
  }
  else if (!strcmp(cmd, "ST")) {
    enviarStatus();
  }
  else {
    Serial.print(F("ERR cmd ")); Serial.println(cmd);
  }
}

void lerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (bufLen) { buf[bufLen] = '\0'; processarLinha(buf); bufLen = 0; }
    } else if (bufLen < sizeof(buf) - 1) {
      buf[bufLen++] = c;
    }
  }
}

// ------------------------------ geracao de passos ---------------------------
void atualizarVelocidade() {
  if (cfg.acel <= 0.0) { velAtual = cfg.vel; }
  else {
    float dt = periodo / 1000000.0;
    // passos necessarios para desacelerar ate a velocidade inicial
    float paraFrear = (velAtual * velAtual - cfg.velIni * cfg.velIni) / (2.0 * cfg.acel);
    if ((float)passosRestantes <= paraFrear) velAtual -= cfg.acel * dt;
    else                                     velAtual += cfg.acel * dt;
    if (velAtual < cfg.velIni) velAtual = cfg.velIni;
    if (velAtual > cfg.vel)    velAtual = cfg.vel;
  }
  periodo = (unsigned long)(1000000.0 / velAtual);
  if (periodo < PULSO_US * 2) periodo = PULSO_US * 2;
}

void executar() {
  unsigned long agora = micros();

  if (estado == MOVENDO) {
    if (pulsoAlto) {
      if (agora - tPulso >= PULSO_US) {
        digitalWrite(PIN_STEP, LOW);
        pulsoAlto = false;
        posicao += dirAtual ? 1 : -1;
        passosRestantes--;
        atualizarVelocidade();

        if (passosRestantes == 0) {
          movFeitos++;
          Serial.print(F("EV FIMMOV ")); Serial.println(movFeitos);
          if (cicloAtivo && (cfg.repeticoes == 0 || movFeitos < cfg.repeticoes)) {
            if (cfg.alterna) cfg.dir = !cfg.dir;
            if (cfg.pausaMs > 0) { estado = PAUSANDO; tPausa = millis(); }
            else                 iniciarMovimento(cfg.passosMov, cfg.dir);
          } else {
            estado = PARADO;
            cicloAtivo = false;
            Serial.println(F("EV FIM"));
          }
        }
      }
    } else if (agora - tPasso >= periodo) {
      tPasso = agora;
      tPulso = agora;
      digitalWrite(PIN_STEP, HIGH);
      pulsoAlto = true;
    }
  }
  else if (estado == PAUSANDO) {
    if (millis() - tPausa >= cfg.pausaMs) iniciarMovimento(cfg.passosMov, cfg.dir);
  }
}

// ------------------------------ setup / loop --------------------------------
void setup() {
  pinMode(PIN_STEP, OUTPUT);
  pinMode(PIN_DIR,  OUTPUT);
  pinMode(PIN_ENA,  OUTPUT);
  digitalWrite(PIN_STEP, LOW);
  digitalWrite(PIN_DIR,  LOW);

  habilitado = false;
  aplicarEnable();

  Serial.begin(115200);
  Serial.println(F("EV PRONTO"));
}

void loop() {
  lerSerial();
  executar();
}
