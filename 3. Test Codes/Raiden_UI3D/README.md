# Raiden — Robô Solucionador de Cubo Mágico

Projeto de extensão (FEEC/UNICAMP) que integra sensoriamento, cálculo da
solução e movimentação num robô solucionador de cubo mágico.

## Organização
- `software/`  — todo o código (host em Python + firmware em C++).
- `hardware/`  — datasheets e material de eletrônica (motores, sensores).
- `structure/` — modelos 3D (CAD) da estrutura do robô.
- `classroom/` — material das oficinas de extensão.
- `dependencies/` — bibliotecas, executáveis e repositórios externos.

## software/
Duas linguagens, duas fronteiras claras, ligadas por 3 contratos versionados:
- `contracts/` — fonte única de verdade (alfabeto de movimentos, protocolo
  serial, schema do estado do cubo).
- `host/`      — Python: orquestra, configura, seleciona e **calcula a solução**.
- `firmware/`  — C++: um único binário do Arduino que **processa** (sensores
  e motores).

## Interface gráfica (host)

O host tem duas peles sobre o MESMO sistema (mesma classe `Raiden`, mesmos
flows de `sensor/`, `solver/` e `execution/`):

```
cd software/host
python raiden.py                 # GUI 3D (padrão)
python raiden.py --mode demo     # GUI sem hardware (serial simulada)
python raiden.py --port COM5     # força a porta
python raiden.py --terminal      # menu de terminal (o de sempre)
```

A GUI mostra o cubo 3D sendo **sensoriado** (os 48 adesivos acendem face a
face, na ordem de contrato) e depois sendo **resolvido** (replay dos giros
enquanto o robô executa), com contador de movimentos, cronômetro e mapa dos
12 sensores. A aba lateral repete os MESMOS números do menu de terminal.

O cronômetro (TEMPO) mede o ciclo do cubo: começa no `r0*` (sensoriamento)
e para quando a worker terminou E o cubo 3D acabou de mostrar o resultado —
o que durar mais. Conectar, escanear, calibrar ou mudar velocidade não
entram na conta. A linha menor (`motores`) é o `d_<seg>*` puro do firmware,
para separar mecânica de leitura/cálculo.

| Tecla | Ação |
|-|-|
|1|Preparar (scan + calibração)|
|2|Resolver + Executar (sense › solve › exec)|
|3 4 5 6|Scan · Calibrar · Sensoriar · Resolver|
|7|Executar sequência (chars A–R; vem preenchida com a última solução)|
|8|Alterna o método do solver|
|9 (ou S)|Painel de configuração: modo, porta, método, velocidade, pausa|
|R L U D F B|Gira a face no cubo virtual e envia o movimento ao robô|
|Shift + giro|Anti-horário · **Ctrl + giro**: 180°|
|C|Reposiciona o cubo virtual (resolvido) — só visual|
|0 ou ESC|Sair|

No painel de configuração: `↑↓` troca de campo, `←→` alterna as opções,
dígitos/letras editam. **Método, velocidade e pausa são aplicados sozinhos**
ao sair do campo ou fechar o painel — `ENTER` só antecipa. Modo e porta
reabrem o link, então exigem `ENTER` explícito e voltam ao valor real no `ESC`.

Velocidade (`v_<us>*`) é o `delayMicroseconds` de cada nível do pulso STEP:
o período de um passo é 2×esse valor. Pausa (`g_<ms>*`) é o `delay` após
cada movimento (ou após cada par de faces opostas acionado junto). Ao
conectar, a GUI envia os dois valores do painel para a placa, que reseta ao
abrir a porta e voltaria aos próprios defaults.

### Dependências do host
`pip install -r software/host/requirements.txt`
(pyserial, kociemba para o solver, e pygame + PyOpenGL para a GUI 3D).

### Nota de contrato (2026)
`host/solver/base.py` estava mapeando os movimentos na ordem URFDLB
(`R`→`D`, `F`→`G`, `D`→`J`, `L`→`M`), divergindo de
`contracts/move_alphabet.md` e da LUT de `firmware/src/motion/motion.cpp`,
que usam a ordem U,D,L,R,F,B. Na prática o host pedia "R" e o robô girava
"D". `MOVE_TABLE` foi alinhada ao contrato (fonte única) — `U` e `B` já
estavam certos; `R`↔`D` e `F`↔`L` foram desfeitos.
