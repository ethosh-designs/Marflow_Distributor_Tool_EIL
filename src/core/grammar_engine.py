from __future__ import annotations

from src.core.grammar.registry import GrammarDefinition


def grammar_order(grammar: GrammarDefinition) -> list[str]:
    return [segment.name for segment in grammar.segments]
