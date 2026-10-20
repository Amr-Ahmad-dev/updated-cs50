import pytest
from app import create_app, UserSession, Authority, AccountState
import modules.evidence_registry as reg
import modules.portfolio as port


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


# ==============================================================================
# 1. Registry & Audit Integrity Tests
# ==============================================================================

def test_registry_loads_successfully():
    data = reg.load_registry(force_reload=True)
    assert "repositories" in data
    assert "projects" in data
    assert "cs50_assignments" in data
    assert "services" in data
    assert len(data["repositories"]) == 18


def test_unique_repository_and_project_ids():
    repos = reg.get_all_repositories()
    repo_ids = [r["id"] for r in repos]
    assert len(repo_ids) == len(set(repo_ids)), "Duplicate repository IDs found!"

    projects = reg.get_all_projects(only_public=False)
    proj_ids = [p["id"] for p in projects]
    assert len(proj_ids) == len(set(proj_ids)), "Duplicate project IDs found!"


def test_cs50_inventory_completeness():
    assignments = reg.get_cs50_assignments()
    assert len(assignments) == 21
    weeks = {a["week"] for a in assignments}
    assert weeks == {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_deterministic_service_eligibility():
    services = reg.get_service_catalog(only_eligible=True)
    assert len(services) > 0
    for s in services:
        assert s["eligible"] is True
        assert len(s["evidence_project_ids"]) > 0, f"Service {s['id']} has no supporting projects!"
        for sub in s["subservices"]:
            assert sub["eligible"] is True


def test_service_validation_rejects_nonexistent_or_disabled():
    # Nonexistent
    valid, err = reg.validate_service_selection("nonexistent-service", None)
    assert valid is False
    assert "does not exist" in err

    # Disabled subservice
    valid, err = reg.validate_service_selection("ai-engineering", "rag-systems")
    assert valid is False
    assert "not currently active" in err

    # Valid service and active subservice
    valid, err = reg.validate_service_selection("data-ml", "predictive-ml")
    assert valid is True
    assert err == ""


# ==============================================================================
# 2. Public Portfolio Route Tests
# ==============================================================================

def test_portfolio_landing_page(client):
    resp = client.get("/portfolio")
    assert resp.status_code == 200
    assert b"Python Developer" in resp.data
    assert b"Featured Projects" in resp.data


def test_portfolio_projects_list(client):
    resp = client.get("/portfolio/projects")
    assert resp.status_code == 200
    assert b"Projects" in resp.data

    # Filter test
    resp_filter = client.get("/portfolio/projects?filter=data_ml")
    assert resp_filter.status_code == 200
    assert b"DATA ML" in resp_filter.data


def test_portfolio_project_detail_valid(client):
    resp = client.get("/portfolio/projects/chronic-disease-ml")
    assert resp.status_code == 200
    assert b"End-to-End Chronic Disease Prediction" in resp.data
    assert b"Known Limitations" in resp.data


def test_portfolio_project_detail_invalid(client):
    resp = client.get("/portfolio/projects/invalid-project-slug")
    assert resp.status_code == 404


def test_portfolio_services_page(client):
    resp = client.get("/portfolio/services")
    assert resp.status_code == 200
    assert b"Services &amp; Technical Capabilities" in resp.data
    assert b"Data Analytics &amp; Machine Learning" in resp.data


def test_portfolio_cs50_page(client):
    resp = client.get("/portfolio/cs50")
    assert resp.status_code == 200
    assert b"Harvard CS50x Coursework" in resp.data
    assert b"Tideman (Ranked Pairs)" in resp.data


# ==============================================================================
# 3. Commission & Service Inquiry Tests
# ==============================================================================

def test_inquiry_get(client):
    resp = client.get("/portfolio/inquire")
    assert resp.status_code == 200
    assert b"Start a Project" in resp.data


def test_inquiry_post_valid(client):
    payload = {
        "name": "Sarah Miller",
        "email": "sarah@example.com",
        "service": "data-ml",
        "subservice": "data-cleaning",
        "project": "chronic-disease-ml",
        "message": "We need automated cleaning and outlier rejection for our health dataset."
    }
    resp = client.post("/portfolio/inquire", data=payload)
    assert resp.status_code == 200
    assert b"successfully submitted" in resp.data


def test_inquiry_post_invalid_service(client):
    payload = {
        "name": "Sarah Miller",
        "email": "sarah@example.com",
        "service": "nonexistent-service",
        "message": "Testing invalid service injection."
    }
    resp = client.post("/portfolio/inquire", data=payload)
    assert resp.status_code == 200
    assert b"does not exist" in resp.data


def test_inquiry_post_invalid_subservice(client):
    payload = {
        "name": "Sarah Miller",
        "email": "sarah@example.com",
        "service": "ai-engineering",
        "subservice": "rag-systems",  # Disabled in registry
        "message": "Testing disabled subservice rejection."
    }
    resp = client.post("/portfolio/inquire", data=payload)
    assert resp.status_code == 200
    assert b"not currently active" in resp.data


# ==============================================================================
# 4. Protected Administration Tests
# ==============================================================================

def test_admin_inquiries_unauthorized_guest(client):
    resp = client.get("/admin/portfolio/inquiries")
    # Redirects to login
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_admin_inquiries_unauthorized_student(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 99
        sess["email"] = "student@ledger.edu"
        sess["authority"] = int(Authority.STUDENT)
        sess["state"] = int(AccountState.ACTIVE)
    resp = client.get("/admin/portfolio/inquiries")
    assert resp.status_code == 403


def test_admin_inquiries_authorized(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "admin@ledger.edu"
        sess["authority"] = int(Authority.ADMIN_L2)
        sess["state"] = int(AccountState.ACTIVE)
    resp = client.get("/admin/portfolio/inquiries")
    assert resp.status_code == 200
    assert b"Portfolio Commission Inquiries" in resp.data
