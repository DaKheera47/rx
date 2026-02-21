from typing import Optional

import requests


class RxNormNormalizer:
    BASE_URL = "https://rxnav.nlm.nih.gov/REST/rxcui.json"

    def resolve_rxcui(self, generic_name: str) -> Optional[str]:
        name = generic_name.strip()
        if not name:
            return None

        try:
            response = requests.get(self.BASE_URL, params={"name": name}, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException:
            return None

        id_group = payload.get("idGroup", {})
        concepts = id_group.get("rxnormId") or []
        if not concepts:
            return None
        return str(concepts[0])
