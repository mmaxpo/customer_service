from __future__ import annotations

from abc import ABC, abstractmethod

from .base import ResolutionContext


class ResolverPolicy(ABC):

    @abstractmethod
    def apply(
        self,
        ctx: ResolutionContext,
    ) -> None:
        ...
