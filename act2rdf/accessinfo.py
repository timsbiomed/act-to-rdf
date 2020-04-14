from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, List, Union

import union as union
from rdflib import Namespace


class ServiceType(Enum):
    FHIR = auto()           # FHIR terminology server
    CTS2 = auto()           # CTS2 terminology server
    BIOPORTAL = auto()      # BioPortal terminology server
    BIOPORTAL_REST = auto() # BioPortal REST server
    CUSTOM = auto()         # Custom terminology server

@dataclass
class AccessInfo:
    servicetype: ServiceType
    url_template: str
    accept_header: Optional[List[str]] = None
    credentials_required: bool = False


@dataclass
class NamespaceInfo:
    namespace: str
    officialuri: Union[Namespace, str]
    urls: Optional[List[AccessInfo]] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.officialuri, Namespace):
            self.officialuri = NamespaceInfo(str(self.officialuri))
