import re

icd10_re = re.compile(r'[A-Z][0-9][0-9](\.[0-9]+)?$')

def icd10cm_member(code: str) -> bool:
    """
    Determine whether code is a valid icd-cm code
    :param code:
    :return:
    """
    if ':' in code:
        ns, code = code.split(':', 1)
        return bool(ns == 'ICD10CM' and icd10_re.match(code))
    else:
        return icd10_re.match(code)

# print(icd10cm_member("ICD10CM:A10"))
# print(icd10cm_member("ICD10CM:A10.1"))
# print(icd10cm_member("ICD10CM:A10.113"))
# print(icd10cm_member("ICD10CM:A00-B99"))
# print(icd10cm_member("ICD10CM:Diagnosis Codes"))