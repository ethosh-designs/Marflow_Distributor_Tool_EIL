from src.core.parser.feature_extractor import extract_features


def test_extract_features_numeric_and_tokens() -> None:
	text = "URETERAL CATHETER BLUE (OPEN END-PREMIUM) 04.0 FR 70 CM WITH HYDROPHILIC COATED - CURVED"
	features = extract_features(text)

	assert features.size_fr == 4
	assert features.length_cm == 70
	assert features.color == "BLUE"
	assert features.coating_hydrophilic is True
	assert features.open_end is True
	assert features.premium is True
	assert features.curved is True


def test_extract_features_variant_and_stylet_flags() -> None:
	text = "URETERAL CATHETER CONE TIP WITH STYLET 06 FR 70 CM"
	features = extract_features(text)

	assert features.cone_tip is True
	assert features.bulb_tip is False
	assert features.with_stylet is True
