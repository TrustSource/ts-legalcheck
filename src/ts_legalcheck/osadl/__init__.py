import sys

from pathlib import Path

from .download import download_files_from_url_list

from .transformer.RulesTransformer import RulesTransformer
from .transformer.ConstraintsExtractor import ConstraintsExtractor


def download_lang(output_directory: str):
	download_files_from_url_list(
		"https://www.osadl.org/fileadmin/checklists/all/language.txt",
		output_directory,
	)


def download_license(output_directory: str):
	download_files_from_url_list(
		"https://www.osadl.org/fileadmin/checklists/all/jsonlicenses.txt",
		output_directory,
	)


def create_defs(input_file: Path, 
								output_dir: Path, 
								transformer: RulesTransformer = RulesTransformer()):
	"""
	Create definitions from the input file and save them to the output directory.
	"""
	import json
	import toml

	with input_file.open("r") as fp:
		data = json.load(fp)

	transformed_data = transformer.transform(data)

	rules = [{'key': key, 'require': f"(implies (license \"{key}\") {val})"} 
					for key, val in transformed_data.items()]

	defs = {
		"Constraints": {key: {} for key in transformed_data.keys()},
		"Obligations": {val['key']: {'name': val['name']} for val in transformer.obligations.values()},
		"Properties": {val['key']: {'name': val['name']} for val in transformer.properties.values()},
		"Rules": rules
	}

	output_file = output_dir / f"{input_file.stem}.toml"
	with output_file.open("w") as f:
		toml.dump(defs, f)


def create_processed_file(input_file: Path, output_dir: Path):
	"""
	Create a processed file from the input file and save it to the output directory.
	A processed file contains checklists where all properties and obligations are replaced by unique identifiers.
	"""
	import json

	with input_file.open("r") as fp:
		data = json.load(fp)
	
	transformer = ConstraintsExtractor()
	transformed_data = transformer.transform(data)

	output_file = output_dir / f"{input_file.stem}.json"
	with output_file.open("w") as f:
		json.dump(transformed_data, f, indent=2)