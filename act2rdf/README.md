# Mapping between generic ACT Ontology and RDF SKOS
The ACT ontology represents a hierarchically organized collection of "pick lists".  In the context of `idb2`, the 
ACT ontology performs two functions:
1) It allows the user to select sets of one or more concept codes by navigating the "Ontology" panel in the i2b2 web client.
2) It generates queries that select entries in the i2b2 `Observation Fact` table that select rows having a `concept_cd`
that matches a concept selected in the pick list.

This project separates the first function from the second, rendering the ACT concept code pick lists as a hierarchical
RDF structure based on SKOS.  As we are representing the *user view* (what a webclient user sees), we assign a separate
SKOS `ConceptScheme` to each base node which corresponds to each `table_access` entry:

| ConceptScheme URI | rdfs:label | skos:prefLabel | skos:description | 
| ---- | ---- | ---- | --- |
| act:A20098492 | ACT_DX_ICD10_2018 | ACT Diagnoses ICD-10-CM  | ACT Diagnoses ICD-10 |
| act:A28298479 | ACT_LAB_LOINC_2018 | ACT Laboratory Tests (Provisional) | ACT Lab LOINC (Full list) |

The pick-list "scaffolding" which forms the hierarchical structure mirrors the hierarchy of the corresponding ontology
table.  Each "Draggable" scaffolding element can be resolved to a "value set" -- a set of non-ACT concept codes (e.g. ICD9, CPT,
 LOINC, etc).
 
## SKOS Representation of ACT nodes
Act nodes are identified by curies of the form "act:{act concept id}" (e.g. act:20098491).

### Metadata tables
| column |  RDF representation | example | note |
| --- | --- | --- | --- |
| c_hlevel | (none) | | This represents the relative hierarchy of a node.  When converting from SKOS to ACT Tables, this will represent the relative nesting. |
| c_fullname | act:{id} rdf:type skos:Concept ; skos:inScheme act:{root} . | \ACT\Procedures\ICD9\V2_2018AA\A18090800\A8352133\A15574666\A15574281\A15574670\ --> act:A15574670 | Note 1  |
| c_name | skos:prefLabel | act:A15574670 skos:prefLabel "17.1 Laparoscopic unilateral repair of inguinal hernia" . | |
| c_synonym_cd | (none) | | Not used in ACT use case.  Always 'N' |
| c_visualattributes |  |  | Non-draggable attributes ('Cx' and 'xI') do not have any skos:exactMatch entries |
| c_totalnum | (none) | | unused |
| c_basecode | skos:editorialNote | act:A15574670 skos:editorialNote "ICD9PROC:17.1" . | This is a hint, not actually definitional |
| c_metadataxml | (none) | | not currently implemented |
| c_facttablecolumn | (none) | |  |
| c_tablename | (none) | | MUST be "concept_dimension" or empty - we don't do non-concept queries at the moment |
| c_columnname | (none) | |  |
| c_columndatatype | (none) | | MUST be "T" or empty |
| c_operator | (none) | | MUST be 'LIKE' or empty |
| c_dimcode | (See: [Concept Dimension table](#Concept Dimension table)) | | |
| c_comment | (none) | | Ignored |
| c_tooltip | skos:scopeNote | act:A15574670 skos:scopeNote "Procedures ICD9\PROCEDURES\OTHER MISCELLANEOUS DIAGN\Other miscellaneous proce\Laparoscopic unilateral r\" | |

Note 1:  c_fullname is used to build the hierarchy.  The following SKOS entries are created:
1) The subject of all of the row assertions is `act:{id}` where *id* is the last entry in the path.
2) If the path *up to* the last entry in the path is the `table_access.c_fullname` that got us to this table then:
    ```
    act:{id} skos:inScheme act:{parent_id} .
    act:{parent_id} skos:hasTopConcept act:{id} .
    ```
3) Otherwise:
    ``` 
    act:{id} skos:broader {act:parent_id} .
    ```
### Concept Dimension table
For every `act{id}` recorded in the metadata table, *if* the first character in `c_visualattributes` is one of 'F', 'L', 'M' (draggable) and
the second character is 'A', execute the following query:
    ```sql
    select {c_facttablecolumn} from {c_tablename} where {c.columnname} {c_operator} {c_dimcode};
    ``` 
note that the operator/c_dimcode is a different format for 'LIKE' vs '=', quotes are added in 'T' data types only and '%' is
added onto the end with 'LIKE' and a non 'M' visual attribute.

For every entry, e, in the result of this select, add the following:
    ```
    act:{id} rdf:type skos:Collection ;
    act:{id} skos:member {e} .
    ```
Note: We may want to consider mapping the namespace of `{e}` to lower case.

## URI assignment
Discuss the `schemes` table

## Issues
### Fabricated codes
Currently there is no way to distinguish official concept codes from groupers.  As an example, there is no way to 
differentiate the following:

| ACT Code | "ICD-10" code | Visual Attributes |
| --- | --- | --- |
| A20098492  | ICD10CM:ICD10CM Diagnosis | FA |
| A18905737 | ICD10CM:A00-B99 | FA |
| A17798915 | ICD10CM:A17 | FA |
| A17798917 | ICD10CM:A17.8 | FA |
| A17798919 | ICD10CM:A17.81 | LA |

The first two entries above clearly are *not* valid ICD-10 codes, and the final entry (A17.81) clearly is.  The remaining
two entries, (A17 and A17.8) can be coded in certain situations and not others.  This has not become an issue in i2b2
nodes because (theoretically), no one will use the first two codes.  At worst it will only result in slightly inefficient
queries.

For value set definition purposes, however, we DO need to distinguish these elements.  In the short term, we are just
going to add a code predicate that tests the code to determine what does and does not belong.