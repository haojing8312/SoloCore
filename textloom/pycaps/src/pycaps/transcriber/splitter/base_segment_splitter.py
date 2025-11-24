from abc import ABC, abstractmethod
from pycaps.common import Document

class BaseSegmentSplitter(ABC):

    @abstractmethod
    def split(self, document: Document) -> None:
        '''
        Splits the segments of a document, modifying the amount of words per segment.
        It assumes that the segments have not been splitted into lines yet.
        '''
        pass
