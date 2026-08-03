from __future__ import annotations

import json

import requests


ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"
QUERIES = {
    "tractability_type": 'query { __type(name: "Tractability") { fields { name type { kind name ofType { kind name } } } } }',
    "safety_liability_type": 'query { __type(name: "SafetyLiability") { fields { name type { kind name ofType { kind name } } } } }',
    "clinical_disease_list_item": 'query { __type(name: "ClinicalDiseaseListItem") { fields { name type { kind name ofType { kind name } } } } }',
    "clinical_disease_row": 'query { __type(name: "ClinicalIndicationFromDisease") { fields { name type { kind name ofType { kind name ofType { kind name } } } } } }',
    "clinical_target_row": 'query { __type(name: "ClinicalTargetFromTarget") { fields { name type { kind name ofType { kind name ofType { kind name } } } } } }',
    "clinical_disease_type": 'query { __type(name: "clinicalIndicationsFromDiseaseImp") { fields { name type { kind name ofType { kind name ofType { kind name ofType { kind name } } } } } } }',
    "clinical_target_type": 'query { __type(name: "clinicalTargets") { fields { name type { kind name ofType { kind name ofType { kind name ofType { kind name } } } } } } }',
    "associated_targets_type": 'query { __type(name: "AssociatedTargets") { fields { name type { kind name ofType { kind name } } } } }',
    "disease_field_signatures": 'query { __type(name: "Disease") { fields { name args { name type { kind name ofType { kind name } } } type { kind name ofType { kind name } } } } }',
    "target_field_signatures": 'query { __type(name: "Target") { fields { name args { name type { kind name ofType { kind name } } } type { kind name ofType { kind name } } } } }',
    "query_fields": 'query { __type(name: "Query") { fields { name } } }',
    "disease_fields": 'query { __type(name: "Disease") { fields { name } } }',
    "target_fields": 'query { __type(name: "Target") { fields { name } } }',
    "search_disease": 'query { search(queryString: "ulcerative colitis", entityNames: ["disease"], page: {index: 0, size: 5}) { hits { id name entity } } }',
    "search_target": 'query { search(queryString: "IL2", entityNames: ["target"], page: {index: 0, size: 5}) { hits { id name entity } } }',
    "disease": 'query { disease(efoId: "EFO_0000729") { id name } }',
    "associations": 'query { disease(efoId: "EFO_0000729") { associatedTargets(page: {index: 0, size: 2}) { rows { score target { id approvedSymbol } } } } }',
    "datatypes": 'query { disease(efoId: "EFO_0000729") { associatedTargets(page: {index: 0, size: 2}) { rows { score datatypeScores { id score } target { id approvedSymbol } } } } }',
    "mondo_associations": 'query { disease(efoId: "MONDO_0005101") { id name associatedTargets(page: {index: 0, size: 2}) { rows { score datatypeScores { id score } target { id approvedSymbol } } } } }',
    "drugs": 'query { disease(efoId: "EFO_0000729") { knownDrugs(size: 2) { rows { phase status drug { id name } target { id approvedSymbol } } } } }',
    "target_drugs": 'query { target(ensemblId: "ENSG00000109471") { id approvedSymbol knownDrugs(size: 2) { rows { phase status drug { id name } target { id approvedSymbol } } } } }',
    "target_clinical": 'query { target(ensemblId: "ENSG00000109471") { id approvedSymbol drugAndClinicalCandidates { count rows { id maxClinicalStage drug { id name } diseases { diseaseFromSource disease { id name } } } } } }',
}


def main() -> None:
    for name, query in QUERIES.items():
        response = requests.post(ENDPOINT, json={"query": query}, timeout=45)
        print(f"PROBE={name} HTTP={response.status_code}")
        try:
            payload = response.json()
            if name.endswith("field_signatures"):
                fields = payload.get("data", {}).get("__type", {}).get("fields", [])
                payload = {"fields": [field for field in fields if field["name"] in {
                    "associatedTargets", "drugAndClinicalCandidates", "associatedDiseases",
                    "safetyLiabilities", "tractability",
                }]}
            print(json.dumps(payload, ensure_ascii=False)[:2000])
        except ValueError:
            print(response.text[:1000])


if __name__ == "__main__":
    main()
