"""
Evidence Registry Loader & Validator
====================================
Loads, validates, and queries the comprehensive evidence registry containing:
- Audited GitHub repositories (18 repositories)
- Cataloged technical projects (with classifications and verification states)
- Detailed CS50 assignment inventory
- Evidence-based service catalog with dynamic subservices and eligibility rules
"""

import json
import os
from typing import Any, Dict, List, Optional

_REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "registry",
    "evidence_registry.json"
)

_cached_registry: Optional[Dict[str, Any]] = None


def load_registry(force_reload: bool = False) -> Dict[str, Any]:
    """Loads and validates the registry JSON schema."""
    global _cached_registry
    if _cached_registry is not None and not force_reload:
        return _cached_registry

    if not os.path.exists(_REGISTRY_PATH):
        raise FileNotFoundError(f"Required evidence registry not found at: {_REGISTRY_PATH}")

    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Basic schema integrity assertions
    required_keys = ["repositories", "projects", "cs50_assignments", "services"]
    for k in required_keys:
        if k not in data or not isinstance(data[k], list):
            raise ValueError(f"Malformed registry: missing or invalid '{k}' key")

    _cached_registry = data
    return _cached_registry


def get_all_repositories() -> List[Dict[str, Any]]:
    return load_registry().get("repositories", [])


def get_all_projects(classification: Optional[str] = None, only_public: bool = True) -> List[Dict[str, Any]]:
    projects = load_registry().get("projects", [])
    result = []
    for p in projects:
        if only_public and p.get("visibility") != "public":
            continue
        if classification and p.get("portfolio_classification") != classification:
            continue
        result.append(p)
    return result


def get_project_by_id(project_id: str) -> Optional[Dict[str, Any]]:
    projects = load_registry().get("projects", [])
    for p in projects:
        if p.get("id") == project_id or p.get("slug") == project_id:
            return p
    return None


def get_cs50_assignments() -> List[Dict[str, Any]]:
    return load_registry().get("cs50_assignments", [])


def get_service_catalog(only_eligible: bool = True) -> List[Dict[str, Any]]:
    services = load_registry().get("services", [])
    if not only_eligible:
        return services
    
    eligible_services = []
    for s in services:
        if s.get("eligible", False):
            # Filter subservices to only eligible ones
            s_copy = dict(s)
            s_copy["subservices"] = [sub for sub in s.get("subservices", []) if sub.get("eligible", False)]
            eligible_services.append(s_copy)
    return eligible_services


def get_service_by_id(service_id: str) -> Optional[Dict[str, Any]]:
    services = load_registry().get("services", [])
    for s in services:
        if s.get("id") == service_id:
            return s
    return None


def validate_service_selection(service_id: str, subservice_id: Optional[str]) -> tuple[bool, str]:
    """
    Deterministically validates service eligibility and ensures the subservice belongs
    to the parent service and is active.
    """
    if not service_id:
        return False, "Please select a service."

    service = get_service_by_id(service_id)
    if not service:
        return False, f"Selected service '{service_id}' does not exist."

    if not service.get("eligible", False):
        return False, f"Service '{service.get('title')}' is currently not eligible for commission."

    if subservice_id:
        valid_sub = None
        for sub in service.get("subservices", []):
            if sub.get("id") == subservice_id:
                valid_sub = sub
                break
        if not valid_sub:
            return False, f"Subservice '{subservice_id}' is not part of '{service.get('title')}'."
        if not valid_sub.get("eligible", False):
            return False, f"Subservice '{valid_sub.get('title')}' is not currently active."

    return True, ""
