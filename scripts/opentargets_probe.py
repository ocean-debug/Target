from __future__ import annotations

import argparse
import json

import requests


ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"
SEARCH_QUERY = """
query ResolveDisease($name: String!) {
  search(queryString: $name, entityNames: ["disease"], page: {index: 0, size: 5}) {
    hits { id name entity }
  }
}
"""
ASSOCIATION_QUERY = """
query DiseaseAssociations($diseaseId: String!) {
  disease(efoId: $diseaseId) {
    id
    name
    associatedTargets(page: {index: 0, size: 2}) {
      rows { score datatypeScores { id score } target { id approvedSymbol } }
    }
  }
}
"""


def post(query: str, variables: dict[str, str]) -> dict:
    response = requests.post(
        ENDPOINT,
        json={"query": query, "variables": variables},
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe dynamic Open Targets disease resolution.")
    parser.add_argument("--disease", required=True)
    args = parser.parse_args()

    search = post(SEARCH_QUERY, {"name": args.disease})
    hits = search.get("data", {}).get("search", {}).get("hits", [])
    print("SEARCH=" + json.dumps(hits, ensure_ascii=False))
    if not hits:
        raise SystemExit("No disease match")
    resolved_id = str(hits[0]["id"])
    result = post(ASSOCIATION_QUERY, {"diseaseId": resolved_id})
    print("ASSOCIATIONS=" + json.dumps(result, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()
