import json

from src.core.resolver import ProductCodeResolver


def _write_file(path, content: str) -> None:
	path.write_text(content, encoding="utf-8")


def test_resolver_returns_constructed_code(tmp_path) -> None:
	grammar = {
		"MFUUCVDDLLH": {
			"name": "CYSTO CATHETER & SET",
			"segments": {
				"MF": "Marflow AG",
				"U": "Urology",
				"UC": "Ureteral Catheter",
				"V": {"1": "OPEN END PREMIUM BLUE"},
				"DD": "Size in FR",
				"LL": "Length in CM",
				"H": "Hydrophilic coating",
			},
		}
	}
	grammar_path = tmp_path / "index_docs.json"
	_write_file(grammar_path, json.dumps(grammar))

	master_path = tmp_path / "master.csv"
	_write_file(
		master_path,
		"product_code,product_description\nMFUUC10470H,URETERAL CATHETER BLUE OPEN END PREMIUM 04 FR 70 CM HYDROPHILIC\n",
	)

	resolver = ProductCodeResolver(grammar_path=grammar_path, master_path=master_path)
	result = resolver.resolve(
		"URETERAL CATHETER BLUE (OPEN END-PREMIUM) 04.0 FR 70 CM WITH HYDROPHILIC COATED"
	)

	assert result["resolved_code"] == "MFUUC10470H"
	assert result["method"] == "constructed"
	assert result["confidence"] == "high"


def test_resolver_fallback_when_constructed_not_found(tmp_path) -> None:
	grammar = {
		"MFUUCVDDLLH": {
			"name": "CYSTO CATHETER & SET",
			"segments": {
				"MF": "Marflow AG",
				"U": "Urology",
				"UC": "Ureteral Catheter",
				"V": {"1": "OPEN END PREMIUM BLUE"},
				"DD": "Size in FR",
				"LL": "Length in CM",
				"H": "Hydrophilic coating",
			},
		}
	}
	grammar_path = tmp_path / "index_docs.json"
	_write_file(grammar_path, json.dumps(grammar))

	master_path = tmp_path / "master.csv"
	_write_file(
		master_path,
		(
			"product_code,product_description\n"
			"MFUUC20470H,URETERAL CATHETER BLUE OPEN END PREMIUM 04 FR 70 CM HYDROPHILIC\n"
			"MFUUC10660H,URETERAL CATHETER BLUE OPEN END 06 FR 60 CM HYDROPHILIC\n"
		),
	)

	resolver = ProductCodeResolver(grammar_path=grammar_path, master_path=master_path)
	result = resolver.resolve(
		"URETERAL CATHETER BLUE (OPEN END-PREMIUM) 04.0 FR 70 CM WITH HYDROPHILIC COATED"
	)

	assert result["resolved_code"] == "MFUUC20470H"
	assert result["method"] == "matched"
	assert result["confidence"] in {"medium", "low"}


def test_resolver_uc_variant_mapping_open_end_and_cone_tip(tmp_path) -> None:
	grammar = {
		"MFUUCVDDLLH": {
			"name": "CYSTO CATHETER & SET",
			"segments": {
				"MF": "Marflow AG",
				"U": "Urology",
				"UC": "Ureteral Catheter",
				"V": {
					"10": "OPEN END PREMIUM",
					"13": "CONE TIP",
					"14": "BULB TIP",
				},
				"DD": "Size in FR",
				"LL": "Length in CM",
				"H": "Hydrophilic coating",
			},
		}
	}
	grammar_path = tmp_path / "index_docs.json"
	_write_file(grammar_path, json.dumps(grammar))

	master_path = tmp_path / "master.csv"
	_write_file(
		master_path,
		(
			"product_code,product_description\n"
			"MFUUC100470H,URETERAL CATHETER OPEN END 04 FR 70 CM HYDROPHILIC\n"
			"MFUUC130670H,URETERAL CATHETER CONE TIP WITH STYLET 06 FR 70 CM HYDROPHILIC\n"
		),
	)

	resolver = ProductCodeResolver(grammar_path=grammar_path, master_path=master_path)

	open_end_result = resolver.resolve("URETERAL CATHETER OPEN END 04 FR 70 CM WITH HYDROPHILIC COATED")
	assert open_end_result["resolved_code"] == "MFUUC100470H"
	assert open_end_result["method"] == "constructed"

	cone_tip_result = resolver.resolve("URETERAL CATHETER CONE TIP WITH STYLET 06 FR 70 CM HYDROPHILIC")
	assert cone_tip_result["resolved_code"] == "MFUUC130670H"
	assert cone_tip_result["method"] == "constructed"
