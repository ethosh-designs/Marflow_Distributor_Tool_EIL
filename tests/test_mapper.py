from src.core.grammar.registry import GrammarRegistry
from src.core.mapper.abbreviation_mapper import map_features_to_segments
from src.core.parser.feature_extractor import extract_features


def test_mapper_sets_numeric_segments() -> None:
	grammar_json = {
		"MFUXXDDLL": {
			"name": "SAMPLE",
			"segments": {
				"MF": "Marflow",
				"U": "Urology",
				"XX": {"01": "Blue"},
				"DD": "Size in FR",
				"LL": "Length in CM",
			},
		}
	}

	registry = GrammarRegistry(grammar_json)
	grammar = registry.get("MFUXXDDLL")
	features = extract_features("BLUE 04 FR 70 CM")
	mapped = map_features_to_segments(features, grammar)

	assert mapped.values["DD"] == "04"
	assert mapped.values["LL"] == "70"
	assert mapped.values["XX"] == "01"
