# act2rdf 

Converting ACT ontologies to RDF

ACT Ontologies are downloaded from [the ACT Network](https://ncatswiki.dbmi.pitt.edu/acts). 

Versions

* [Version 2.0.1](https://ncatswiki.dbmi.pitt.edu/acts/wiki/ACT%20Ontology%20Version%202.0.1#no1)
* Version 1.7

## Conversion: 

The conversion is based on the following ontology files: 

* ACT_CPT_PX_2018AA.zip
* ACT_HCPCS_PX_2018AA.zip
* ACT_ICD10CM_DX_2018AA.zip
* ACT_ICD10PCS_PX_2018AA.zip
* ACT_ICD9CM_DX_2018AA.zip
* ACT_ICD9CM_PX_2018AA.zip
* ACT_LOINC_LAB_2018AA.zip
* ACT_MED_ALPHA_V2_121318.dsv
* ACT_MED_ALPHA_V2_121318.zip
* ACT_MED_VA_V2_092818.zip

In each file, the columns mapped to the triples

C_FULLNAME: the hierarchy is mapped to skos:broader
C_BASECODE: skos:exactMatch. Prefix:code is used to map to URIs. 
C_NAME: skos:prefLabel

Run act2rdf.py to convert the ACT ontologies to RDF (Turtle).

'''
pipenv run python act2rdf.act2rdf
''' 


