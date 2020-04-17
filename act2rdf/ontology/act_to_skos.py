import argparse
import logging
import os
import sys
from typing import List, Tuple, Optional, Dict

from i2b2model.metadata.i2b2ontology import OntologyEntry
from i2b2model.metadata.i2b2ontologyvisualattributes import VisualAttributes
from i2b2model.metadata.i2b2tableaccess import TableAccess
from i2b2model.sqlsupport.dbconnection import process_parsed_args, add_connection_args
from i2b2model.sqlsupport.file_aware_parser import FileAwareParser
from i2b2model.sqlsupport.i2b2tables import I2B2Tables
from rdflib import Dataset, RDF, OWL, URIRef, Literal
from rdflib.namespace import SKOS
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import sessionmaker, Session

from act2rdf import DATA_DIR
from namespaces_and_uris import code_to_uri, namespaces
from ontology.codesystem_membership import is_valid_code

ACT = namespaces['ACT']
ISO = namespaces['iso-11179']

# Parameters -- these should really be put on the command line
EXPLICIT_MEMBERS = True         # True means compute value set members.  False means leave implicit
COMPUTE_MEMBERS = True          # True means compute closure in graph, false means use LIKE queries
TABLE_PREFIX = 'ACT_'           # Only process tables that start with this prefix
SKIP_TABLES = ['ACT_DEMO']
ONE_TABLE = False               # True means process first matching table, False means all matching tables
NUM_CODES = 0                   # Number of codes to process (debug). 0 means all
OUTPUT_DIR = DATA_DIR
DEBUG = False                   # Emit diagnostic statements


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

    def get_query(self, te: OntologyEntry, dim: str, oper: str) -> Tuple[Connection, text]:
        return self.tables[te.c_tablename.lower()], \
               self.query_tables.setdefault(QueryKey(te), self._gentext(te).format(dim=dim, oper=oper))

    def _gentext(self, te: OntologyEntry) -> str:
        table = self.tables[te.c_tablename.lower()]
        return f"SELECT {te.c_facttablecolumn}, {te.c_columnname} " \
               f"FROM {table} WHERE {te.c_columnname} {{oper}} {{dim}} ;"


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
        # Beware of the double escape requirement for percents
        upper_oper = te.c_operator.upper()
        if (not COMPUTE_MEMBERS or VisualAttributes(te.c_visualattributes).leaf) and upper_oper == 'LIKE' and VisualAttributes(te.c_visualattributes).approximate:
            print(f"Approximate leaf {te.c_fullname}")
            oper = te.c_operator
            dimcode = te.c_dimcode.replace('\\', '\\\\') + "%%"
        else:
            oper = '=' if upper_oper == 'LIKE' else te.c_operator
            dimcode = te.c_dimcode
        dimcode = f"'{dimcode}'"
    else:
        oper, dimcode = te.c_operator, te.c_dimcode
    table, querytext = queries.get_query(te, dimcode, oper)
    if DEBUG:
        print(querytext)
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
        if EXPLICIT_MEMBERS:
            g.add((cid, RDF.type, ISO.EnumeratedConceptualDomain))
        if not COMPUTE_MEMBERS and EXPLICIT_MEMBERS:
            for code in codes:
                if is_valid_code(code):
                    g.add((cid, ISO['enumeratedConceptualDomain.hasMember'], code_to_uri(code)))
        for exact in exacts:
            if is_valid_code(exact):
                g.add((cid, SKOS.exactMatch, code_to_uri(exact)))


def proc_ontology_table(queries: QueryTexts, table_name: str, concept_scheme: URIRef, basename: str, g: Dataset) -> int:
    """
    Process the entries in ontology table, table
    :param queries: QueryText instance
    :param table_name: table to process
    :param concept_scheme: Owning concept scheme
    :param basename: Root name of table -- used to strip the front part of the full name path
    :param g: Graph to record assertions
    :return: Number processed
    """
    te: OntologyEntry
    table = queries.tables[table_name.lower()]
    nentries = 0
    q = queries.ont_session.query(table) if not NUM_CODES else queries.ont_session.query(table).order_by(table.c.c_fullname)
    for te in q.all():
        parent, ccode = proc_fullname(basename, te.c_fullname)
        if ccode:
            cid = ACT[ccode]
            g.add((cid, RDF.type, SKOS.Concept))
            g.add((cid, SKOS.inScheme, concept_scheme))
            g.add((cid, SKOS.prefLabel, Literal(te.c_name)))
            if te.c_basecode:
                g.add((cid, SKOS.editorialNote, Literal(te.c_basecode)))
            if te.c_tooltip:
                tip = ', '.join([e for e in te.c_tooltip.split('\\') if e])
                g.add((cid, SKOS.scopeNote, Literal(tip)))
            if parent:
                g.add((cid, SKOS.broader, ACT[parent]))
            else:
                g.add((concept_scheme, SKOS.hasTopConcept, cid))
            # Some sort of PyCharm debbugger issue here...
            va = VisualAttributes(te.c_visualattributes)
            if va.draggable:
                evaluate_ontology_entry(queries, te, cid, g)
            nentries += 1
            if NUM_CODES and nentries >= NUM_CODES:
                break
    return nentries


def proc_table_access_row(queries: QueryTexts, ta: TableAccess, g: Dataset) -> int:
    """
    Process a table_access entry
    :param queries: query cache and tables access
    :param ta: table_access entry
    :param g: target Graph
    :return: URI of value set to be represented
    """
    name_parts = ta.c_fullname.split('\\')[2:-1]    # Skip leading and trailing slashes
    concept_scheme = ACT['/'.join(name_parts[:2])]
    concept_scheme_version = ACT['/'.join(name_parts[:3])]
    g.add((concept_scheme, RDF.type, SKOS.ConceptScheme))
    g.add((concept_scheme, RDF.type, OWL.Ontology))
    g.add((concept_scheme, OWL.versionIRI, concept_scheme_version))
    return proc_ontology_table(queries, ta.c_table_name, concept_scheme, ta.c_fullname, g)


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


def dump_as_rdf(g: Dataset, table_name: str) -> bool:
    """
    Dump the contents of Graph g in RDF turtle
    :param g: Dataset to dump
    :param table_name: name of the base table
    :return: success indicator
    """
    # Propagate the mapped concepts up the tree
    def add_to_ancestors(s: URIRef, vm: URIRef):
        g.add((s, ISO['enumeratedConceptualDomain.hasMember'], vm))
        for parent in g.objects(s, SKOS.broader):
            add_to_ancestors(parent, vm)

    if COMPUTE_MEMBERS and EXPLICIT_MEMBERS:
        for subj, obj in g.subject_objects(SKOS.exactMatch):
            add_to_ancestors(subj, obj)
        # TODO: this gives us a list of all concepts in the scheme... useful?
        for scheme, tc in g.subject_objects(SKOS.hasTopConcept):
            for member in g.objects(tc, ISO['enumeratedConceptualDomain.hasMember']):
                g.add((scheme, ISO['enumeratedConceptualDomain.hasMember'], member))

    for name, ns in namespaces.items():
        g.bind(name.lower(), ns)
    outfile = os.path.join(DATA_DIR, table_name + '.ttl')
    print(f"Saving output to {outfile}")
    g.serialize(outfile, format='turtle')
    print(f"{len(g)} triples written")
    return True


def proc_table_access_table(opts: argparse.Namespace) -> int:
    """
    Iterate over the table_access table emitting its entries
    :param opts: function arguments
    :return: Graph
    """
    logging.info("Iterating over table_access table")
    process_parsed_args(opts, FileAwareParser.error)
    queries = QueryTexts(I2B2Tables(opts))
    q = queries.ont_session.query(queries.tables.table_access)
    e: TableAccess
    for e in q.all():
        print(f"{e.c_table_cd}", end='')
        if not e.c_table_cd.startswith(TABLE_PREFIX) or e.c_table_cd in SKIP_TABLES:
            print(" skipped")
            continue
        g = Dataset()
        nelements = proc_table_access_row(queries, e, g)
        if nelements:
            print(f" {nelements} elements processed")
            dump_as_rdf(g, e.c_table_cd)
            if ONE_TABLE:
                break
    else:
        nelements = 0
    return nelements


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
    proc_table_access_table(opts)


if __name__ == "__main__":
    list_table_access(sys.argv[1:])
