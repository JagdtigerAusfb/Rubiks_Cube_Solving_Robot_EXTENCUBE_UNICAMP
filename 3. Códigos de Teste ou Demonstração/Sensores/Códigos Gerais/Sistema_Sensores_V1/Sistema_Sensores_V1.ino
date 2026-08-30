#include <Wire.h>
#include <string.h>
#include "TCS34725.h"

//Sensores
  
  TCS34725 tcs;
  #define AMOSTRAS 20

  //Sensores/Multiplexador
    #define LED_0 2
    #define LED_1 3
    #define LED_2 4
    #define LED_3 5
    #define LED_4 6
    #define LED_5 7
    #define LED_6 8
    #define LED_7 9
    #define LED_8 10
    #define LED_9 11
    #define LED_10 12
    #define LED_11 13


    #define EN_MUX 23
    #define MUX_0 22
    #define MUX_1 18
    #define MUX_2 17
    #define MUX_3 15 
  //

  //Inicialização de parâmetros Calibração
    int face_calib = 0;
    int position_calib = 0;
    int estado_calib = 0;
    bool flag_calib = false;
    int progression_calib[6] = {0};
    float m_calibration[12][6] = {-1};
    
    // Define Constantes de Operação do Sistema
    //Inserir aqui Parametros peso de HSV
    int ordem[6][6] = {
        {0, 1, 3, 4, 5, 2},
        {1, 5, 4, 2, 0, 3},
        {2, 1, 5, 4, 0, 3},
        {3, 1, 0, 4, 2, 5},
        {4, 2, 1, 5, 3, 0},
        {5, 4, 2, 1, 3, 0}
    };
    int seq_faces_calib[] = {
      0,3, 0,3, 0,3, 0,3,
      2,1,5,4, 2,1,5,4, 2,1,5,4, 2,1,5,4,
      0,3, 0,3,
      2,5, 2,5,
      1,4, 1,4
    };
    char seq_moves_calib[][7] = {
      "PG", "PG", "PG", "PG",
      "A", "A", "A",
      "AEBK", "JAFBK",
      "JAFHP", "GQFHP",
      "GQEQEM", "DNREM",
      "DNQ"
    };
    bool flags_move_calib[] = {
      0,0,1,0,1,0,1,0,
      1,0,0,0, 1,0,0,0, 1,0,0,0, 1,0,0,0,
      1,0,1,0,
      1,0,1,0,
      1,0,1,0,
      1
    };
  //

  //Inicialização de parâmetros Embaralhamento
    int face_shuf = 0;
    int position_shuf = 0;
    int estado_shuf = 0;
    int progression_shuf[6] = {0};
    char m_shuffle[6][8];
    int erros_shuf;

    // Define Constantes de Operação do Sistema
    //Inserir aqui Parametros peso de HSV
      int seq_faces_shuf[] =  {
        0,3, 0,3, 0,3, 0,3,
        2,5, 2,5, 2,5, 2,5,
        1,4, 1,4, 1,4, 1,4
      };
      char seq_moves_shuf[][3] = {
        "BK", "BK", "BK", "BK",
        "HQ", "HQ", "HQ", "HQ",
        "EN", "EN", "EN", "EN"
      };
      bool flags_move_shuf[] = {
      0,0, 1,0, 1,0, 1,0,
      1,0, 1,0, 1,0, 1,0,
      1,0, 1,0, 1,0, 1,0,
      1
      };
  //
//

//Motores
  #define DIR_PIN_1 31
  #define STEP_PIN_1 30
  #define DIR_PIN_2 35
  #define STEP_PIN_2 34
  #define DIR_PIN_3 A12
  #define STEP_PIN_3 A13
  #define DIR_PIN_4 A6
  #define STEP_PIN_4 A7
  #define DIR_PIN_5 A0
  #define STEP_PIN_5 A1
  #define DIR_PIN_6 43
  #define STEP_PIN_6 42


  #define ENABLE_PIN_1 14
  #define ENABLE_PIN_2 16
  #define ENABLE_PIN_3 49
  #define ENABLE_PIN_4 48
  #define ENABLE_PIN_5 A3
  #define ENABLE_PIN_6 19

  #define MAX_SEQ 350


  char lineBuffer[50];
  char sequencia[MAX_SEQ];


  int seqLen = 0;
  int DELAY_STEP = 1000;
  int DELAY_ENTRE_MOV = 10;


  bool recebendo = false;

//

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

  //Configuração Portas - Motores
    pinMode(ENABLE_PIN_1,OUTPUT); digitalWrite(ENABLE_PIN_1,HIGH);
    pinMode(ENABLE_PIN_2,OUTPUT); digitalWrite(ENABLE_PIN_2,HIGH);
    pinMode(ENABLE_PIN_3,OUTPUT); digitalWrite(ENABLE_PIN_3,HIGH);
    pinMode(ENABLE_PIN_4,OUTPUT); digitalWrite(ENABLE_PIN_4,HIGH);
    pinMode(ENABLE_PIN_5,OUTPUT); digitalWrite(ENABLE_PIN_5,HIGH);
    pinMode(ENABLE_PIN_6,OUTPUT); digitalWrite(ENABLE_PIN_6,HIGH);


    pinMode(DIR_PIN_1,OUTPUT); pinMode(STEP_PIN_1,OUTPUT);
    pinMode(DIR_PIN_2,OUTPUT); pinMode(STEP_PIN_2,OUTPUT);
    pinMode(DIR_PIN_3,OUTPUT); pinMode(STEP_PIN_3,OUTPUT);
    pinMode(DIR_PIN_4,OUTPUT); pinMode(STEP_PIN_4,OUTPUT);
    pinMode(DIR_PIN_5,OUTPUT); pinMode(STEP_PIN_5,OUTPUT);
    pinMode(DIR_PIN_6,OUTPUT); pinMode(STEP_PIN_6,OUTPUT);
  //

}

void loop() {
  char carac;
  Serial.println();
  Serial.println("Calibrar? (digite C)");
  if (flag_calib) {Serial.println("Leitura Embaralhamento? (digite L)");}

  while (Serial.available() <= 0)
  // Aguarda confirmação pela serial
  while (Serial.available() > 0){
    carac = Serial.read();
  }
  if (carac == 'C') {
    carac ='\0';
    calibration();
  }
  if (carac == 'L') {
    carac ='\0';
    if (flag_calib) { shuffle();}
    else {Serial.println("CALIBRE PRIMEIRO");}
  }
}


// Funções motor

  bool configurarMotor(char m, int &dirPin, int &stepPin, int &enablePin, int &dir, int &passos) {


      switch(m) {


          case 'A': dirPin=DIR_PIN_1; stepPin=STEP_PIN_1; enablePin=ENABLE_PIN_1; dir=LOW;  passos=50; break;
          case 'B': dirPin=DIR_PIN_1; stepPin=STEP_PIN_1; enablePin=ENABLE_PIN_1; dir=HIGH; passos=50; break;
          case 'C': dirPin=DIR_PIN_1; stepPin=STEP_PIN_1; enablePin=ENABLE_PIN_1; dir=LOW;  passos=100; break;


          case 'D': dirPin=DIR_PIN_2; stepPin=STEP_PIN_2; enablePin=ENABLE_PIN_2; dir=LOW;  passos=50; break;
          case 'E': dirPin=DIR_PIN_2; stepPin=STEP_PIN_2; enablePin=ENABLE_PIN_2; dir=HIGH; passos=50; break;
          case 'F': dirPin=DIR_PIN_2; stepPin=STEP_PIN_2; enablePin=ENABLE_PIN_2; dir=LOW;  passos=100; break;


          case 'G': dirPin=DIR_PIN_3; stepPin=STEP_PIN_3; enablePin=ENABLE_PIN_3; dir=LOW;  passos=50; break;
          case 'H': dirPin=DIR_PIN_3; stepPin=STEP_PIN_3; enablePin=ENABLE_PIN_3; dir=HIGH; passos=50; break;
          case 'I': dirPin=DIR_PIN_3; stepPin=STEP_PIN_3; enablePin=ENABLE_PIN_3; dir=LOW;  passos=100; break;


          case 'J': dirPin=DIR_PIN_4; stepPin=STEP_PIN_4; enablePin=ENABLE_PIN_4; dir=LOW;  passos=50; break;
          case 'K': dirPin=DIR_PIN_4; stepPin=STEP_PIN_4; enablePin=ENABLE_PIN_4; dir=HIGH; passos=50; break;
          case 'L': dirPin=DIR_PIN_4; stepPin=STEP_PIN_4; enablePin=ENABLE_PIN_4; dir=LOW;  passos=100; break;


          case 'M': dirPin=DIR_PIN_5; stepPin=STEP_PIN_5; enablePin=ENABLE_PIN_5; dir=LOW;  passos=50; break;
          case 'N': dirPin=DIR_PIN_5; stepPin=STEP_PIN_5; enablePin=ENABLE_PIN_5; dir=HIGH; passos=50; break;
          case 'O': dirPin=DIR_PIN_5; stepPin=STEP_PIN_5; enablePin=ENABLE_PIN_5; dir=LOW;  passos=100; break;


          case 'P': dirPin=DIR_PIN_6; stepPin=STEP_PIN_6; enablePin=ENABLE_PIN_6; dir=LOW;  passos=50; break;
          case 'Q': dirPin=DIR_PIN_6; stepPin=STEP_PIN_6; enablePin=ENABLE_PIN_6; dir=HIGH; passos=50; break;
          case 'R': dirPin=DIR_PIN_6; stepPin=STEP_PIN_6; enablePin=ENABLE_PIN_6; dir=LOW;  passos=100; break;


          default: return false;
      }
      return true;
  }

  void executarSimples(char m){


      int d,s,e,dir,p;
      if(!configurarMotor(m,d,s,e,dir,p)) return;


      digitalWrite(e,LOW);
      digitalWrite(d,dir);


      for(int i=0;i<p;i++){
          digitalWrite(s,HIGH);
          delayMicroseconds(DELAY_STEP);
          digitalWrite(s,LOW);
          delayMicroseconds(DELAY_STEP);
      }


      digitalWrite(e,HIGH);
      delay(DELAY_ENTRE_MOV);
  }

//

// Funções sensor

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

  void MUX(int n){
    digitalWrite(EN_MUX, LOW);
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
        digitalWrite(LED_0, HIGH);
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
    digitalWrite(EN_MUX, HIGH);  // Habilita MUX
  }

//

// Funções Calibração
  void imprimirCalib(float matriz[][6], int linhas, int colunas) {
    Serial.println();
    Serial.println("============= CALIBRATION =============");
  
    String nomesColunas[6] = {"White", "Red", "Green", "Yellow", "Orange", "Blue"};
    String nomesLinhas[12] = {"Ue", "Uc", "Re", "Rc", "Fe", "Fc", "De", "Dc", "Le", "Lc", "Be", "Bc"};
    // Cabeçalho
    Serial.print("\t");
    for (int j = 0; j < colunas; j++) {
      Serial.print(nomesColunas[j]);
      Serial.print("\t");
    }
    Serial.println();


    // Linhas da matriz
    for (int i = 0; i < linhas; i++) {
      Serial.print(nomesLinhas[i]);
      Serial.print("\t");


      for (int j = 0; j < colunas; j++) {
        Serial.print(matriz[i][j], 2); // 2 casas decimais
        Serial.print("\t");
      }
      Serial.println();
    }
  }

  void calibration() {
    
    face_calib = 0;
    position_calib = 0;
    estado_calib = 0;
    flag_calib = true;
    for (int j; j < 6; j++) {progression_calib[j] = 0;}
    
    while(1) {
      
      // Bloco Sensoriamento Calibração
        int NS = 2*face_calib + position_calib;

        // Leitura
        MUX(NS);
        float r_NS, g_NS, b_NS, sum_NS;
        sensor_rgb(r_NS, g_NS, b_NS, sum_NS);
        r_NS /= sum_NS;
        g_NS /= sum_NS;
        b_NS /= sum_NS;
        
        float hue, sat, val;
        rgbToHsv(r_NS, g_NS, b_NS, hue, sat, val);
        
        // Armazena Valor Medido
        int b = progression_calib[face_calib];
        int indice = ordem[face_calib][b];
        m_calibration[NS][indice] = hue;

        estado_calib++;
      //
    
      if (position_calib == 0){
        position_calib = 1;
        continue;
      }
    
      position_calib = 0;
      progression_calib[face_calib]++;
    
    
      if (estado_calib == 72) { // Condição de término
        imprimirCalib(m_calibration,12,6);
        flag_calib = true;
        break;
      }
      
      int a = estado_calib>>1;
      face_calib = seq_faces_calib[a];
    
      if (flags_move_calib[a]) {
        // Executa movimentos da string
        for (int i = 0; seq_moves_calib[a][i] != '\0'; i++) {
          executarSimples(seq_moves_calib[a][i]);
        } 
      }
    }
  }
//

// Funções Embaralhamento
  void imprimirShuf() {
    Serial.println("Embaralhamento 48 cores, URFDLB (Sem centros):");
    for (int i = 0; i < 6; i++) {
      for (int j = 0; j < 8; j++) {
        Serial.print(m_shuffle[i][j]); // 2 casas decimais
      }
      Serial.println();
    }
    return;
  }

  void classific(float h, float s, float v, char &rotulo) {

    // Condições HSV p/ medida inválida, classificação erronea
      if (s < 0.05) { // Saturação muito baixa (leitura cinza)
        erros_shuf++;
        return 'X';
      }
      //ADICIONAR OUTRAS CONDIÇÕES
    //
    int x;
    float ang = 180; // Maior distância angular possível
    for (int i = 0; i < 6; i++) {
      float dist = abs(h - m_calibration[face_shuf][i]); // distancia angular entre medida e calibração
      dist = min(dist, 360 - dist); // correção angulo
      
      if (dist <= ang) {
        ang = dist; // seleciona o menor angulo
        x = i; // registra cor correspondente 
      }
    }
    switch(x) {
      case 0:
        rotulo = 'W';
        break;
      case 1:
        rotulo = 'R';
        break;
      case 2:
        rotulo = 'G';
        break;
      case 3:
        rotulo = 'Y';
        break;
      case 4:
        rotulo = 'O';
        break;
      default: // 5
        rotulo = 'B';
        break;
    }
  }

  void shuffle() {
    face_shuf = 0;
    position_shuf = 0;
    estado_shuf = 0;
    erros_shuf = 0; // Variavel q conta erros da classificação
    for (int j; j < 6; j++) {progression_shuf[j] = 0;}

    while(1) {
      
      // Bloco Sensoriamento Embaralhamento
        int NS = 2*face_shuf + position_shuf;

        // Leitura
        MUX(NS);
        float r_NS, g_NS, b_NS, sum_NS;
        sensor_rgb(r_NS, g_NS, b_NS, sum_NS);
        r_NS /= sum_NS;
        g_NS /= sum_NS;
        b_NS /= sum_NS;
        
        float hue, sat, val;
        rgbToHsv(r_NS, g_NS, b_NS, hue, sat, val);
        
        // Classifica a cor retornando rótulo
        char color;
        classific(hue, sat, val, color);

        // Armazena Cor classificada
        int b = progression_shuf[face_shuf];
        m_shuffle[face_shuf][b] = color;

        estado_shuf++;
        progression_shuf[face_shuf]++;
      //
    
      if (position_shuf == 0){
        position_shuf = 1;
        continue;
      }
    
      position_shuf = 0;    
    
      if (estado_shuf == 48) { // Condição de término
        Serial.print("Número de Erros Leitura:");
        Serial.println(erros_shuf);

        imprimirShuf();
        break;
      }
      
      int a = estado_shuf>>1;
      face_shuf = seq_faces_shuf[a];
    
      if (flags_move_shuf[a]) {
        // Executa movimentos da string
        for (int i = 0; seq_moves_shuf[a][i] != '\0'; i++) {
          executarSimples(seq_moves_shuf[a][i]);
        } 
      }
    }
  }
//