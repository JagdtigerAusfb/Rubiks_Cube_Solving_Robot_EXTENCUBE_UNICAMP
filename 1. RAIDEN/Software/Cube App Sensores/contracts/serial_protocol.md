# Contrato: Protocolo Serial (host <-> firmware)

Um único link serial. Host é MESTRE, firmware é ESCRAVO: o firmware só age
em resposta a um comando e nunca toma iniciativa própria.

Baud: 115200 (deve casar com host/app/communication/embedded.py).
Ao ligar/resetar, o firmware emite o banner: READY\*

## Formato das mensagens

* Todo comando e toda resposta terminam no delimitador '\*'.
* Args opcionais após o código, separados por '\_'.
* Sem checksum nesta versão (manter simples).
* O firmware lê incrementalmente até o '\*' — nunca acumula a sequência
inteira de uma vez, então não estoura o buffer serial (\~64 bytes).

## Host -> Firmware (comandos)

|Comando|Código na serial|Ação|
|-|-|-|
|CALIBRATE|c0\*|calibra (cubo resolvido) -> devolve 6 HUEs globais|
|SCAN|s0\*|self-check de hardware -> responde SCAN-MAP|
|SENSE|r0\*|sensoriamento completo -> responde STATE|
|MOVE|<chars>\*  (ex: J\* ou ADJ\*)|executa 1..N movimentos A–R (ver abaixo)|
|SPEED|v\_<us>\*   (ex: v\_850\*)|ajusta o delay do passo em µs (stress test)|
|GAP|g\_<ms>\*   (ex: g\_10\*)|ajusta a pausa entre movimentos em ms|

Os códigos-letra vivem apenas aqui e em protocol.h — trocá-los é barato.

### MOVE (1..N chars)

O corpo é uma sequência de 1 ou mais chars do alfabeto A–R
(contracts/move\_alphabet.md). Um movimento único é só o caso N=1.
O firmware executa a sequência aplicando a otimização de faces opostas
(dois motores acionados simultaneamente quando dois movimentos
consecutivos são de faces opostas) e responde UM único DONE ao final.

## Firmware -> Host (respostas)

|Resposta|Formato na serial|Quando|
|-|-|-|
|READY|READY\*|boot/reset|
|DONE|d\_<seg>\*  (ex: d\_1.820\*)|comando/sequência concluída|
|STATE|<48 chars W/G/R/O/Y/B>\*|resposta ao r0\* (SENSE)|
|SCAN-MAP|<12 chars 1/0>\*  (ex: 111111111111\*)|resposta ao s0\* (SCAN)|
|ERROR|e<n>\*|falha (ver códigos)|

DONE carrega, no arg opcional, o tempo de execução em segundos. O host
pode usar (telemetria) ou ignorar.

### SCAN (s0\*)

Resposta: 12 chars, um por sensor na ordem de canal 0..11 do mux.
'1' = sensor respondeu (ID lido via I2C), '0' = não respondeu.
Tudo '1' = hardware íntegro; cada '0' localiza o sensor mudo.

### CALIBRATE (c0\*) — cubo resolvido, sem movimento

Estabelece o balanço de branco (resposta do sensor à face branca) e deriva
as referências no espaço balanceado. O branco é classificado por saturação
(agora acromático), as demais por hue.
Resposta: 6 HUEs \_ 6 saturações \_ whiteSatThresh \_ wR \_ wG \_ wB, tudo
separado por '\_' e terminado em '\*'. Ordem de cor: W R G Y O B.

### Códigos de erro

|Código|Significado|
|-|-|
|e0\*|comando desconhecido|
|e1\*|char de movimento inválido (fora A–R)|
|e2\*|overflow da linha de recepção|
|e3\*|índice de sensor inválido|
|e4\*|calibração falhou: sensor sem leitura válida|
|e5\*|calibração violou premissas (branco não dessaturou,|
||cromática morta, ou reflexo no branco) — ver sensor\_map.md|
|e6\*|sensoriamento incompleto: uma ou mais leituras 'X'|
|e9\*|comando ainda não implementado (stub)|

## Handshake (controle de fluxo mestre/escravo)

O host envia UM comando (que pode ser uma sequência inteira de movimentos)
e AGUARDA a resposta (d\_<seg>\*, STATE ou SCAN-MAP) antes de enviar o
próximo.

## Fluxo do SENSE

Ao receber r0\*, o firmware sozinho aciona os motores (via motion/) para
girar e apresentar as faces aos sensores, faz a leitura/classificação e
só então devolve STATE. O host não comanda motor durante o sensoriamento.

