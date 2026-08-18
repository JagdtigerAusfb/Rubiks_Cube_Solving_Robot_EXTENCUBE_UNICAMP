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
