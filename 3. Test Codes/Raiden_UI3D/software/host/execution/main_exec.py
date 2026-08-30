"""Orquestra a execução dos movimentos (regras do jogo da movimentação).

Estratégia: SEQUÊNCIA INTEIRA num único MOVE. O host envia a robot_sequence
completa (chars A–R) terminada em '*', o firmware executa tudo de uma vez
(aproveitando a otimização de faces opostas) e responde um único d_<seg>*.
O firmware fica "surdo" durante a execução — aceitável por ora.

Espelha SensorFlow/SolverFlow: etapas atômicas + StepResult de retorno.
"""

import logging

# StepResult é o tipo de resultado compartilhado pelos flows do host.
# (Ao montar main_raiden, avaliar mover para um lar comum.)
from common import StepResult
from app.communication.embedded import InvalidMoveError

logger = logging.getLogger(__name__)


class ExecFlow:
    """Executa a sequência de solução em um único envio, sobre o link serial.

    Recebe o link global injetado — não abre porta nem conhece transporte.
    """

    def __init__(self, link):
        self._link = link

    # ------------------------------------------------------------------
    # Config (útil para demo: devagar para ver, rápido para o recorde)
    # ------------------------------------------------------------------
    def set_speed(self, us: int) -> StepResult:
        """v_<us>* — delay do passo em µs. Menor = mais rápido."""
        self._link.set_speed(us)                 # ProtocolError propaga
        return StepResult(True, "set_speed", data=us,
                          message=f"Velocidade ajustada: {us} µs/passo.")

    def set_gap(self, ms: int) -> StepResult:
        """g_<ms>* — pausa entre movimentos em ms."""
        self._link.set_gap(ms)
        return StepResult(True, "set_gap", data=ms,
                          message=f"Pausa entre movimentos: {ms} ms.")

    # ------------------------------------------------------------------
    # Etapa atômica — executa a sequência INTEIRA num MOVE só
    # ------------------------------------------------------------------
    def execute_sequence(self, sequence: str) -> StepResult:
        """Envia a sequência completa de chars A–R e aguarda o d_<seg>* final.

        O tempo de execução reportado pelo firmware fica em .data (segundos).
        Sequência vazia é sucesso trivial (nada a fazer).
        """
        if not sequence:
            return StepResult(True, "execute", data=0.0,
                              message="Sequência vazia — nada a executar.")
        try:
            secs = self._link.move(sequence)      # 'KNI...*' -> d_<seg>*
        except ValueError as e:                    # barrado no host (char fora de A–R)
            return StepResult(False, "execute",
                              message=f"Sequência inválida no host: {e}")
        except InvalidMoveError:                   # firmware recusou (e1)
            return StepResult(False, "execute", error=1,
                              message="Firmware recusou a sequência (e1): "
                                      "char fora de A–R.")
        logger.info("Sequência de %d movimentos executada em %.3fs",
                    len(sequence), secs)
        return StepResult(True, "execute", data=secs,
                          message=f"{len(sequence)} movimentos executados "
                                  f"em {secs:.3f}s.")