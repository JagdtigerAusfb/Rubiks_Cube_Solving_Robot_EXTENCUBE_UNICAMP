# Contrato: Alfabeto de Movimentos (A–R)

Fonte única de verdade da notação de movimentos (Tabela 1 do artigo).
O byte enviado na serial é o caractere ASCII 'A'..'R' — 1 byte por
movimento, para máxima velocidade de comunicação.

## Onde a tradução acontece (toda no HOST)
    solver resolve -> notação de cubo (U, U', U2, ...)
      -> host/solver/base.py traduz para o char 'A'..'R' (to_robot_sequence)
      -> firmware recebe SÓ o char e o mapeia na LUT (índice 0..17)

MOVE_TABLE em host/solver/base.py é o espelho desta tabela no host.
(embedded.py NÃO traduz — apenas valida que os chars estão em A..R.)

O firmware nunca vê a notação de cubo mágico, apenas a letra.
`firmware/src/protocol/protocol.h` espelha esta tabela.

## Tabela canônica

|Notação|Descrição|Ângulo|Char|Índice LUT|
|-|-|-|-|-|
|U|Superior Horário|90°|A|0|
|U'|Superior Anti-horário|-90°|B|1|
|U2|Superior Duplo|180°|C|2|
|D|Inferior Horário|90°|D|3|
|D'|Inferior Anti-horário|-90°|E|4|
|D2|Inferior Duplo|180°|F|5|
|L|Esquerda Horário|90°|G|6|
|L'|Esquerda Anti-horário|-90°|H|7|
|L2|Esquerda Duplo|180°|I|8|
|R|Direita Horário|90°|J|9|
|R'|Direita Anti-horário|-90°|K|10|
|R2|Direita Duplo|180°|L|11|
|F|Frontal Horário|90°|M|12|
|F'|Frontal Anti-horário|-90°|N|13|
|F2|Frontal Duplo|180°|O|14|
|B|Traseira Horário|90°|P|15|
|B'|Traseira Anti-horário|-90°|Q|16|
|B2|Traseira Duplo|180°|R|17|

Índice LUT = (char - 'A'), de 0 a 17.

