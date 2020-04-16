import re

# Valid code pattern by namespace
from typing import Dict

DEBUG = False

code_re: Dict[str, re.Pattern] = {'CPT4': re.compile(r'[0-9]+$'),
                                  'HCPCS': re.compile(r'[A-Z0-9]+$'),
                                  'ICD10CM': re.compile(r'[A-Z][0-9][0-9](\.[0-9]+)?$'),
                                  'ICD10PCS': re.compile(r'[A-Z0-9]+$'),
                                  'ICD9CM': re.compile(r'[A-Z][0-9][0-9][0-9]?(\.[0-9]+)?$'),
                                  'ICD9PROC': re.compile(r'[0-9][0-9](\.[0-9]+)?$'),
                                  'LOINC': re.compile(r'(LP)?[0-9]+-[0-9]$'),
                                  'NDC': re.compile(r'[0-9]{11}$'),
                                  'RXNORM': re.compile(r'[0-9]+$')}


def is_valid_code(code: str) -> bool:
    if ':' in code:
        ns, name = code.split(':', 1)
        if ns in code_re:
            if DEBUG and not code_re[ns].match(name):
                print(f"Code is not valid: {code}")
            return bool(code_re[ns].match(name))
        else:
            print(f"Unrecognized namespace: {ns} in {code}")
            return False
    else:
        print(f"Invalid code: {code}")
        return False