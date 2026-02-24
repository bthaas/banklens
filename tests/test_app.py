import io
import json
from unittest.mock import patch

import pytest

import app as app_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    results_dir = tmp_path / "processed_results"
    upload_dir.mkdir()
    results_dir.mkdir()

    monkeypatch.setattr(app_module, "UPLOAD_FOLDER", upload_dir)
    monkeypatch.setattr(app_module, "RESULTS_FOLDER", results_dir)

    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")

    with app_module.app.test_client() as test_client:
        yield test_client, results_dir


def _post_csv(client, content: bytes, filename: str = "statement.csv"):
    return client.post(
        "/upload",
        data={"file": (io.BytesIO(content), filename)},
        content_type="multipart/form-data",
        follow_redirects=False,
    )


def test_upload_success_stores_server_side_result(client):
    test_client, results_dir = client
    csv_data = b"Date,Description,Amount\n2026-01-01,Coffee,-4.50\n"

    with patch.object(app_module, "categorize_transactions", return_value=["Food"]):
        response = _post_csv(test_client, csv_data)

    assert response.status_code == 302
    assert response.location.endswith("/results")

    with test_client.session_transaction() as flask_session:
        result_id = flask_session.get("result_id")
        assert result_id
        assert "transactions" not in flask_session

    result_path = results_dir / f"{result_id}.json"
    assert result_path.exists()
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload[0]["category"] == "Food"


def test_upload_replaces_previous_result_file(client):
    test_client, results_dir = client
    csv_data = b"Date,Description,Amount\n2026-01-01,Coffee,-4.50\n"

    with patch.object(app_module, "categorize_transactions", return_value=["Food"]):
        _post_csv(test_client, csv_data)
    with test_client.session_transaction() as flask_session:
        first_id = flask_session.get("result_id")
    assert first_id
    assert (results_dir / f"{first_id}.json").exists()

    with patch.object(app_module, "categorize_transactions", return_value=["Other"]):
        _post_csv(test_client, csv_data)
    with test_client.session_transaction() as flask_session:
        second_id = flask_session.get("result_id")
    assert second_id and second_id != first_id

    assert not (results_dir / f"{first_id}.json").exists()
    assert (results_dir / f"{second_id}.json").exists()


def test_upload_empty_csv_returns_clear_error(client):
    test_client, _ = client
    csv_data = b"Date,Description,Amount\n"

    with patch.object(app_module, "categorize_transactions", return_value=[]):
        response = _post_csv(test_client, csv_data)

    assert response.status_code == 302
    assert "No+transactions+found+in+the+CSV+file." in response.location


def test_upload_invalid_file_type_rejected(client):
    test_client, _ = client
    response = _post_csv(test_client, b"Date,Description,Amount\n", filename="statement.txt")

    assert response.status_code == 302
    assert "Invalid+file+type" in response.location


def test_results_without_result_id_redirects(client):
    test_client, _ = client
    response = test_client.get("/results", follow_redirects=False)

    assert response.status_code == 302
    assert "Upload+a+CSV+file+to+view+results." in response.location


def test_upload_handles_openai_failure(client):
    test_client, _ = client
    csv_data = b"Date,Description,Amount\n2026-01-01,Coffee,-4.50\n"

    with patch.object(app_module, "categorize_transactions", side_effect=RuntimeError("API down")):
        response = _post_csv(test_client, csv_data)

    assert response.status_code == 302
    assert "API+down" in response.location


def test_compute_summary_logic():
    """Verify that compute_summary correctly separates income and expenses."""
    transactions = [
        {"amount": -10.0, "category": "Food"},
        {"amount": -20.0, "category": "Transport"},
        {"amount": 100.0, "category": "Salary"},  # Income
    ]
    summary = app_module.compute_summary(transactions)

    assert summary["total_spent"] == 30.0  # abs(-10 + -20)
    assert summary["total_income"] == 100.0
    assert summary["biggest_expense"] == 20.0
    assert summary["category_totals"]["Food"] == 10.0
    assert summary["category_totals"]["Transport"] == 20.0
    assert "Salary" not in summary["category_totals"]  # Income not in spending breakdown
