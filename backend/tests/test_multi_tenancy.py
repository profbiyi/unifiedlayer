"""
Multi-tenancy isolation tests.

Tests to ensure that organizations are properly isolated and users cannot
access resources from other organizations.
"""
import pytest
from fastapi import status
from sqlalchemy.orm import Session

from backend.models.pipeline import Organization, User, Pipeline, DataSource, Destination
from backend.auth import create_access_token, get_password_hash


@pytest.fixture
def org1(db: Session):
    """Create test organization 1."""
    org = Organization(
        name="Acme Corp",
        slug="acme-corp"
    )
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


@pytest.fixture
def org2(db: Session):
    """Create test organization 2."""
    org = Organization(
        name="TechCo",
        slug="techco"
    )
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


@pytest.fixture
def user1(db: Session, org1, setup_rbac):
    """Create test user 1 (belongs to org1) with ORG_USER role."""
    from backend.models.rbac import UserRole

    user = User(
        username="john",
        email="john@acme.com",
        hashed_password=get_password_hash("password123"),
        organization_id=org1.id
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    # Assign ORG_USER role
    user_role = UserRole(
        user_id=user.id,
        role_id=setup_rbac["org_user_role"].id,
        organization_id=org1.id
    )
    db.add(user_role)
    db.flush()

    return user


@pytest.fixture
def user2(db: Session, org2, setup_rbac):
    """Create test user 2 (belongs to org2) with ORG_USER role."""
    from backend.models.rbac import UserRole

    user = User(
        username="jane",
        email="jane@techco.com",
        hashed_password=get_password_hash("password123"),
        organization_id=org2.id
    )
    db.add(user)
    db.flush()
    db.refresh(user)

    # Assign ORG_USER role
    user_role = UserRole(
        user_id=user.id,
        role_id=setup_rbac["org_user_role"].id,
        organization_id=org2.id
    )
    db.add(user_role)
    db.flush()

    return user


@pytest.fixture
def source1(db: Session, org1):
    """Create test data source for org1."""
    source = DataSource(
        name="M-Pesa Source Acme",
        source_type="mpesa",
        organization_id=org1.id,
        config={"api_key": "test_key_1"}
    )
    db.add(source)
    db.flush()
    db.refresh(source)
    return source


@pytest.fixture
def source2(db: Session, org2):
    """Create test data source for org2."""
    source = DataSource(
        name="M-Pesa Source TechCo",
        source_type="mpesa",
        organization_id=org2.id,
        config={"api_key": "test_key_2"}
    )
    db.add(source)
    db.flush()
    db.refresh(source)
    return source


@pytest.fixture
def destination1(db: Session, org1):
    """Create test destination for org1."""
    dest = Destination(
        name="S3 Destination Acme",
        destination_type="s3",
        organization_id=org1.id,
        config={"bucket_url": "s3://acme-bucket"}
    )
    db.add(dest)
    db.flush()
    db.refresh(dest)
    return dest


@pytest.fixture
def destination2(db: Session, org2):
    """Create test destination for org2."""
    dest = Destination(
        name="S3 Destination TechCo",
        destination_type="s3",
        organization_id=org2.id,
        config={"bucket_url": "s3://techco-bucket"}
    )
    db.add(dest)
    db.flush()
    db.refresh(dest)
    return dest


@pytest.fixture
def pipeline1(db: Session, org1, source1, destination1):
    """Create test pipeline for org1."""
    pipeline = Pipeline(
        name="Pipeline Acme",
        organization_id=org1.id,
        source_id=source1.id,
        destination_id=destination1.id,
        is_active=True
    )
    db.add(pipeline)
    db.flush()
    db.refresh(pipeline)
    return pipeline


@pytest.fixture
def pipeline2(db: Session, org2, source2, destination2):
    """Create test pipeline for org2."""
    pipeline = Pipeline(
        name="Pipeline TechCo",
        organization_id=org2.id,
        source_id=source2.id,
        destination_id=destination2.id,
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


class TestPipelineIsolation:
    """Test pipeline isolation between organizations."""

    def test_user_can_list_own_pipelines(self, client, user1, pipeline1):
        """Test that user can list their own organization's pipelines."""
        headers = get_auth_headers(user1)
        response = client.get("/pipelines", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        pipelines = response.json()
        assert len(pipelines) == 1
        assert pipelines[0]["id"] == str(pipeline1.public_id)
        assert pipelines[0]["name"] == "Pipeline Acme"

    def test_user_cannot_see_other_org_pipelines(self, client, user1, user2, pipeline1, pipeline2):
        """Test that user cannot see pipelines from other organizations."""
        headers1 = get_auth_headers(user1)
        response1 = client.get("/pipelines", headers=headers1)

        assert response1.status_code == status.HTTP_200_OK
        pipelines1 = response1.json()
        assert len(pipelines1) == 1
        assert pipelines1[0]["id"] == str(pipeline1.public_id)
        assert all(p["id"] != str(pipeline2.public_id) for p in pipelines1)

        headers2 = get_auth_headers(user2)
        response2 = client.get("/pipelines", headers=headers2)

        assert response2.status_code == status.HTTP_200_OK
        pipelines2 = response2.json()
        assert len(pipelines2) == 1
        assert pipelines2[0]["id"] == str(pipeline2.public_id)
        assert all(p["id"] != str(pipeline1.public_id) for p in pipelines2)

    def test_user_cannot_get_other_org_pipeline_by_id(self, client, user1, pipeline2):
        """Test that user cannot access another organization's pipeline by ID."""
        headers = get_auth_headers(user1)
        response = client.get(f"/pipelines/{str(pipeline2.public_id)}", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_can_get_own_pipeline_by_id(self, client, user1, pipeline1):
        """Test that user can access their own organization's pipeline by ID."""
        headers = get_auth_headers(user1)
        response = client.get(f"/pipelines/{str(pipeline1.public_id)}", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        pipeline = response.json()
        assert pipeline["id"] == str(pipeline1.public_id)
        assert pipeline["name"] == "Pipeline Acme"

    def test_user_cannot_update_other_org_pipeline(self, client, user1, pipeline2):
        """Test that user cannot update another organization's pipeline."""
        headers = get_auth_headers(user1)
        response = client.put(
            f"/pipelines/{str(pipeline2.public_id)}",
            headers=headers,
            json={"name": "Hacked Pipeline"}
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_delete_other_org_pipeline(self, client, user1, pipeline2):
        """Test that user cannot delete another organization's pipeline."""
        headers = get_auth_headers(user1)
        response = client.delete(f"/pipelines/{str(pipeline2.public_id)}", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_trigger_other_org_pipeline(self, client, user1, pipeline2):
        """Test that user cannot trigger another organization's pipeline run."""
        headers = get_auth_headers(user1)
        response = client.post(f"/pipelines/{str(pipeline2.public_id)}/run", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPipelineCreationIsolation:
    """Test pipeline creation isolation between organizations."""

    def test_user_cannot_create_pipeline_for_other_org(self, client, user1, org2, source1, destination1):
        """Test that user cannot create a pipeline for another organization."""
        headers = get_auth_headers(user1)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Malicious Pipeline",
                "organization_id": org2.id,  # Trying to create for org2!
                "source_id": str(source1.public_id),
                "destination_id": str(destination1.public_id)
            }
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "different organization" in response.json()["detail"]

    def test_user_cannot_use_other_org_source(self, client, user1, org1, source2, destination1):
        """Test that user cannot use another organization's data source."""
        headers = get_auth_headers(user1)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Pipeline with stolen source",
                "organization_id": org1.id,
                "source_id": str(source2.public_id),  # Belongs to org2!
                "destination_id": str(destination1.public_id)
            }
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Source not found or access denied" in response.json()["detail"]

    def test_user_cannot_use_other_org_destination(self, client, user1, org1, source1, destination2):
        """Test that user cannot use another organization's destination."""
        headers = get_auth_headers(user1)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Pipeline with stolen destination",
                "organization_id": org1.id,
                "source_id": str(source1.public_id),
                "destination_id": str(destination2.public_id)  # Belongs to org2!
            }
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Destination not found or access denied" in response.json()["detail"]

    def test_user_can_create_pipeline_with_own_resources(self, client, user1, org1, source1, destination1):
        """Test that user can create pipeline with their own organization's resources."""
        headers = get_auth_headers(user1)
        response = client.post(
            "/pipelines",
            headers=headers,
            json={
                "name": "Valid Pipeline",
                "organization_id": org1.id,
                "source_id": str(source1.public_id),
                "destination_id": str(destination1.public_id)
            }
        )

        assert response.status_code == status.HTTP_201_CREATED
        pipeline = response.json()
        assert pipeline["name"] == "Valid Pipeline"
        assert pipeline["organization_id"] == org1.id


class TestSourceDestinationIsolation:
    """Test source and destination isolation between organizations."""

    def test_user_can_list_own_sources(self, client, user1, source1, source2):
        """Test that user can only see their own organization's sources."""
        headers = get_auth_headers(user1)
        response = client.get("/sources", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        sources = response.json()
        assert len(sources) == 1
        assert sources[0]["id"] == str(source1.public_id)
        assert all(s["id"] != str(source2.public_id) for s in sources)

    def test_user_can_list_own_destinations(self, client, user1, destination1, destination2):
        """Test that user can only see their own organization's destinations."""
        headers = get_auth_headers(user1)
        response = client.get("/destinations", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        destinations = response.json()
        assert len(destinations) == 1
        assert destinations[0]["id"] == str(destination1.public_id)
        assert all(d["id"] != str(destination2.public_id) for d in destinations)

    def test_user_cannot_get_other_org_source(self, client, user1, source2):
        """Test that user cannot access another organization's source by ID."""
        headers = get_auth_headers(user1)
        response = client.get(f"/sources/{str(source2.public_id)}", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_user_cannot_get_other_org_destination(self, client, user1, destination2):
        """Test that user cannot access another organization's destination by ID."""
        headers = get_auth_headers(user1)
        response = client.get(f"/destinations/{str(destination2.public_id)}", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestPipelineRunIsolation:
    """Test pipeline run isolation between organizations."""

    def test_user_can_view_own_pipeline_runs(self, client, user1, pipeline1):
        """Test that user can view runs for their own organization's pipelines."""
        headers = get_auth_headers(user1)
        response = client.get(f"/pipelines/{str(pipeline1.public_id)}/runs", headers=headers)

        assert response.status_code == status.HTTP_200_OK

    def test_user_cannot_view_other_org_pipeline_runs(self, client, user1, pipeline2):
        """Test that user cannot view runs for another organization's pipeline."""
        headers = get_auth_headers(user1)
        response = client.get(f"/pipelines/{str(pipeline2.public_id)}/runs", headers=headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
