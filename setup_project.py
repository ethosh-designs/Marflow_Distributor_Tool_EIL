import os

# Base project name
BASE_DIR = "marflow-code-engine"

# Structure definition
STRUCTURE = {
    "data": {
        "raw": [
            "master_list.csv",
            "index_docs.pdf",
        ],
        "processed": {
            "": [
                "structured_products.parquet",
                "grammar.json",
            ],
            "legends": [
                "global.csv",
                "product.csv",
                "code.csv",
            ],
        },
    },
    "src": {
        "core": {
            "grammar": [
                "loader.py",
                "validator.py",
                "registry.py",
            ],
            "parser": [
                "family_detector.py",
                "tokenizer.py",
                "feature_extractor.py",
            ],
            "mapper": [
                "abbreviation_mapper.py",
                "reverse_mapper.py",
            ],
            "compiler": [
                "code_builder.py",
                "formatter.py",
            ],
            "matcher": [
                "exact_match.py",
                "scoring_engine.py",
            ],
            "": [
                "resolver.py",
            ],
        },
        "pipeline": {
            "ingest": [
                "csv_loader.py",
                "pdf_parser.py",
            ],
            "transform": [
                "master_parser.py",
                "grammar_builder.py",
                "legend_generator.py",
            ],
            "build": [
                "index_builder.py",
                "db_loader.py",
            ],
        },
        "db": [
            "models.py",
            "queries.py",
            "connection.py",
        ],
        "api": {
            "": [
                "main.py",
            ],
            "routes": [
                "resolve.py",
                "validate.py",
            ],
        },
        "utils": [
            "regex.py",
            "normalizer.py",
            "logger.py",
        ],
    },
    "scripts": [
        "build_grammar.py",
        "generate_legends.py",
        "preprocess_master.py",
    ],
    "tests": [
        "test_parser.py",
        "test_mapper.py",
        "test_resolver.py",
    ],
    "config": [
        "settings.yaml",
        "mappings.yaml",
    ],
    "": [
        "requirements.txt",
        "README.md",
    ],
}


def create_structure(base_path, structure):
    for name, content in structure.items():
        current_path = os.path.join(base_path, name) if name else base_path

        if isinstance(content, dict):
            os.makedirs(current_path, exist_ok=True)
            create_structure(current_path, content)

        elif isinstance(content, list):
            os.makedirs(current_path, exist_ok=True)
            for file in content:
                file_path = os.path.join(current_path, file)
                if not os.path.exists(file_path):
                    with open(file_path, "w") as f:
                        pass  # create empty file


def main():
    os.makedirs(BASE_DIR, exist_ok=True)
    create_structure(BASE_DIR, STRUCTURE)
    print(f"✅ Project '{BASE_DIR}' created successfully.")


if __name__ == "__main__":
    main()