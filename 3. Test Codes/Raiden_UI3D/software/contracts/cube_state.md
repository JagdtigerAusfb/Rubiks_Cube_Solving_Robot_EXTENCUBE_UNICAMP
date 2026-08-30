# Contrato: Estado do Cubo (6×8 = 48) — entrada do solver

Pacote padronizado do estado do cubo. É o handoff sensoriamento -> solver
e o formato consumido pelo grupo `solver/` para a busca da solução.

## Dimensão

54 adesivos no cubo, 6 centros fixos -> 48 adesivos móveis -> matriz 6×8.

## Cor já classificada no FIRMWARE

O firmware executa RGB -> HSV -> distância mínima (Algoritmo 1) e devolve a
cor JÁ classificada. O pacote carrega 48 chars de cor, não RGB cru.

Alfabeto de cor (Tab. C.2):

|Char|Cor|
|-|-|
|W|Branca|
|G|Verde|
|R|Vermelha|
|O|Laranja|
|Y|Amarela|
|B|Azul|

## Ordem das faces (linhas 0..5)

&#x20;   U(branca)  R  F(verde)  D  L  B      ==  U R F D L B


Convenção física do robô: face branca sempre para cima, face verde sempre
à frente (motor designado como frente).

## Ordem de leitura dentro de cada face

Sentido horário, começando pela peça superior esquerda, 8 posições
(pula o centro).

## Indexação

&#x20;   índice do adesivo = face \* 8 + posição      (0..47)
    face ∈ {0..5} na ordem URFDLB acima
    posição ∈ {0..7} na ordem horária acima


## Centros

Implícitos/fixos por convenção (não são sensoriados). O adapter do
`solver/` reconstrói os 54 facelets inserindo os 6 centros conhecidos e
reordenando cada face para o formato exigido pela biblioteca de solução.

`firmware/src/protocol/cube\_state.h` espelha este schema.

