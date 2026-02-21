from typing import Optional
import logging

import requests


logger = logging.getLogger("pharma_pivot.normalizer")


class RxNormNormalizer:
    BASE_URL = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
    APPROX_URL = "https://rxnav.nlm.nih.gov/REST/approximateTerm.json"

    def resolve_rxcui(self, generic_name: str) -> Optional[str]:
        name = generic_name.strip()
        if not name:
            return None

        try:
            response = requests.get(self.BASE_URL, params={"name": name}, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            logger.warning("RxNorm direct lookup failed for '%s': %s", name, exc)
            payload = {}

        id_group = payload.get("idGroup", {})
        concepts = id_group.get("rxnormId") or []
        if concepts:
            rxcui = str(concepts[0])
            logger.info("Resolved RXCUI via direct lookup '%s' -> %s", name, rxcui)
            return rxcui

        try:
            response = requests.get(self.APPROX_URL, params={"term": name, "maxEntries": 1}, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            logger.warning("RxNorm approximate lookup failed for '%s': %s", name, exc)
            return None

        candidate = (payload.get("approximateGroup", {}).get("candidate") or [{}])[0]
        rxcui = candidate.get("rxcui")
        if rxcui:
            logger.info("Resolved RXCUI via approximate lookup '%s' -> %s", name, rxcui)
            return str(rxcui)

        logger.warning("No RXCUI found for '%s'", name)
        return None
