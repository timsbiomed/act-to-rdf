from rdflib import Graph

g = Graph()
g.load('output.ttl', format="turtle")
g.serialize('output.json', format="json-ld")