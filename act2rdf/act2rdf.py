import csv
import sys
from rdflib import Namespace, Graph, Literal, RDF, OWL
from rdflib.namespace import SKOS, DCTERMS
import itertools
import os

act = Namespace('http://example.org/act/')
cpt4 = Namespace('http://example.org/cpt4/')


def pairwise(iterable):
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)


def act2rdf(file: str):
    g = Graph()
    g.bind('SKOS', SKOS)
    g.add((act.ACT, RDF.type, SKOS.ConceptScheme))
    g.add((act.ACT, DCTERMS.title, Literal("ACT Ontology")))
    g.add((act.ACT, OWL.versionInfo, Literal('2.0.1')))
    with open(file, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='|', )
        for row in reader:
            nodes = [n for n in row['CONCEPT_PATH'].split('\\') if n]
            for n1, n2 in pairwise(nodes):
                g.add((act[n2], SKOS.broader, act[n1]))
            code = row['CONCEPT_CD'].split(':')[1]
            g.add((act[nodes[-1]], RDF.type, SKOS.Concept))
            g.add((act[nodes[-1]], SKOS.exactMatch, cpt4[code.replace(' ', '_')]))
            g.add((act[nodes[-1]], SKOS.prefLabel, Literal(row['NAME_CHAR'])))
    return g


if __name__ == '__main__':
    g = act2rdf(sys.argv[1])
    g.serialize('output.ttl', format='ttl')