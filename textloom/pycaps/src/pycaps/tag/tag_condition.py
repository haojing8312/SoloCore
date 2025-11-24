from abc import ABC, abstractmethod
import ast
from typing import List
from pycaps.common import Tag
import re

class TagCondition(ABC):
    @abstractmethod
    def evaluate(self, tags: List[Tag]) -> bool:
        pass

class TagHasCondition(TagCondition):
    def __init__(self, tag: Tag):
        self.tag = tag

    def evaluate(self, tags: List[Tag]) -> bool:
        return any(self.tag.name == t.name for t in tags)

class TagNotCondition(TagCondition):
    def __init__(self, condition: TagCondition):
        self.condition = condition
    
    def evaluate(self, tags: List[Tag]) -> bool:
        return not self.condition.evaluate(tags)

class TagAndCondition(TagCondition):
    def __init__(self, *conditions: TagCondition):
        self.conditions = list(conditions)
    
    def evaluate(self, tags: List[Tag]) -> bool:
        return all(condition.evaluate(tags) for condition in self.conditions)

class TagOrCondition(TagCondition):
    def __init__(self, *conditions: TagCondition):
        self.conditions = list(conditions)
    
    def evaluate(self, tags: List[Tag]) -> bool:
        return any(condition.evaluate(tags) for condition in self.conditions)
    
class TagConditionFactory:
    @staticmethod
    def HAS(tag: Tag) -> TagCondition:
        return TagHasCondition(tag)
    
    @staticmethod
    def NOT(condition: 'TagCondition|Tag') -> TagCondition:
        if isinstance(condition, Tag):
            condition = TagHasCondition(condition)
        return TagNotCondition(condition)

    @staticmethod
    def AND(*conditions: 'TagCondition|Tag') -> TagCondition:
        conditions = [condition if isinstance(condition, TagCondition) else TagHasCondition(condition) for condition in conditions]
        return TagAndCondition(*conditions)
    
    @staticmethod
    def OR(*conditions: 'TagCondition|Tag') -> TagCondition:
        conditions = [condition if isinstance(condition, TagCondition) else TagHasCondition(condition) for condition in conditions]
        return TagOrCondition(*conditions)
    
    @staticmethod
    def TRUE() -> TagCondition:
        return TagAndCondition()
    
    @staticmethod
    def parse(expr: str) -> TagCondition:
        """
        Transforms a string like "'a' and ('b' or 'c')" into a TagCondition.
        """
        return _TagConditionParser.parse(expr)

class _TagConditionParser:
    OPS = {"and", "or", "not"}
    TOKEN_RE = re.compile(r"\band\b|\bor\b|\bnot\b|\(|\)|[^\s()]+", flags=re.IGNORECASE)

    @staticmethod
    def parse(expr: str) -> TagCondition:
        expr = _TagConditionParser.__auto_quote_by_ops(expr)
        tree = ast.parse(expr, mode="eval")
        return _TagConditionParser.__parse_condition_expr(tree.body)

    @staticmethod
    def __auto_quote_by_ops(expr: str) -> str:
        tokens = _TagConditionParser.TOKEN_RE.findall(expr)
        new_tokens = []
        for tok in tokens:
            lower = tok.lower()
            if lower in _TagConditionParser.OPS or tok in ("(", ")"):
                new_tokens.append(tok)
            else:
                new_tokens.append(f"'{tok}'")
        return " ".join(new_tokens)

    @staticmethod
    def __parse_condition_expr(node: ast.AST) -> TagCondition:
        if isinstance(node, ast.BoolOp):
            subconds = [_TagConditionParser.__parse_condition_expr(v) for v in node.values]
            if isinstance(node.op, ast.And):
                return TagConditionFactory.AND(*subconds)
            else:  # ast.Or
                return TagConditionFactory.OR(*subconds)

        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return TagConditionFactory.NOT(_TagConditionParser.__parse_condition_expr(node.operand))
        
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            return TagConditionFactory.HAS(Tag(node.value))

        elif isinstance(node, ast.Name):
            return TagConditionFactory.HAS(Tag(node.id))

        else:
            raise ValueError(f"Unsupported operator in condition: {ast.dump(node)}")