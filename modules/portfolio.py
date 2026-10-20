"""
Portfolio Service Layer
=======================
Handles business logic for the developer portfolio, project showcase,
service catalog, and inquiry dispatch. Integrates directly with modules.sql_helper_dictionary.
"""

from typing import Any, Dict, List, Optional, Tuple
import modules.sql_helper_dictionary as sql_h
import modules.evidence_registry as reg


def get_portfolio_overview() -> Dict[str, Any]:
    """Returns overview statistics and featured projects for the landing page."""
    all_projects = reg.get_all_projects(only_public=True)
    featured = [p for p in all_projects if p.get("featured", False)]
    if not featured:
        featured = all_projects[:4]

    eligible_services = reg.get_service_catalog(only_eligible=True)
    cs50_count = len(reg.get_cs50_assignments())
    repos_count = len(reg.get_all_repositories())

    return {
        "featured_projects": featured,
        "eligible_services": eligible_services,
        "stats": {
            "total_repositories": repos_count,
            "total_projects": len(all_projects),
            "cs50_assignments": cs50_count,
            "primary_pillars": len(eligible_services)
        }
    }


def list_projects(classification: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns projects optionally filtered by classification."""
    return reg.get_all_projects(classification=classification, only_public=True)


def get_project_detail(project_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a project by id/slug."""
    return reg.get_project_by_id(project_id)


def list_services() -> List[Dict[str, Any]]:
    """Returns all publicly eligible services with active subservices."""
    return reg.get_service_catalog(only_eligible=True)


def list_cs50_assignments() -> List[Dict[str, Any]]:
    """Returns detailed CS50 assignment inventory."""
    return reg.get_cs50_assignments()


def submit_service_inquiry(
    name: str,
    email: str,
    service_id: str,
    subservice_id: Optional[str],
    project_id: Optional[str],
    channel: str,
    message: str
) -> Tuple[bool, str]:
    """
    Validates input server-side, validates service eligibility,
    and reliably persists the inquiry to databases/main.db.
    """
    name = (name or "").strip()
    email = (email or "").strip()
    message = (message or "").strip()
    service_id = (service_id or "").strip()
    subservice_id = (subservice_id or "").strip() or None
    project_id = (project_id or "").strip() or None
    channel = (channel or "web_form").strip()

    if not name or len(name) < 2:
        return False, "Please provide your name (at least 2 characters)."
    if not email or "@" not in email or "." not in email:
        return False, "Please provide a valid email address."
    if not message or len(message) < 10:
        return False, "Please provide a message or project brief (at least 10 characters)."

    # Validate service eligibility
    is_valid_service, err = reg.validate_service_selection(service_id, subservice_id)
    if not is_valid_service:
        return False, err

    # Validate optional project reference if provided
    if project_id:
        proj = reg.get_project_by_id(project_id)
        if not proj:
            return False, f"Referenced project '{project_id}' was not found in catalog."

    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO service_inquiries (name, email, service_id, subservice_id, project_id, channel, message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, email, service_id, subservice_id, project_id, channel, message))
            conn.commit()
        return True, "Your inquiry has been successfully submitted! I will review your requirements and respond shortly."
    except Exception as e:
        print(f"Error persisting service inquiry: {e}")
        return False, "A database error occurred while saving your inquiry. Please try again later."


def list_inquiries_for_admin() -> List[Dict[str, Any]]:
    """Retrieves all inquiries for administrative review."""
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM service_inquiries ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error fetching inquiries: {e}")
        return []


def update_inquiry_status(inquiry_id: int, new_status: str) -> Tuple[bool, str]:
    """Updates the administrative review status of an inquiry."""
    allowed = ["new", "reviewed", "contacted", "archived"]
    if new_status not in allowed:
        return False, f"Invalid status: {new_status}"
    try:
        with sql_h.get_db("main.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE service_inquiries SET status = ? WHERE id = ?
            """, (new_status, inquiry_id))
            conn.commit()
        return True, "Status updated."
    except Exception as e:
        return False, str(e)
