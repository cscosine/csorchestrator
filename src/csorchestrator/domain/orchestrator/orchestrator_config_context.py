from dataclasses import dataclass, field
from typing import TypeVar


class OrchestratorConfigBaseCapability:
    pass


OrchestratorConfigBaseCapabilityT = TypeVar("OrchestratorConfigBaseCapabilityT", bound=OrchestratorConfigBaseCapability)


@dataclass
class OrchestratorConfigContext:
    # add capcability and use them to register downloaded bundles and manifests with a unique id,
    # - avoid double downloads
    # - error on double but different e.g. same provider with different versions

    _capabilities: dict[type, OrchestratorConfigBaseCapability] = field(
        default_factory=dict,
        kw_only=True,
    )

    def add_capability(
        self,
        capability: OrchestratorConfigBaseCapability,
        key: type[OrchestratorConfigBaseCapability],  # use key = type(capability) to register as exact type,
        # but if need generic, use a specific subclass of OrchestratorConfigBaseCapability
    ) -> "OrchestratorConfigContext":
        self._capabilities[key] = capability
        return self

    def get_capability(self, t: type[OrchestratorConfigBaseCapabilityT]) -> OrchestratorConfigBaseCapabilityT | None:
        capability = self._capabilities.get(t)
        return capability if isinstance(capability, t) else None

    def remove_capability(
        self,
        key: type[OrchestratorConfigBaseCapabilityT],
    ) -> "OrchestratorConfigContext":
        self._capabilities.pop(key, None)  # no exception if not exists
        return self
