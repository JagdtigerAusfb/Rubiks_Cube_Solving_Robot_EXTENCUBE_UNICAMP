# Contrato: Mapa e Nomenclatura dos Sensores

Identidade dos 12 TCS34725 e sua relação com faces, células e multiplexador.
Depende de: cube\_state.md (faces/índices) e move\_alphabet.md (movimentos).
Lib de sensor: TCS34725.h (hideakitai) — instância única re-selecionada via mux.

## Faces (idêntico a cube\_state.md)

U=0  R=1  F=2  D=3  L=4  B=5
HOME do robô: face branca (U) para cima, face verde (F) à frente.
Cor de cada face no HOME: U=Branca R=Vermelha F=Verde D=Amarela L=Laranja B=Azul.

## Dois sensores por face (nas células de menor índice)

* QUINA  (posição 0, tag 'q'): lê célula de canto  -> posição 0 da face
* CENTRO (posição 1, tag 'c'): lê célula de aresta -> posição 1 da face
"CENTRO" é o adesivo do meio-topo (aresta). NÃO é o centro fixo da face;
ambos os sensores leem adesivos MÓVEIS.

## Número do Sensor lógico (NS) e nomenclatura

NS lógico = 2\*face + posição       (posição: 0 = quina, 1 = centro)
Tag de 2 letras = \[inicial da face em inglês]\[papel: q=quina, c=centro]
As estruturas de dados usam SEMPRE o NS lógico (ordem de contrato).

|NS|Tag|Face|Papel|Cor no HOME|Canal físico do mux|
|-|-|-|-|-|-|
|0|Uq|Up (0)|quina|Branca|2|
|1|Uc|Up (0)|centro|Branca|3|
|2|Rq|Right (1)|quina|Vermelha|4|
|3|Rc|Right (1)|centro|Vermelha|5|
|4|Fq|Front (2)|quina|Verde|6|
|5|Fc|Front (2)|centro|Verde|7|
|6|Dq|Down (3)|quina|Amarela|10|
|7|Dc|Down (3)|centro|Amarela|11|
|8|Lq|Left (4)|quina|Laranja|8|
|9|Lc|Left (4)|centro|Laranja|9|
|10|Bq|Back (5)|quina|Azul|0|
|11|Bc|Back (5)|centro|Azul|1|

## Indireção fiação física (IMUTÁVEL — hardware pronto)

A fiação NÃO segue NS = 2\*face+posição. As estruturas de dados seguem a
ordem de contrato U,R,F,D,L,B; apenas a seleção do canal do mux é remapeada:

MUX\_CHANNEL\[NS lógico] = {2,3, 4,5, 6,7, 10,11, 8,9, 0,1}

Canais físicos por face: Back=0,1  Up=2,3  Right=4,5  Front=6,7
Left=8,9  Down=10,11

## Fiação (reprodutibilidade)

* Barramento compartilhado: VIN (5V), GND, SCL.
* Por sensor, via mux 74HC4067: SDA (obrigatório) e LED (opcional, retentivo).
* Seleção de canal = canal físico, com S0=LSB..S3=MSB e EN habilitando.
* Sem seleção individual de LED (limitação de cabeamento): o conjunto é
ligado/desligado por um único pino. Cross-talk mitigado por calibração e
leitura ocorrerem sob a mesma iluminação.
* Cores de jumper da bancada: LED=azul, SDA=verde, SCL=amarelo, GND=laranja,
VIN=vermelho.

## Calibração (versão atual: GLOBAL, cubo resolvido, sem movimento)

Pré-condição: cubo RESOLVIDO no HOME. Cada face mostra sua cor sólida aos
seus 2 sensores. Lêem-se os 12 sensores; para cada cor, faz-se a média
circular dos 2 sensores da respectiva face -> 1 HUE global por cor,
aplicado a TODOS os sensores (hipótese: sensores próximos).
Saída: globalRef\[6] (HSV; hoje só o HUE é usado na classificação).
Ordem das cores = ordem de contrato por índice de face: W,R,G,Y,O,B.
(Futuro documentado: referência por sensor 12x6 com a máquina de 72 estados.)

## Leitura (embaralhamento)

Saída: matriz 6x8 = 48 adesivos = o payload STATE do serial\_protocol,
na ordem de contrato (face U,R,F,D,L,B; posição horária a partir do topo-esq).

## Classificação

Distância angular de HUE entre a leitura e as 6 referências de globalRef;
menor distância vence. Guards: soma RGB < 5 ou saturação < 0.05 -> 'X'.

## Premissas de uma calibração válida (c0\*)

A estratégia de cor assume o seguinte, estabelecido empiricamente:

1. **Balanço de branco (von Kries).** O TCS34725 não responde a um alvo
neutro com R=G=B — os canais têm sensibilidades intrínsecas diferentes
(não é clipping; é invariante ao tempo de integração). A face branca
define whiteBal = {wR,wG,wB}; toda leitura é dividida por ele antes do
HSV. Sem isso o branco sai com hue/saturação falsos e colide com amarelo.
2. **Branco por saturação, cores por hue.** Após o balanço, o branco é
acromático (saturação baixa) e é classificado por s < whiteSatThresh.
As 5 cromáticas (R,G,Y,O,B) por menor distância angular de hue. O hue do
branco é IRRELEVANTE (ele nunca chega ao teste de hue).
3. **Tempo de integração equilibra o azul, não o branco.** O azul é a cor
de menor refletância; integração curta demais o mata (S(B)->0). Valor de
referência: \~50 ms. O branco NÃO precisa de integração curta (ver premissa 1).
4. **Cubo resolvido no HOME, sem reflexo especular.** Cada face mostra sua
cor sólida aos 2 sensores. Reflexo/brilho na face branca corrompe o
whiteBal e, por consequência, TODAS as cores.

### Critérios de aceitação (checar na resposta do c0\*)

Uma calibração é considerada BOA quando:

* S(W) é a MENOR das 6 saturações, com folga (ex.: S(W) < 0.5 \* menor S cromática).
* whiteSatThresh fica entre S(W) e a menor saturação cromática (não colado em nenhuma).
* Todas as 5 saturações cromáticas são altas (ex.: > 0.4). S(qualquer)\~0 = cor morta.
* wR, wG, wB são da mesma ordem de grandeza (nenhum \~0 nem um absurdamente maior).
* Os 6 hues cromáticos estão razoavelmente espalhados (o par mais próximo é R\~O).

### Referência de uma calibração boa (bancada, 2026)

280.9\_356.2\_132.1\_54.1\_0.6\_233.6\_0.086\_0.741\_0.624\_0.863\_0.961\_0.813\_0.355\_18\_18\_7
(H: W R G Y O B | S: W R G Y O B | whiteSatThresh | wR wG wB)
Nota: H(W)=280.9 é irrelevante por construção (branco resolvido por saturação).

