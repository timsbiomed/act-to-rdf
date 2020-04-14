import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

from i2b2model.metadata.i2b2ontology import OntologyEntry
from i2b2model.metadata.i2b2ontologyvisualattributes import VisualAttributes
from i2b2model.metadata.i2b2tableaccess import TableAccess
from i2b2model.sqlsupport.dbconnection import process_parsed_args, add_connection_args
from i2b2model.sqlsupport.file_aware_parser import FileAwareParser
from i2b2model.sqlsupport.i2b2tables import I2B2Tables
from rdflib import Dataset, SKOS, RDF, Namespace, OWL, URIRef, Literal
from sqlalchemy import text, bindparam
from sqlalchemy.engine import Connection
from sqlalchemy.orm import sessionmaker, Session

from namespaces_and_uris import code_to_uri, namespaces

ACT = namespaces['ACT']
ISO = namespaces['iso-11179']

# Unique key to pre-built query
class QueryKey:
    facttablecolumn: str
    tablename: str
    columnname: str
    operator: str
    datatype: str

    def __init__(self, te: OntologyEntry) -> None:
        self.facttablecolumn = te.c_facttablecolumn
        self.tablename = te.c_tablename.lower()
        self.columnname = te.c_facttablecolumn
        self.operator = te.c_operator


class QueryTexts:
    tables: I2B2Tables
    query_tables: Dict[QueryKey, text] = dict()
    ont_session: Session = None
    crc_session: Session = None

    def __init__(self, tables: I2B2Tables) -> None:
        self.tables = tables
        self.ont_session = sessionmaker(bind=tables.ont_engine)()
        self.crc_session = sessionmaker(bind=tables.crc_engine)()

    def get_query(self, te: OntologyEntry, dim: str) -> Tuple[Connection, text]:
        return self.tables[te.c_tablename.lower()], self.query_tables.setdefault(QueryKey(te), self._gentext(te).format(dim=dim))

    def _gentext(self, te: OntologyEntry) -> str:
        table = self.tables[te.c_tablename.lower()]
        return f"SELECT {te.c_facttablecolumn}, {te.c_columnname} " \
               f"FROM {table} WHERE {te.c_columnname} {te.c_operator} {{dim}} ;"


def proc_fullname(base: str, fn: str) -> Tuple[str, ...]:
    """
    Return the parent code followed by the concept code
    :param base: root of fullname
    :param fn: fullname
    :return: parent code (if any) and concept code
    """
    return tuple(fn.replace(base, '\\\\').split('\\')[-3:-1])


def get_te_valueset(queries: QueryTexts, te: OntologyEntry) -> Tuple[str, List[str], List[str]]:
    """
    Return all members of the value set and the exact match
    :param queries:
    :param te:
    :return: column name, value set members, exact match
    """
    if te.c_columndatatype == 'T':
        # Beware of the double escape requirement
        approx = '%%' if VisualAttributes(te.c_visualattributes).approximate else ''
        dimcode = f"'{te.c_dimcode}{approx}'".replace('\\', '\\\\')
    else:
        dimcode = te.c_dimcode
    table, querytext = queries.get_query(te, dimcode)
    qr = list(queries.crc_session.execute(querytext))
    return te.c_columnname, [e[0] for e in qr], [e[0] for e in qr if e[1] == te.c_dimcode]


def evaluate_ontology_entry(queries: QueryTexts, te: OntologyEntry, cid: URIRef, g: Dataset) -> None:
    """
    Execute the OntologyEntry row in te and get the resulting set fact table keys
    :param queries: QueryTexts instance
    :param te: OntologyEntry instance to look up
    :param cid: parent concept identifier
    :param g: Graph to add entries to
    :return:
    """
    column_name, codes, exacts = get_te_valueset(queries, te)
    if codes:
        g.add((cid, RDF.type, ISO.EnumeratedConceptualDomain))
        for code in codes:
            g.add((cid, ISO['enumeratedConceptualDomain.hasMember'], code_to_uri(code)))
        for exact in exacts:
            g.add((cid, SKOS.exactMatch, code_to_uri(exact)))


def proc_ontology_table(queries: QueryTexts, table_name: str, concept_scheme: URIRef, basename: str, g: Dataset) -> None:
    """
    Process the entries in ontology table, table
    :param queries: QueryText instance
    :param table_name: table to process
    :param concept_scheme: Owning concept scheme
    :param basename: Root name of table -- used to strip the front part of the full name path
    :param g: Graph to record assertions
    """
    te: OntologyEntry = None        # For type hints
    table = queries.tables[table_name.lower()]
    nentries = 0
    for te in queries.ont_session.query(table).all():
        parent, ccode = proc_fullname(basename, te.c_fullname)
        cid = ACT[ccode]
        g.add((cid, RDF.type, SKOS.Concept))
        g.add((cid, SKOS.inScheme, concept_scheme))
        if parent:
            g.add((cid, SKOS.broader, ACT[parent]))
            g.add((cid, SKOS.prefLabel, Literal(te.c_name)))
            if te.c_basecode:
                g.add((cid, SKOS.editorialNote, Literal(te.c_basecode)))
            if te.c_tooltip:
                g.add((cid, SKOS.scopeNote, Literal(te.c_tooltip)))
        else:
            g.add((concept_scheme, SKOS.hasTopConcept, cid))
        # Some sort of PyCharm debbugger issue here...
        va = VisualAttributes(te.c_visualattributes)
        if va.draggable:
            evaluate_ontology_entry(queries, te, cid, g)
        nentries += 1
        if nentries > 100:
            break


def proc_list_entry(queries: QueryTexts, ta: TableAccess, g: Dataset) -> Optional[URIRef]:
    """
    Process a table_access entry
    :param queries: query cache and tables access
    :param ta: table_access entry
    :param g: target Graph
    :return: URI of value set to be represented
    """
    if not ta.c_fullname.startswith('\\ACT\\'):
        print(f"Skipping {ta.c_table_name}")
    else:
        name_parts = ta.c_fullname.split('\\')[2:-1]    # Skip leading and trailing slashes
        concept_scheme = ACT['/'.join(name_parts[:2])]
        concept_scheme_version = ACT['/'.join(name_parts[:3])]
        g.add((concept_scheme, RDF.type, SKOS.ConceptScheme))
        g.add((concept_scheme, RDF.type, OWL.Ontology))
        g.add((concept_scheme, OWL.versionIRI, concept_scheme_version))
        proc_ontology_table(queries, ta.c_table_name, concept_scheme, ta.c_fullname, g)
        return concept_scheme


def parse_args(argv: List[str]) -> Optional[argparse.Namespace]:
    """
    Parse i2b2 connection arguments
    :param argv: Arguments
    :return: parsed arguments if success otherwise nothing
    """
    parser = FileAwareParser(description="Iterate over table_access table", prog="table_access")
    add_connection_args(parser)
    opts, _ = parser.parse_known_args(parser.decode_file_args(argv))
    return opts


def proc_table_access_table(opts: argparse.Namespace, g: Dataset) -> Dataset:
    """
    Iterate over the table_access table emitting its entries
    :param opts: function arguments
    :param g: graph to emit to
    :return: Graph
    """
    process_parsed_args(opts, FileAwareParser.error)
    queries = QueryTexts(I2B2Tables(opts))
    q = queries.ont_session.query(queries.tables.table_access)
    for e in q.all():
        print(e.c_table_name)
        if proc_list_entry(queries, e, g):
            break
    return g


def dump_as_rdf(g: Dataset) -> bool:
    """
    Dump the contents of Graph g in RDF turtle
    :param g: Dataset to dump
    :return: success indicator
    """
    for name, ns in namespaces.items():
        g.bind(name.lower(), ns)
    g.serialize('output.ttl', format='turtle')
    return True


def list_table_access(argv: List[str]) -> bool:
    """
    Iterate over the i2b2 table_access table converting the ACT ontology to SKOS
    :param argv: i2b2 connection arguments
    :return: Success indicator
    """
    # Process the arguments and connect to the database
    opts = parse_args(argv)
    if opts is None:
        return False

    # Convert the tables to RDF
    g = Dataset()
    proc_table_access_table(opts, g)

    # Dump the results
    return dump_as_rdf(proc_table_access_table(opts, Dataset()))


if __name__ == "__main__":
    list_table_access(sys.argv[1:])
