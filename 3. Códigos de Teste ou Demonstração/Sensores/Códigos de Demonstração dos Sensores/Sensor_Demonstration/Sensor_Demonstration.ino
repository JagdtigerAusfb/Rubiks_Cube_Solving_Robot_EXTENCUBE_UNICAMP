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


// Funções Sensor
void sensor_rgb(float &red, float &green, float &blue, float &sum) {


  if (!tcs.attach(Wire)) {
    Serial.print("Sensor nao encontrado!");
    // Aguarda Sensor conectar
    while (1);
  }
  
  tcs.integrationTime(33);
  tcs.gain(TCS34725::Gain::X01);


  delay(50); // alterar delay?

  red = 0;
  green = 0;
  blue = 0;
  sum = 0;


  for (int i = 0; i < AMOSTRAS; i++) {
    while (!tcs.available());

    auto c = tcs.color();
    float r = c.r, g = c.g, b = c.b;
    float soma = r + g + b;
    if (soma < 5) {continue;}

    red = r;
    green = g;
    blue = b;
    sum = soma;
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
  char carac;
  float hue_verde;
  float hue_vermelho;
  float hue_azul;
  float hue_laranja;
  float hue_branco;
  float hue_amarelo;
  Serial.println("Calibrar ou Leitura? (C ou L)");
  while (Serial.available() <= 0) {
  // Aguarda confirmação de movimento pela serial
  }
  while (Serial.available() > 0){ // Enviado qualquer confirmação pela serial continua
    carac = Serial.read(); // limpa serial
  }
  if (carac == 'C') {
    carac ='\0';
    flag_calib = 1;

    Serial.println("Mostre Verde (confirme pela serial)");
    while (Serial.available() <= 0);
    Serial.read(); // limpa serial
    calib(hue_verde);

    Serial.println("Mostre Vermelho (confirme pela serial)");
    while (Serial.available() <= 0);
    Serial.read(); // limpa serial
    calib(hue_vermelho);

    Serial.println("Mostre Azul (confirme pela serial)");
    while (Serial.available() <= 0);
    Serial.read(); // limpa serial
    calib(hue_azul);

    Serial.println("Mostre Laranja (confirme pela serial)");
    while (Serial.available() <= 0);
    Serial.read(); // limpa serial
    calib(hue_laranja);

    Serial.println("Mostre Branco (confirme pela serial)");
    while (Serial.available() <= 0);
    Serial.read(); // limpa serial
    calib(hue_branco);

    Serial.println("Mostre Amarelo (confirme pela serial)");
    while (Serial.available() <= 0);
    Serial.read(); // limpa serial
    calib(hue_amarelo);
    Serial.println("Calibração Concluída");
  }
  if (carac == 'L') {
    carac ='\0';
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

      Serial.print("A cor é");
      if (dOrange == menor) {Serial.println(" Laranja");}
      else if (dYellow == menor) {Serial.println(" Amarelo");}
      else if (dWhite  == menor) {Serial.println(" Branco");}
      else if (dGreen  == menor) {Serial.println(" Verde");}
      else if (dBlue   == menor) {Serial.println(" Azul");}
      else {Serial.println(" Vermelho");}
    }
    else {
      Serial.println("Calibre Primeiro");
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








