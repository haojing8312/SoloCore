from typing import List, Union, TypeVar, Generic, Iterator, Optional, Tuple, overload
from .models import WordClip, Word, Line, Segment, Document

E = TypeVar('E', bound=Union[WordClip, Word, Line, Segment])

class ElementContainer(Generic[E]):
    def __init__(self, parent: Union[WordClip, Word, Line, Segment, Document]):
        self._elements: List[E] = []
        self._parent = parent

    def set_all(self, elements: List[E]):
        self._elements = elements
        for element in self._elements:
            element._parent = self._parent

    def extend(self, elements: List[E]):
        self._elements.extend(elements)
        for element in elements:
            element._parent = self._parent

    def add(self, element: E, index: Optional[int] = None):
        if index is None:
            index = len(self._elements)
        self._elements.insert(index, element)
        element._parent = self._parent

    def get_all(self) -> Tuple[E, ...]:
        return tuple(self._elements)
    
    def remove(self, element: E):
        self._elements.remove(element)

    @overload
    def __getitem__(self, index: int) -> E: ...
    @overload
    def __getitem__(self, index: slice) -> List[E]: ...
    def __getitem__(self, index: Union[int, slice]) -> Union[E, List[E]]:
        return self._elements[index]

    def __setitem__(self, index: int, value: E):
        self._elements[index] = value
        value.parent = self._parent

    def __iter__(self) -> Iterator[E]:
        return iter(self._elements)
    
    def __len__(self) -> int:
        return len(self._elements)
