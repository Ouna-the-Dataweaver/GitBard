from abc import ABC, abstractmethod
from ..base import Pipeline


class Command(ABC):
    """Base class for all commands"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Command name (e.g., 'oc_review')"""
        pass

    @property
    @abstractmethod
    def trigger_pattern(self) -> str:
        """Pattern to detect command in webhook (e.g., '/oc_review')"""
        pass

    @abstractmethod
    def get_pipeline(self) -> Pipeline:
        """Return the pipeline for this command"""
        pass
