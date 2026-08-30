"""Orquestra as regras do sensoriamento (as "regras do jogo").

Princípio primordial: nenhum método espera sozinho. Cada ETAPA faz um comando
serial, aplica sua regra de decisão, retorna um StepResult e PARA. Quem
encadeia é o chamador (terminal hoje; main_raiden/UI depois).

Dois níveis, mesma classe:
  - Etapas atômicas (scan, calibrate, sense): chamáveis sozinhas — passo-a-passo
    e tratamento de erro isolado.
  - Fluxos (prepare, read_for_solution): encadeiam etapas e param na 1ª falha.

Falha do firmware (e<n>) vira StepResult(ok=False) — a UI lê .ok sem try/except.
Só ProtocolError (timeout/conexão) propaga como exceção: é infraestrutura, não
um estado de fluxo.
"""

from dataclasses import dataclass
from typing import Any, Optional
from common import StepResult

from app.communication.embedded import (
    CalibrationReadError,
    CalibrationPremiseError,
    SenseIncompleteError,
)

class SensorFlow:
    """Etapas atômicas do sensoriamento + fluxos que as encadeiam.

    Recebe o link serial global (injetado) — não abre porta nem conhece
    transporte. Lembra se já calibrou, para avisar sense() sem calibração.
    """

    def __init__(self, link):
        self._link = link
        self._calibrated = False

    # ------------------------------------------------------------------
    # Etapas atômicas — uma por comando serial, chamáveis isoladamente
    # ------------------------------------------------------------------
    def scan(self) -> StepResult:
        """s0* — self-check de hardware. ok se os 12 sensores respondem."""
        bools = self._link.scan()                 # ProtocolError propaga
        if all(bools):
            return StepResult(True, "scan", data=bools,
                              message="Hardware íntegro: 12 sensores OK.")
        mudos = [i for i, ok in enumerate(bools) if not ok]
        return StepResult(False, "scan", data=bools,
                          message=f"Sensores mudos nos canais físicos {mudos}. "
                                  f"Verifique fiação/conexão e repita o scan.")

    def calibrate(self) -> StepResult:
        """c0* — calibração (cubo resolvido). ok se as premissas passam."""
        try:
            cal = self._link.calibrate()          # dict OU e4/e5
        except CalibrationReadError:
            self._calibrated = False
            return StepResult(False, "calibrate", error=4,
                              message="Calibração falhou: algum sensor sem "
                                      "leitura válida. Verifique iluminação/mux.")
        except CalibrationPremiseError:
            self._calibrated = False
            return StepResult(False, "calibrate", error=5,
                              message="Calibração violou as premissas (branco não "
                                      "dessaturou, cor morta ou reflexo no branco). "
                                      "Recalibre sem reflexo, cubo resolvido.")
        self._calibrated = True
        return StepResult(True, "calibrate", data=cal,
                          message=f"Calibração OK. Limiar de branco="
                                  f"{cal['white_sat_thresh']:.3f}, "
                                  f"balanço={cal['white_balance']}.")

    def sense(self) -> StepResult:
        """r0* — leitura do embaralhamento. ok se estado completo (sem X)."""
        if not self._calibrated:
            # Avisa, mas NÃO bloqueia (o firmware pode ter calibração anterior).
            aviso = " (atenção: nenhuma calibração feita nesta sessão)"
        else:
            aviso = ""
        try:
            state = self._link.sense()            # matriz 6x8 OU e6
        except SenseIncompleteError:
            return StepResult(False, "sense", error=6,
                              message="Leitura incompleta: um ou mais adesivos "
                                      "vieram inválidos (X). Repita o sense." + aviso)
        return StepResult(True, "sense", data=state,
                          message="Estado do cubo lido (matriz 6x8)." + aviso)

    # ------------------------------------------------------------------
    # Fluxos — encadeiam etapas e PARAM na primeira falha
    # ------------------------------------------------------------------
    def prepare(self) -> StepResult:
        """Momento 1 (botão solver, parte A): scan -> calibrate.

        Retorna o resultado da etapa que parou o fluxo: a falha do scan, ou
        o resultado final da calibração. O chamador decide reparo + retry.
        """
        r = self.scan()
        if not r.ok:
            return r
        return self.calibrate()

    def read_for_solution(self) -> StepResult:
        """Momento 2 (botão solver, parte B): scan -> sense.

        Revalida o hardware e lê o estado. Retorna a falha do scan, ou o
        resultado do sense (estado pronto para o solver, ou falha e6).
        """
        r = self.scan()
        if not r.ok:
            return r
        return self.sense()

    # ------------------------------------------------------------------
    @property
    def calibrated(self) -> bool:
        """Se houve calibração bem-sucedida nesta sessão."""
        return self._calibrated