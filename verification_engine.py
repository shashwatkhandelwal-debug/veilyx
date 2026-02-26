# Verification Engine - The brain of Veilyx
# This checks user attributes and decides if verification passes

from datetime import date

def check_age(date_of_birth_str, minimum_age=18):
    dob = date.fromisoformat(date_of_birth_str)
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age >= minimum_age

def check_name(name_from_digilocker, name_from_company):
    return name_from_digilocker.lower().strip() == name_from_company.lower().strip()

def check_document_valid(document_valid):
    return document_valid == True

def verify_user(user_data, requested_checks, company_provided_name=None):
    results = {}

    if "age_above_18" in requested_checks:
        results["age_above_18"] = check_age(user_data["date_of_birth"])

    if "name_match" in requested_checks and company_provided_name:
        results["name_match"] = check_name(user_data["name"], company_provided_name)

    if "document_valid" in requested_checks:
        results["document_valid"] = check_document_valid(user_data["document_valid"])

    return results