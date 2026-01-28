"""
Tests for Access Control (RBAC) Service
========================================

Comprehensive test suite for role-based access control, including:
- Permission checks
- Role assignments
- Role revocation
- User permissions retrieval
- Default role validation
"""

import pytest
from datetime import datetime, timedelta, timezone
from src.services.access_control import (
    AccessControl,
    Role,
    Permission,
    RoleDefinition,
    RoleAssignment,
)


@pytest.fixture
def access_control():
    """Create a fresh access control instance for each test."""
    return AccessControl()


@pytest.fixture
def admin_user(access_control):
    """Create an admin user."""
    access_control.assign_role(
        user_id="admin-1",
        role=Role.ADMIN,
        assigned_by="system",
    )
    return "admin-1"


class TestRoleDefinition:
    """Tests for RoleDefinition class."""

    def test_role_definition_creation(self):
        """Test creating a role definition."""
        role = RoleDefinition(
            name=Role.ANALYST,
            description="Test analyst role",
            permissions={Permission.CANVAS_READ, Permission.CANVAS_CREATE},
        )

        assert role.name == Role.ANALYST
        assert Permission.CANVAS_READ in role.permissions

    def test_has_permission(self):
        """Test checking if role has permission."""
        role = RoleDefinition(
            name=Role.ANALYST,
            description="Test analyst role",
            permissions={Permission.CANVAS_READ, Permission.CANVAS_CREATE},
        )

        assert role.has_permission(Permission.CANVAS_READ)
        assert not role.has_permission(Permission.CANVAS_DELETE)

    def test_admin_has_all_permissions(self):
        """Test that admin role has all permissions."""
        role = RoleDefinition(
            name=Role.ADMIN,
            description="Admin role",
            permissions={Permission.ADMIN_ALL},
        )

        assert role.has_permission(Permission.ADMIN_ALL)
        assert role.has_permission(Permission.CANVAS_READ)
        assert role.has_permission(Permission.CANVAS_DELETE)
        assert role.has_permission(Permission.PERMISSION_GRANT)

    def test_add_permission(self):
        """Test adding permission to role."""
        role = RoleDefinition(
            name=Role.VIEWER,
            description="Test viewer role",
            permissions={Permission.CANVAS_READ},
        )

        assert not role.has_permission(Permission.CANVAS_UPDATE)

        role.add_permission(Permission.CANVAS_UPDATE)

        assert role.has_permission(Permission.CANVAS_UPDATE)

    def test_remove_permission(self):
        """Test removing permission from role."""
        role = RoleDefinition(
            name=Role.ANALYST,
            description="Test analyst role",
            permissions={Permission.CANVAS_READ, Permission.CANVAS_UPDATE},
        )

        assert role.has_permission(Permission.CANVAS_UPDATE)

        role.remove_permission(Permission.CANVAS_UPDATE)

        assert not role.has_permission(Permission.CANVAS_UPDATE)


class TestDefaultRoles:
    """Tests for default role initialization."""

    def test_admin_role_created(self, access_control):
        """Test that admin role is created by default."""
        assert Role.ADMIN in access_control.role_definitions
        role = access_control.role_definitions[Role.ADMIN]
        assert role.has_permission(Permission.ADMIN_ALL)

    def test_analyst_role_created(self, access_control):
        """Test that analyst role is created by default."""
        assert Role.ANALYST in access_control.role_definitions
        role = access_control.role_definitions[Role.ANALYST]
        assert role.has_permission(Permission.CANVAS_CREATE)
        assert role.has_permission(Permission.CANVAS_READ)
        assert role.has_permission(Permission.CANVAS_UPDATE)
        assert not role.has_permission(Permission.CANVAS_DELETE)

    def test_viewer_role_created(self, access_control):
        """Test that viewer role is created by default."""
        assert Role.VIEWER in access_control.role_definitions
        role = access_control.role_definitions[Role.VIEWER]
        assert role.has_permission(Permission.CANVAS_READ)
        assert not role.has_permission(Permission.CANVAS_CREATE)
        assert not role.has_permission(Permission.CANVAS_UPDATE)

    def test_investigator_role_created(self, access_control):
        """Test that investigator role is created by default."""
        assert Role.INVESTIGATOR in access_control.role_definitions
        role = access_control.role_definitions[Role.INVESTIGATOR]
        assert role.has_permission(Permission.CANVAS_ANALYZE)
        assert not role.has_permission(Permission.CANVAS_CREATE)


class TestAssignRole:
    """Tests for role assignment."""

    def test_assign_role_to_user(self, access_control, admin_user):
        """Test assigning a role to a user."""
        assignment = access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
        )

        assert assignment.user_id == "user-1"
        assert assignment.role == Role.ANALYST
        assert assignment.is_active

    def test_assign_role_requires_permission(self, access_control):
        """Test that assigning role requires permission."""
        with pytest.raises(PermissionError):
            access_control.assign_role(
                user_id="user-1",
                role=Role.ANALYST,
                assigned_by="unauthorized-user",
            )

    def test_assign_resource_specific_role(self, access_control, admin_user):
        """Test assigning role for specific resource."""
        assignment = access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
            resource_id="canvas-1",
        )

        assert assignment.resource_id == "canvas-1"

    def test_assign_role_with_expiration(self, access_control, admin_user):
        """Test assigning role with expiration time."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        assignment = access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
            expires_at=expires_at,
        )

        assert assignment.expires_at == expires_at


class TestPermissionChecks:
    """Tests for permission checking."""

    def test_check_permission_success(self, access_control, admin_user):
        """Test successful permission check."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
        )

        has_perm = access_control.check_permission(
            "user-1",
            Permission.CANVAS_CREATE,
        )

        assert has_perm is True

    def test_check_permission_failure(self, access_control, admin_user):
        """Test failed permission check."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.VIEWER,
            assigned_by=admin_user,
        )

        has_perm = access_control.check_permission(
            "user-1",
            Permission.CANVAS_CREATE,
        )

        assert has_perm is False

    def test_check_permission_for_unassigned_user(self, access_control):
        """Test permission check for user without roles."""
        has_perm = access_control.check_permission(
            "unknown-user",
            Permission.CANVAS_READ,
        )

        assert has_perm is False

    def test_check_permission_with_expired_role(self, access_control, admin_user):
        """Test permission check with expired role."""
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Already expired

        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
            expires_at=expires_at,
        )

        has_perm = access_control.check_permission(
            "user-1",
            Permission.CANVAS_CREATE,
        )

        assert has_perm is False

    def test_check_resource_specific_permission(self, access_control, admin_user):
        """Test resource-specific permission check."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
            resource_id="canvas-1",
        )

        # Should have permission for canvas-1
        has_perm = access_control.check_permission(
            "user-1",
            Permission.CANVAS_READ,
            resource_id="canvas-1",
        )
        assert has_perm is True

        # Should not have permission for canvas-2
        has_perm = access_control.check_permission(
            "user-1",
            Permission.CANVAS_READ,
            resource_id="canvas-2",
        )
        assert has_perm is False

    def test_global_role_allows_all_resources(self, access_control, admin_user):
        """Test that global role allows access to all resources."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
            resource_id=None,  # Global role
        )

        # Should have permission for any resource
        has_perm1 = access_control.check_permission(
            "user-1",
            Permission.CANVAS_READ,
            resource_id="canvas-1",
        )
        has_perm2 = access_control.check_permission(
            "user-1",
            Permission.CANVAS_READ,
            resource_id="canvas-2",
        )

        assert has_perm1 is True
        assert has_perm2 is True


class TestRoleRevocation:
    """Tests for role revocation."""

    def test_revoke_role(self, access_control, admin_user):
        """Test revoking a role from a user."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
        )

        assert access_control.check_permission("user-1", Permission.CANVAS_CREATE)

        access_control.revoke_role(
            user_id="user-1",
            role=Role.ANALYST,
            revoked_by=admin_user,
        )

        assert not access_control.check_permission("user-1", Permission.CANVAS_CREATE)

    def test_revoke_role_requires_permission(self, access_control, admin_user):
        """Test that revoking role requires permission."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
        )

        with pytest.raises(PermissionError):
            access_control.revoke_role(
                user_id="user-1",
                role=Role.ANALYST,
                revoked_by="unauthorized-user",
            )

    def test_revoke_nonexistent_role(self, access_control, admin_user):
        """Test revoking a role that was not assigned."""
        result = access_control.revoke_role(
            user_id="user-1",
            role=Role.ANALYST,
            revoked_by=admin_user,
        )

        assert result is False

    def test_revoke_resource_specific_role(self, access_control, admin_user):
        """Test revoking a resource-specific role."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
            resource_id="canvas-1",
        )

        access_control.revoke_role(
            user_id="user-1",
            role=Role.ANALYST,
            revoked_by=admin_user,
            resource_id="canvas-1",
        )

        # Should not have permission for canvas-1
        has_perm = access_control.check_permission(
            "user-1",
            Permission.CANVAS_READ,
            resource_id="canvas-1",
        )
        assert has_perm is False


class TestUserPermissions:
    """Tests for retrieving user permissions."""

    def test_get_user_permissions(self, access_control, admin_user):
        """Test getting all permissions for a user."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
        )

        permissions = access_control.get_user_permissions("user-1")

        assert "global" in permissions
        assert "canvas:create" in permissions["global"]
        assert "canvas:read" in permissions["global"]

    def test_get_user_roles(self, access_control, admin_user):
        """Test getting all roles for a user."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
        )
        access_control.assign_role(
            user_id="user-1",
            role=Role.INVESTIGATOR,
            assigned_by=admin_user,
            resource_id="canvas-1",
        )

        roles = access_control.get_user_roles("user-1")

        assert len(roles) == 2
        assert (Role.ANALYST, None) in roles
        assert (Role.INVESTIGATOR, "canvas-1") in roles

    def test_get_permissions_multiple_roles(self, access_control, admin_user):
        """Test getting permissions with multiple roles."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.VIEWER,
            assigned_by=admin_user,
        )
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
            resource_id="canvas-1",
        )

        permissions = access_control.get_user_permissions("user-1")

        # Global permissions from VIEWER role
        assert "global" in permissions
        assert "canvas:read" in permissions["global"]

        # Canvas-1 specific permissions from ANALYST role
        assert "canvas-1" in permissions
        assert "canvas:create" in permissions["canvas-1"]


class TestAdminAccess:
    """Tests for admin access checks."""

    def test_has_admin_access_true(self, access_control, admin_user):
        """Test detecting admin access."""
        assert access_control.has_admin_access(admin_user) is True

    def test_has_admin_access_false(self, access_control, admin_user):
        """Test detecting non-admin user."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.VIEWER,
            assigned_by=admin_user,
        )

        assert access_control.has_admin_access("user-1") is False


class TestAssignmentHistory:
    """Tests for role assignment history."""

    def test_get_assignment_history(self, access_control, admin_user):
        """Test retrieving assignment history."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
        )
        access_control.assign_role(
            user_id="user-1",
            role=Role.VIEWER,
            assigned_by=admin_user,
        )
        access_control.assign_role(
            user_id="user-2",
            role=Role.INVESTIGATOR,
            assigned_by=admin_user,
        )

        history = access_control.get_assignment_history()

        assert len(history) >= 3

    def test_get_assignment_history_for_user(self, access_control, admin_user):
        """Test retrieving assignment history for specific user."""
        access_control.assign_role(
            user_id="user-1",
            role=Role.ANALYST,
            assigned_by=admin_user,
        )
        access_control.assign_role(
            user_id="user-1",
            role=Role.VIEWER,
            assigned_by=admin_user,
        )

        history = access_control.get_assignment_history("user-1")

        assert len(history) == 2
        assert all(a.user_id == "user-1" for a in history)
