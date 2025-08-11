import z3
import typing as t

from lark import Lark, Transformer, Token
from pathlib import Path

from .. import ConstraintsBuilder


class Parser(Transformer):
	"""
	A class to handle parsing of constraints using the Lark parser.
	"""
	def __init__(self, builder: ConstraintsBuilder):
		"""
		Initialize the Parser instance.
		"""
		
		self.__builder = builder

		grammar_path = Path(__file__).parent / "grammar.lark"
		with grammar_path.open("r") as fp:						
			self.__parser = Lark(grammar=fp)

	@staticmethod
	def __mk_cnstr(builder: t.Callable[[str], z3.BoolRef], token: str) -> z3.BoolRef:
		cnstr = token.split('.', 2)
		return builder(cnstr[1])

	def __mk_bool_expr(self, ctor, *args) -> z3.BoolRef:
		return t.cast(z3.BoolRef, ctor(*args, self.__builder.context)) 

	def parse_cnstr(self, cnstr: str) -> z3.BoolRef:
		"""
		Parse the given text using the Lark parser.
		
		:param text: The text to parse.
		:return: The parsed result.
		"""
		tree = self.__parser.parse(cnstr)
		return self.transform(tree)

	"""
	Transformer methods to handle the parsed tree.
	Each method corresponds to a rule in the grammar.
	"""
	def neg_symbol(self, items) -> z3.BoolRef:
			return self.__mk_bool_expr(z3.Not, items[0])

	def and_op(self, items) -> z3.BoolRef:
			return self.__mk_bool_expr(z3.And, items)

	def or_op(self, items) -> z3.BoolRef:
			return self.__mk_bool_expr(z3.Or, items)
	
	def xor_op(self, items) -> z3.BoolRef:
			return self.__mk_bool_expr(z3.Xor, items)
	
	def not_(self, items) -> z3.BoolRef:
			return self.__mk_bool_expr(z3.Not, items[0])
	
	def implies_op(self, items) -> z3.BoolRef:			
			return self.__mk_bool_expr(z3.Implies, items[0], items[1])						
	
	def ite_op(self, items) -> z3.BoolRef:
			# items: [cond, true_branch, false_branch]
			return self.__mk_bool_expr(z3.If, items[0], items[1], items[2])						

	def true_val(self, _) -> z3.BoolRef:
			return self.__mk_bool_expr(z3.BoolVal, True)
				
	def false_val(self, _) -> z3.BoolRef:
			return self.__mk_bool_expr(z3.BoolVal, False)

	def license_op(self, items) -> z3.BoolRef:
		return self.__builder.makeLicenseNameExpr(items[0])


	def ESCAPED_STRING(self, token: Token) -> str:
			# Return the token as a string, removing the quotes
			return token[1:-1]

	def CONST(self, token: Token) -> z3.BoolRef:
			# TODO: Handle constants properly
			return t.cast(z3.BoolRef, self.__builder.makeComponentCnstrExpr(token))
			# return t.cast(z3.BoolRef, z3.Const(token, z3.BoolSort(self.__builder.context))) 		

	def MODULE_PROP(self, token: Token) -> z3.BoolRef:
			return self.__mk_cnstr(self.__builder.makeModuleCnstrExpr, token)

	def COMPONENT_PROP(self, token: Token) -> z3.BoolRef:
			return self.__mk_cnstr(self.__builder.makeComponentCnstrExpr, token)

	def LICENSE_PROP(self, token: Token) -> z3.BoolRef:
			return self.__mk_cnstr(self.__builder.makeLicenseCnstrExpr, token)