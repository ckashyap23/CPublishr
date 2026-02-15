from abc import ABC, abstractmethod

from src.services.orchestration.contracts import NodeExecutionContext, NodeExecutionResult


class OrchestrationNode(ABC):
    name: str

    @abstractmethod
    def run(self, context: NodeExecutionContext) -> NodeExecutionResult:
        raise NotImplementedError
