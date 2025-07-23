import sys

from lark import Lark, Transformer
from pathlib import Path

try:
	grammar_path = Path(__file__).parent / "grammar.lark"
	
	with grammar_path.open("r") as fp:
		parser = Lark(grammar=fp)

	result = parser.parse(sys.argv[1])
		
	print(result)

except Exception as e:
	print(f"Error parsing text: {e}")