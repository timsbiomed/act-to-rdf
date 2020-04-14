from typing import Dict

from rdflib import Namespace, URIRef, OWL, SKOS

from act2rdf.accessinfo import NamespaceInfo, AccessInfo, ServiceType

# The namespaces table supplies the official namespaces for the various resources.  These namespaces form the URI
# of the entity and may or may not resolve.  When in doubt, we refer the 'system' identifier in the FHIR specification

namespaces = {
    'ACT': Namespace('https://ncatswiki.dbmi.pitt.edu/acts/ACT/'),
    'CPT4': Namespace('http://www.ama-assn.org/go/cpt#'),
    'HCPCS': Namespace('http://purl.bioontology.org/ontology/HCPCS/'),
    'ICD10CM': Namespace('http://hl7.org/fhir/sid/icd-10-cm#'),
    'ICD10PCS': Namespace('http://purl.bioontology.org/ontology/ICD10PCS/'),
    'ICD9CM': Namespace('http://purl.bioontology.org/ontology/ICD9CM/'),
    'RXNORM': Namespace('http://www.nlm.nih.gov/research/umls/rxnorm/'),
    'NDC': Namespace('https://identifiers.org/ndc:'),
    'NUI': Namespace('http://example.org/NUI/'),
    'ICD9PROC': Namespace('http://example.org/ICD9PROC/'),
    'LOINC': Namespace('http://purl.bioontology.org/ontology/LNC/'),
    'OWL': OWL,
    'SKOS': SKOS,
    'iso-11179': Namespace("http://www.iso.org/11179/")
}
UNKNOWN = Namespace('http://UNKNOWN.NS/')


def code_to_uri(code: str) -> URIRef:
    ns, ln = code.split(':', 1)
    return namespaces.get(ns, UNKNOWN)[ln]

# namespaces: Dict[str, NamespaceInfo] = {
#     'ACT': NamespaceInfo('act', 'https://ncatswiki.dbmi.pitt.edu/acts/ACT/'),
#     'CPT4': NamespaceInfo('cpt4', 'http://www.ama-assn.org/go/cpt#'),
#     'HCPCS': NamespaceInfo('hcpcs', 'http://purl.bioontology.org/ontology/HCPCS/'),
#     'ICD10CM': NamespaceInfo('icd10cm', 'http://purl.bioontology.org/ontology/ICD10CM/'),
#     'ICD10PCS': NamespaceInfo('icd10pcs', 'http://purl.bioontology.org/ontology/ICD10PCS/'),
#     'ICD9CM': NamespaceInfo('icd9cm', 'http://purl.bioontology.org/ontology/ICD9CM/'),
#     'RXNORM': NamespaceInfo('rxnorm', 'http://www.nlm.nih.gov/research/umls/rxnorm/'),
#     'NDC': NamespaceInfo('ndc', 'https://identifiers.org/ndc:'),
#     'NUI': NamespaceInfo('nui', 'http://example.org/NUI/'),
#     'ICD9PROC': NamespaceInfo('icd9p', 'http://example.org/ICD9PROC/'),
#     'LOINC': NamespaceInfo('loinc', 'http://purl.bioontology.org/ontology/LNC/'),
#     'OWL': NamespaceInfo('owl', 'http://www.w3.org/2002/07/owl#'),
#     'SNOMED': NamespaceInfo('sct', 'http://snomed.info/id/')
# }
#
# namespaces['LOINC'].urls.add([AccessInfo(ServiceType.FHIR, 'https://fhir.loinc.org/CodeSystem/$lookup?system=http://loinc.org&code={cid}')])
#
# namespaces['SNOMED'].urls.add([AccessInfo(ServiceType.CUSTOM, 'http://snomed.info/id/{cid}'),
#                                AccessInfo(ServiceType.BIOPORTAL, 'http://purl.bioontology.org/ontology/SNOMEDCT/{cid}'),
#                                AccessInfo(ServiceType.BIOPORTAL_REST, 'https://data.bioontology.org/ontologies/SNOMEDCT/classes/http%3A%2F%2Fpurl.bioontology.org%2Fontology%2FSNOMEDCT%2F{cid}?apikey={bioportalapikey}')])