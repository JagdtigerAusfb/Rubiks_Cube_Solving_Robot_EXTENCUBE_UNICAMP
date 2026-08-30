"""Comunicação entre os main_*.py.

FUTURO: event bus (publish/subscribe) — sensor publica 'estado pronto',
solver 'solução calculada', GUI reage. Será formalizado quando a UI
consolidar.

POR ENQUANTO: operação via terminal é sequencial e direta (cada main_*.py
chama o próximo), então não há barramento ativo. Placeholder intencional
para não antecipar complexidade antes da UI.
"""

# TODO(event-bus): publish(topic, payload) / subscribe(topic, handler)