"""Tipos compartilhados entre os orquestradores (main_*.py).

Lar neutro para evitar import circular: os flows e o main_raiden importam
daqui, e este módulo não importa nenhum deles.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class StepResult:
    """Retorno único de toda etapa/fluxo do host.

    ok:      seguir (True) ou parar (False); a UI colore verde/vermelho.
    step:    qual etapa produziu (ex.: "scan", "calibrate", "sense", "execute").
    data:    payload no sucesso (matriz 6x8, dict de calibração/solução, tempo).
    error:   código e<n> do firmware quando falhou (senão None).
    message: texto pronto para print/log/UI.
    """
    ok: bool
    step: str
    data: Any = None
    error: Optional[int] = None
    message: str = ""