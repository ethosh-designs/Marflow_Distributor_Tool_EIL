from __future__ import annotations

from src.core.grammar.registry import GrammarDefinition
from src.core.mapper.abbreviation_mapper import MappedSegments, map_features_to_segments
from src.core.parser.feature_extractor import ExtractedFeatures


def map_description_features(features: ExtractedFeatures, grammar: GrammarDefinition) -> MappedSegments:
    return map_features_to_segments(features, grammar)
