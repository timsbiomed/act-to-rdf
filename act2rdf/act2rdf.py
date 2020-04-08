from csv import DictReader
from io import TextIOWrapper
import sys
from rdflib import Namespace, Graph, Literal, RDF, OWL
from rdflib.namespace import SKOS, DCTERMS
import itertools
import os
from zipfile import ZipFile

namespaces = {
    'ACT': Namespace('http://example.org/ACT/'),
    'CPT4': Namespace('http://purl.bioontology.org/ontology/CPT/'),
    'HCPCS': Namespace('http://purl.bioontology.org/ontology/HCPCS/'),
    'ICD10CM': Namespace('http://purl.bioontology.org/ontology/ICD10CM/'),
    'ICD10PCS': Namespace('http://purl.bioontology.org/ontology/ICD10PCS/'),
    'ICD9CM': Namespace('http://purl.bioontology.org/ontology/ICD9CM/'),
    'RXNORM': Namespace('http://purl.bioontology.org/ontology/RXNORM/'),
    'NDC': Namespace('https://identifiers.org/ndc:'),
    'NUI': Namespace('http://example.org/NUI/'),
    'ICD9PROC': Namespace('http://example.org/ICD9PROC/'),
    'LOINC': Namespace('http://purl.bioontology.org/ontology/LNC/')
}

def pairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def read_rdf(reader: DictReader, g: Graph):
    """
    Read ACT ontology from reader and convert to triples to store in a graph
    :type g: rdflib.Graph
    :type reader: csv.DictReader
    :param reader: csv.DictReader
    :param g: rdflib.Graph
    :return: A Graph
    """
    ACT = namespaces['ACT']
    g.bind('SKOS', SKOS)
    g.add((ACT.ACT, RDF.type, SKOS.ConceptScheme))
    g.add((ACT.ACT, DCTERMS.title, Literal("ACT Ontology")))
    g.add((ACT.ACT, OWL.versionInfo, Literal('2.0.1')))
    for row in reader:
        nodes = [n for n in row['C_FULLNAME'].split('\\') if n]
        for n1, n2 in pairwise(nodes):
            g.add((ACT[n2], SKOS.broader, ACT[n1]))
        g.add((ACT[nodes[-1]], RDF.type, SKOS.Concept))
        if row['C_BASECODE'].strip():
            if ':' in row['C_BASECODE']:
                tokens = row['C_BASECODE'].split(':')
                if len(tokens) == 2:
                    if tokens[0] in namespaces:
                        g.add((ACT[nodes[-1]], SKOS.exactMatch, namespaces[tokens[0]][tokens[1].replace(' ', '_')]))
                    else:
                        print('[NS NOT FOUND] ' + str(row))
                else:
                    print('[NO NS] ' + str(row))
        g.add((ACT[nodes[-1]], SKOS.prefLabel, Literal(row['C_NAME'])))
    return g


if __name__ == '__main__':
    print(os.getcwd())
    # process all files in the data directory
    g = Graph()
    for file in os.scandir('data'):
        if not file.name.endswith('.zip') or file.name.startswith('ACT_CONCEPT_'):
            continue
        full_path = os.path.join('data', file.name)
        zf = ZipFile(full_path)
        files = zf.infolist()
        print(files)
        with ZipFile(full_path) as zf:
            with zf.open(files[0]) as infile:
                reader = DictReader(TextIOWrapper(infile, 'utf-8'), delimiter='|')
                g = read_rdf(reader, g)
    g.serialize('act-ontology.ttl', format='ttl')