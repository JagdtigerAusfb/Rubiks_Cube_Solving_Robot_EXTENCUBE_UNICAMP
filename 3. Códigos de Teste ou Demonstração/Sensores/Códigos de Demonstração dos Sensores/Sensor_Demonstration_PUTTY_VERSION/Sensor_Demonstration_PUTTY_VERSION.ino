/*
---------------------------------------------------------------------------------
        Código de Calibração de uma unidade de sensor
---------------------------------------------------------------------------------
Este programa implementa a calibração do parâmetro de classificação de uma cor para um sensor.
O procedimento de calibração consiste em sensoriar uma face com cor conhecida e executando este código
obter HUE_Médio para determinada cor que servirá de parametro de classificação nos sensoriamentos futuros.
Cada um dos 12 sensores deve ter 6 valores de HUE_Médio, um para cada cor.
Logo o programa de calibração completa (a ser implementado) deve obter uma matriz 12x6 com 96 valores.
*/
#include <Wire.h>
#include "TCS34725.h"



TCS34725 tcs;

  #define LED_2 19
  #define LED_3 18
  #define LED_4 17
  #define LED_5 16
  #define LED_6 15
  #define LED_7 14
  #define LED_8 7
  #define LED_9 8
  #define LED_10 9
  #define LED_11 10





  #define LED_0 13
  #define LED_1 12

  #define EN_MUX 2
  #define MUX_0 3
  #define MUX_1 4
  #define MUX_2 5
  #define MUX_3 6 


#define AMOSTRAS 20

int flag_calib = 0;

char carac;
float hue_verde;
float hue_vermelho;
float hue_azul;
float hue_laranja;
float hue_branco;
float hue_amarelo;

//----------FUNÇÕES EXTRAS PARA INTERFACE PUTTY----
#define TXT_PRETO    "\x1b[30;107m"
#define TXT_VERDE    "\x1b[92;107m"
#define TXT_VERMELHO "\x1b[91;107m"
#define TXT_AZUL     "\x1b[94;107m"
#define TXT_LARANJA  "\x1b[38;5;208;107m"
#define TXT_AMARELO  "\x1b[93;107m"

void aguardarTecla() {
  while (Serial.available() > 0) Serial.read(); // Limpa sujeiras anteriores
  while (Serial.available() <= 0);              // Aguarda nova tecla
  delay(50);                                    // Espera chegar \r e \n juntos
  while (Serial.available() > 0) Serial.read(); // Limpa o buffer de vez
}

// Função para posicionar e centralizar qualquer texto numa linha específica
void printCentralizado(String texto, int linha, String COR_TEXTO) {
  int coluna = (48 - texto.length()) / 2;
  if (coluna < 1) coluna = 1;

  // 1. Define fundo branco puro (107)
  Serial.print("\x1b[107m");

  // 2. Limpa a linha inteira com o fundo branco puro
  Serial.print("\x1b[");
  Serial.print(linha);
  Serial.print(";1H\x1b[2K");

  // 3. Aplica a cor do TEXTO enviada no parâmetro
  Serial.print(COR_TEXTO);

  // 4. Posiciona o cursor e imprime
  Serial.print("\x1b[");
  Serial.print(linha);
  Serial.print(";");
  Serial.print(coluna);
  Serial.print("H");

  Serial.println(texto);
}
//---------------------------------------------------PUTTY


// Funções Sensor
void sensor_rgb(float &red, float &green, float &blue, float &sum) {
  if (!tcs.attach(Wire)) {
    Serial.print("\x1b[30;107m\033[2J");
    printCentralizado("Sensor nao encontrado!", 8, TXT_PRETO);
    while (1);
  }
  
  tcs.integrationTime(33);
  tcs.gain(TCS34725::Gain::X16); // Aumentado para X16 para melhorar a precisão
  delay(50);

  float r_acc = 0, g_acc = 0, b_acc = 0, sum_acc = 0;
  int lidas = 0;

  for (int i = 0; i < AMOSTRAS; i++) {
    while (!tcs.available());
    auto c = tcs.color();
    float soma = c.r + c.g + c.b;
    if (soma < 5) continue;

    r_acc += c.r;
    g_acc += c.g;
    b_acc += c.b;
    sum_acc += soma;
    lidas++;
    
    delay(40); // Aguarda o tempo de integração do sensor para a próxima leitura
  }

  if (lidas > 0) {
    red = r_acc / lidas;
    green = g_acc / lidas;
    blue = b_acc / lidas;
    sum = sum_acc / lidas;
  }
}

void MUX(int n){
  digitalWrite(EN_MUX, HIGH);
  digitalWrite(LED_0, LOW);
  digitalWrite(LED_1, LOW);
  digitalWrite(LED_2, LOW);
  digitalWrite(LED_3, LOW);
  digitalWrite(LED_4, LOW);
  digitalWrite(LED_5, LOW);
  digitalWrite(LED_6, LOW);
  digitalWrite(LED_7, LOW);
  digitalWrite(LED_8, LOW);
  digitalWrite(LED_9, LOW);
  digitalWrite(LED_10, LOW);
  digitalWrite(LED_11, LOW);

  switch(n) {
    case 0:
      digitalWrite(LED_0, HIGH);
      break;
    case 1:
      digitalWrite(LED_1, HIGH);
      break;
    case 2:
      digitalWrite(LED_2, HIGH);
      break;
    case 3:
      digitalWrite(LED_3, HIGH);
      break;
    case 4:
      digitalWrite(LED_4, HIGH);
      break;
    case 5:
      digitalWrite(LED_5, HIGH);
      break;
    case 6:
      digitalWrite(LED_6, HIGH);
      break;
    case 7:
      digitalWrite(LED_7, HIGH);
      break;
    case 8:
      digitalWrite(LED_8, HIGH);
      break;
    case 9:
      digitalWrite(LED_9, HIGH);
      break;
    case 10:
      digitalWrite(LED_10, HIGH);
      break;
    case 11:
      digitalWrite(LED_11, HIGH);
      break;
    default:
      break;
  } // Liga o LED do sensor NS

  // Seleciona o Sensor
  if ((n & (1<<0)) == (1<<0)) {digitalWrite(MUX_0, HIGH);}
  else{digitalWrite(MUX_0, LOW);}
  if ((n & (1<<1)) == (1<<1)) {digitalWrite(MUX_1, HIGH);}
  else{digitalWrite(MUX_1, LOW);}
  if ((n & (1<<2)) == (1<<2)) {digitalWrite(MUX_2, HIGH);}
  else{digitalWrite(MUX_2, LOW);}
  if ((n & (1<<3)) == (1<<3)) {digitalWrite(MUX_3, HIGH);}
  else{digitalWrite(MUX_3, LOW);}
  //Seleciona Sensor NS pelo MUX
  digitalWrite(EN_MUX, LOW);  // Habilita MUX
}

void rgbToHsv(float r, float g, float b,float &hue, float &sat, float &val) {
  float maxc = max(r, max(g, b));
  float minc = min(r, min(g, b));
  float delta = maxc - minc;

  val = maxc;
  if ((maxc == 0)) { sat = 0; hue = 0; return; }
  sat = delta / maxc;

  if (delta == 0) hue = 0;
  else if (maxc == r) hue = 60.0 * fmod(((g - b) / delta), 6);
  else if (maxc == g) hue = 60.0 * (((b - r) / delta) + 2);
  else hue = 60.0 * (((r - g) / delta) + 4);


  if (hue < 0) hue += 360.0;
  
}


void setup() {
  Serial.begin(115200);
  Wire.begin();

  //Configuração Portas - Sensor
    pinMode(LED_0, OUTPUT);
    pinMode(LED_1, OUTPUT);
    pinMode(LED_2, OUTPUT);
    pinMode(LED_3, OUTPUT);
    pinMode(LED_4, OUTPUT);
    pinMode(LED_5, OUTPUT);
    pinMode(LED_6, OUTPUT);
    pinMode(LED_7, OUTPUT);
    pinMode(LED_8, OUTPUT);
    pinMode(LED_9, OUTPUT);
    pinMode(LED_10, OUTPUT);
    pinMode(LED_11, OUTPUT);


    pinMode(EN_MUX, OUTPUT);
    pinMode(MUX_0, OUTPUT);
    pinMode(MUX_1, OUTPUT);
    pinMode(MUX_2, OUTPUT);
    pinMode(MUX_3, OUTPUT);    
  //
}


void loop() {
  Serial.print("\x1b[30;107m"); // Garante fundo branco
  Serial.print("\033[2J"); // Limpa tela
  printCentralizado("Calibração (C)", 7, TXT_PRETO);
  printCentralizado("ou", 8, TXT_PRETO);
  printCentralizado("Leitura (L)",9, TXT_PRETO);
  while (Serial.available() <= 0) {
  // Aguarda confirmação de movimento pela serial
  }
  while (Serial.available() > 0){ // Enviado qualquer confirmação pela serial continua
    carac = Serial.read(); // limpa serial
  }
  if (carac == 'C' || carac == 'c') {
    carac = '\0';
    flag_calib = 1;
    Serial.print("\x1b[30;107m\033[2J");
    
    printCentralizado("MODO DE CALIBRAÇÃO", 6, TXT_PRETO);
    printCentralizado("Apresente a cor", 7, TXT_PRETO);
    printCentralizado("Verde", 8, TXT_VERDE);
    printCentralizado("Calibração 0/6", 9, TXT_PRETO);
    printCentralizado("Pressione Enter...", 10, TXT_PRETO);
    
    aguardarTecla(); // Trava e aguarda o usuário posicionar a peça
    calib(hue_verde);

    printCentralizado("Vermelho", 8, TXT_VERMELHO);
    printCentralizado("Calibração 1/6", 9, TXT_PRETO);
    aguardarTecla();
    calib(hue_vermelho);

    printCentralizado("Azul", 8, TXT_AZUL);
    printCentralizado("Calibração 2/6", 9, TXT_PRETO);
    aguardarTecla();
    calib(hue_azul);

    printCentralizado("Laranja", 8, TXT_LARANJA);
    printCentralizado("Calibração 3/6", 9, TXT_PRETO);
    aguardarTecla();
    calib(hue_laranja);

    printCentralizado("Branco", 8, TXT_PRETO);
    printCentralizado("Calibração 4/6", 9, TXT_PRETO);
    aguardarTecla();
    calib(hue_branco);

    printCentralizado("Amarelo", 8, TXT_AMARELO);
    printCentralizado("Calibração 5/6", 9, TXT_PRETO);
    aguardarTecla();
    calib(hue_amarelo);

    Serial.print("\x1b[30;107m\033[2J");
    printCentralizado("Calibração Concluída!", 8, TXT_PRETO);
    aguardarTecla();
  }
  if (carac == 'L') {
    carac ='\0';
    Serial.print("\x1b[30;107m"); // Garante fundo branco
    Serial.print("\033[2J"); // Limpa tela
    if (flag_calib) {
      float h;
      calib(h);
      float dRed    = distHue(h, hue_vermelho);
      float dOrange = distHue(h, hue_laranja);
      float dYellow = distHue(h, hue_amarelo);
      float dWhite  = distHue(h, hue_branco);
      float dGreen  = distHue(h, hue_verde);
      float dBlue   = distHue(h, hue_azul);   
      
      float menor = min(dRed, dOrange);
      menor = min(menor, dYellow);
      menor = min(menor, dWhite);
      menor = min(menor, dGreen);
      menor = min(menor, dBlue);

      printCentralizado("A Cor Sensoriada É",7, TXT_PRETO);
      if (dOrange == menor) {printCentralizado("Laranja", 8,TXT_LARANJA);}
      else if (dYellow == menor) {printCentralizado("Amarelo", 8,TXT_AMARELO);}
      else if (dWhite  == menor) {printCentralizado("Branco", 8, TXT_PRETO);}
      else if (dGreen  == menor) {printCentralizado("Verde", 8, TXT_VERDE);}
      else if (dBlue   == menor) {printCentralizado("Azul", 8,TXT_AZUL);}
      else {printCentralizado("Vermelho", 8,TXT_VERMELHO);}
      while (Serial.available() <= 0);
      Serial.read(); // limpa serial
    }
    else {
      Serial.print("\x1b[30;107m"); // Garante fundo branco
      Serial.print("\033[2J"); // Limpa tela
      printCentralizado("Calibre Primeiro", 8, TXT_PRETO);
      while (Serial.available() <= 0);
      Serial.read(); // limpa serial
    }
  }


}

float distHue(float h1, float h2) {
  float d = abs(h1 - h2);
  return min(d, 360 - d);
}

void calib(float &hue){
  MUX(1);
  float r_NS, g_NS, b_NS, sum_NS;
  sensor_rgb(r_NS, g_NS, b_NS, sum_NS);
  digitalWrite(LED_0, LOW);
  digitalWrite(LED_1, LOW);
  digitalWrite(LED_2, LOW);
  digitalWrite(LED_3, LOW);
  digitalWrite(LED_4, LOW);
  digitalWrite(LED_5, LOW);
  digitalWrite(LED_6, LOW);
  digitalWrite(LED_7, LOW);
  digitalWrite(LED_8, LOW);
  digitalWrite(LED_9, LOW);
  digitalWrite(LED_10, LOW);
  digitalWrite(LED_11, LOW);
  r_NS /= sum_NS;
  g_NS /= sum_NS;
  b_NS /= sum_NS;

  // Converte RGB para HSV
  float sat, val;
  rgbToHsv(r_NS, g_NS, b_NS, hue, sat, val);
}