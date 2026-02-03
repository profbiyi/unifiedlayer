"""
Pipeline creation and management tests.

Tests for pipeline CRUD operations, validation, and business logic.
"""
import pytest
from fastapi import status
from sqlalchemy.orm import Session

from backend.models.pipeline import Organization, User, Pipeline, DataSource, Destination, PipelineStatus
from backend.auth import create_access_token, get_password_hash


@pytest.fixture
def test_org(db: Session):
    """Create test organization."""
    org = Organization(name="Test Org", slug="test-org")
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


@pytest.fixture
def test_user(db: Session, test_org, setup_rbac):
    """Create test user with ORG_USER role."""
    from backend.models.rbac import UserRole

    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        organization_id=test_org.id
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    # Assign ORG_USER role
    user_role = UserRole(
        user_id=user.id,
        role_id=setup_rbac["org_user_role"].id,
        organization_id=test_org.id
    )
    db.add(user_role)
    db.flush()

    return user


@pytest.fixture
def test_source(db: Session, test_org):
    """Create test data source."""
    source = DataSource(
        name="Test M-Pesa Source",
        source_type="mpesa",
        organization_id=test_org.id,
        config={"api_key": "test_key", "environment": "sandbox"}
    )
    db.add(source)
    db.flush()
    db.refresh(source)
    return source


@pytest.fixture
def test_destination(db: Session, test_org):
    """Create test destination."""
    dest = Destination(
        name="Test S3 Destination",
        destination_type="s3",
        organization_id=test_org.id,
        config={"bucket_url": "s3://test-bucket", "file_format": "parquet"}
    )
    db.add(dest)
    db.flush()
    db.refresh(dest)
    return dest


@pytest.fixture
def test_pipeline(db: Session, test_org, test_source, test_destination):
    """Create test pipeline."""
    pipeline = Pipeline(
        name="Test Pipeline",
        description="A test pipeline",
        organization_id=test_org.id,
        source_id=test_source.id,
        destination_id=test_destination.id,
        is_active=True
    )
    db.add(pipeline)
    db.flush()
    db.refresh(pipeline)
    return pipeline


def get_auth_headers(user: User) -> dict:
    """Get authorization headers for a user."""
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestPipelineCreation:
    """Test pipeline creation."""

    def test_create_pipeline_success(self, client, test_user, test_org, test_source, test_destination):
        """Test successful pipeline creation."""
        headers = get_auth_headers(test_user)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "New Pipeline",
                "description": "Test pipeline description",
                "organization_id": test_org.id,
                "source_id": str(test_source.public_id),
                "destination_id": str(test_destination.public_id),
                "schedule": "0 * * * *"
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        pipeline = response.json()
        assert pipeline["name"] == "New Pipeline"
        assert pipeline["description"] == "Test pipeline description"
        assert pipeline["organization_id"] == test_org.id
        assert pipeline["source_id"] == test_source.id
        assert pipeline["destination_id"] == test_destination.id
        assert pipeline["is_active"] is True

    def test_create_pipeline_minimal_fields(self, client, test_user, test_org, test_source, test_destination):
        """Test creating pipeline with only required fields."""
        headers = get_auth_headers(test_user)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Minimal Pipeline",
                "organization_id": test_org.id,
                "source_id": str(test_source.public_id),
                "destination_id": str(test_destination.public_id)
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        pipeline = response.json()
        assert pipeline["name"] == "Minimal Pipeline"
        assert pipeline["is_active"] is True

    def test_create_pipeline_with_config(self, client, test_user, test_org, test_source, test_destination):
        """Test creating pipeline with custom config."""
        headers = get_auth_headers(test_user)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Configured Pipeline",
                "organization_id": test_org.id,
                "source_id": str(test_source.public_id),
                "destination_id": str(test_destination.public_id),
                "config": {
                    "batch_size": 1000,
                    "retry_count": 3
                }
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        pipeline = response.json()
        assert pipeline["config"]["batch_size"] == 1000
        assert pipeline["config"]["retry_count"] == 3

    def test_create_pipeline_without_authentication(self, client, test_org, test_source, test_destination):
        """Test that creating pipeline requires authentication."""
        response = client.post(
            "/pipelines",
            json={
                "name": "Unauthorized Pipeline",
                "organization_id": test_org.id,
                "source_id": str(test_source.public_id),
                "destination_id": str(test_destination.public_id)
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPipelineRetrieval:
    """Test pipeline retrieval."""

    def test_list_pipelines(self, client, test_user, test_pipeline):
        """Test listing pipelines."""
        headers = get_auth_headers(test_user)
        response = client.get("/pipelines", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        pipelines = response.json()
        assert isinstance(pipelines, list)
        assert len(pipelines) >= 1
        assert any(p["id"] == str(test_pipeline.public_id) for p in pipelines)

    def test_list_pipelines_pagination(self, client, test_user, test_pipeline):
        """Test pipeline listing with pagination."""
        headers = get_auth_headers(test_user)
        response = client.get("/pipelines?skip=0&limit=10", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        pipelines = response.json()
        assert len(pipelines) <= 10

    def test_list_pipelines_filter_active(self, client, test_user, test_pipeline):
        """Test filtering pipelines by active status."""
        headers = get_auth_headers(test_user)
        response = client.get("/pipelines?is_active=true", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        pipelines = response.json()
        assert all(p["is_active"] is True for p in pipelines)

    def test_get_pipeline_by_id(self, client, test_user, test_pipeline):
        """Test getting a specific pipeline by ID."""
        headers = get_auth_headers(test_user)
        response = client.get(f"/pipelines/{str(test_pipeline.public_id)}", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        pipeline = response.json()
        assert pipeline["id"] == str(test_pipeline.public_id)
        assert pipeline["name"] == "Test Pipeline"

    def test_get_nonexistent_pipeline(self, client, test_user):
        """Test getting a non-existent pipeline."""
        headers = get_auth_headers(test_user)
        response = client.get("/pipelines/00000000-0000-0000-0000-000000000000", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPipelineUpdate:
    """Test pipeline updates."""

    def test_update_pipeline_name(self, client, test_user, test_pipeline):
        """Test updating pipeline name."""
        headers = get_auth_headers(test_user)
        response = client.put(
            f"/pipelines/{str(test_pipeline.public_id)}",
            headers=headers,
            json={"name": "Updated Pipeline Name"}
        )

        assert response.status_code == status.HTTP_200_OK
        pipeline = response.json()
        assert pipeline["name"] == "Updated Pipeline Name"

    def test_update_pipeline_description(self, client, test_user, test_pipeline):
        """Test updating pipeline description."""
        headers = get_auth_headers(test_user)
        response = client.put(
            f"/pipelines/{str(test_pipeline.public_id)}",
            headers=headers,
            json={"description": "New description"}
        )

        assert response.status_code == status.HTTP_200_OK
        pipeline = response.json()
        assert pipeline["description"] == "New description"

    def test_update_pipeline_schedule(self, client, test_user, test_pipeline):
        """Test updating pipeline schedule."""
        headers = get_auth_headers(test_user)
        response = client.put(
            f"/pipelines/{str(test_pipeline.public_id)}",
            headers=headers,
            json={"schedule": "0 */2 * * *"}  # Every 2 hours
        )

        assert response.status_code == status.HTTP_200_OK
        pipeline = response.json()
        assert pipeline["schedule"] == "0 */2 * * *"

    def test_update_pipeline_deactivate(self, client, test_user, test_pipeline):
        """Test deactivating a pipeline."""
        headers = get_auth_headers(test_user)
        response = client.put(
            f"/pipelines/{str(test_pipeline.public_id)}",
            headers=headers,
            json={"is_active": False}
        )

        assert response.status_code == status.HTTP_200_OK
        pipeline = response.json()
        assert pipeline["is_active"] is False

    def test_update_pipeline_config(self, client, test_user, test_pipeline):
        """Test updating pipeline config."""
        headers = get_auth_headers(test_user)
        response = client.put(
            f"/pipelines/{str(test_pipeline.public_id)}",
            headers=headers,
            json={
                "config": {
                    "batch_size": 5000,
                    "timeout": 300
                }
            }
        )

        assert response.status_code == status.HTTP_200_OK
        pipeline = response.json()
        assert pipeline["config"]["batch_size"] == 5000

    def test_update_nonexistent_pipeline(self, client, test_user):
        """Test updating a non-existent pipeline."""
        headers = get_auth_headers(test_user)
        response = client.put(
            "/pipelines/00000000-0000-0000-0000-000000000000",
            headers=headers,
            json={"name": "Updated Name"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPipelineDeletion:
    """Test pipeline deletion."""

    def test_delete_pipeline(self, client, test_user, test_pipeline):
        """Test deleting a pipeline."""
        headers = get_auth_headers(test_user)
        pipeline_id = str(test_pipeline.public_id)

        response = client.delete(f"/pipelines/{pipeline_id}", headers=headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify it's deleted
        get_response = client.get(f"/pipelines/{pipeline_id}", headers=headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_pipeline(self, client, test_user):
        """Test deleting a non-existent pipeline."""
        headers = get_auth_headers(test_user)
        response = client.delete("/pipelines/00000000-0000-0000-0000-000000000000", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPipelineExecution:
    """Test pipeline execution triggers."""

    def test_trigger_pipeline_run(self, client, test_user, test_pipeline):
        """Test triggering a pipeline run."""
        headers = get_auth_headers(test_user)
        response = client.post(f"/pipelines/{str(test_pipeline.public_id)}/run", headers=headers)

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "run_id" in data
        assert data["pipeline_id"] == str(test_pipeline.public_id)
        assert "status" in data

    def test_trigger_inactive_pipeline(self, client, test_user, db: Session, test_pipeline):
        """Test that inactive pipelines cannot be triggered."""
        # Deactivate pipeline
        test_pipeline.is_active = False
        db.flush()

        headers = get_auth_headers(test_user)
        response = client.post(f"/pipelines/{str(test_pipeline.public_id)}/run", headers=headers)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not active" in response.json()["detail"].lower()

    def test_trigger_nonexistent_pipeline(self, client, test_user):
        """Test triggering a non-existent pipeline."""
        headers = get_auth_headers(test_user)
        response = client.post("/pipelines/00000000-0000-0000-0000-000000000000/run", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPipelineRuns:
    """Test pipeline run listing and retrieval."""

    def test_list_pipeline_runs(self, client, test_user, test_pipeline):
        """Test listing runs for a pipeline."""
        headers = get_auth_headers(test_user)
        response = client.get(f"/pipelines/{str(test_pipeline.public_id)}/runs", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        runs = response.json()
        assert isinstance(runs, list)

    def test_list_pipeline_runs_pagination(self, client, test_user, test_pipeline):
        """Test pipeline runs with pagination."""
        headers = get_auth_headers(test_user)
        response = client.get(
            f"/pipelines/{str(test_pipeline.public_id)}/runs?skip=0&limit=10",
            headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        runs = response.json()
        assert len(runs) <= 10

    def test_list_runs_nonexistent_pipeline(self, client, test_user):
        """Test listing runs for non-existent pipeline."""
        headers = get_auth_headers(test_user)
        response = client.get("/pipelines/00000000-0000-0000-0000-000000000000/runs", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPipelineValidation:
    """Test pipeline validation."""

    def test_create_pipeline_missing_name(self, client, test_user, test_org, test_source, test_destination):
        """Test that pipeline creation fails without name."""
        headers = get_auth_headers(test_user)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "organization_id": test_org.id,
                "source_id": str(test_source.public_id),
                "destination_id": str(test_destination.public_id)
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_pipeline_missing_source(self, client, test_user, test_org, test_destination):
        """Test that pipeline creation fails without source."""
        headers = get_auth_headers(test_user)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Invalid Pipeline",
                "organization_id": test_org.id,
                "destination_id": str(test_destination.public_id)
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_pipeline_missing_destination(self, client, test_user, test_org, test_source):
        """Test that pipeline creation fails without destination."""
        headers = get_auth_headers(test_user)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Invalid Pipeline",
                "organization_id": test_org.id,
                "source_id": str(test_source.public_id)
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_pipeline_nonexistent_source(self, client, test_user, test_org, test_destination):
        """Test that pipeline creation fails with non-existent source."""
        headers = get_auth_headers(test_user)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Invalid Pipeline",
                "organization_id": test_org.id,
                "source_id": "00000000-0000-0000-0000-000000000000",  # Non-existent
                "destination_id": str(test_destination.public_id)
            }
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_pipeline_nonexistent_destination(self, client, test_user, test_org, test_source):
        """Test that pipeline creation fails with non-existent destination."""
        headers = get_auth_headers(test_user)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Invalid Pipeline",
                "organization_id": test_org.id,
                "source_id": str(test_source.public_id),
                "destination_id": "00000000-0000-0000-0000-000000000000"  # Non-existent
            }
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
