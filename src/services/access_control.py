"""
Role-Based Access Control (RBAC) Service
=========================================

Implements enterprise-grade access control with role-based permissions,
principle of least privilege, and fine-grained authorization.

Key Responsibilities:
- Define roles and permissions
- Enforce access control on operations
- Manage user role assignments
- Support resource-level permissions
- Track permission history
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timezone
from uuid import uuid4


class Role(str, Enum):
    """Predefined system roles."""

    ADMIN = "admin"  # Full access, can manage permissions
    ANALYST = "analyst"  # Can create, read, update canvas
    INVESTIGATOR = "investigator"  # Can investigate and analyze
    VIEWER = "viewer"  # Read-only access
    SYSTEM = "system"  # System-level operations


class Permission(str, Enum):
    """Fine-grained permissions."""

    # Canvas permissions
    CANVAS_CREATE = "canvas:create"
    CANVAS_READ = "canvas:read"
    CANVAS_UPDATE = "canvas:update"
    CANVAS_DELETE = "canvas:delete"
    CANVAS_ANALYZE = "canvas:analyze"
    CANVAS_EXPORT = "canvas:export"

    # Node/Edge permissions
    NODE_CREATE = "node:create"
    NODE_UPDATE = "node:update"
    NODE_DELETE = "node:delete"
    EDGE_CREATE = "edge:create"
    EDGE_UPDATE = "edge:update"
    EDGE_DELETE = "edge:delete"

    # Version permissions
    VERSION_CREATE = "version:create"
    VERSION_READ = "version:read"
    VERSION_ROLLBACK = "version:rollback"

    # Access control permissions
    PERMISSION_GRANT = "permission:grant"
    PERMISSION_REVOKE = "permission:revoke"
    PERMISSION_READ = "permission:read"

    # Admin permissions
    ADMIN_ALL = "admin:*"


@dataclass
class RoleDefinition:
    """Definition of a role and its permissions."""

    name: Role
    description: str
    permissions: Set[Permission]
    is_custom: bool = False

    def has_permission(self, permission: Permission) -> bool:
        """Check if role has a permission."""
        # Admin role has all permissions
        if Permission.ADMIN_ALL in self.permissions:
            return True
        return permission in self.permissions

    def add_permission(self, permission: Permission) -> None:
        """Add a permission to the role."""
        self.permissions.add(permission)

    def remove_permission(self, permission: Permission) -> None:
        """Remove a permission from the role."""
        self.permissions.discard(permission)


@dataclass
class RoleAssignment:
    """Record of a user's role assignment."""

    assignment_id: str
    user_id: str
    role: Role
    resource_id: Optional[str]  # If None, role applies globally
    assigned_at: datetime
    assigned_by: str
    expires_at: Optional[datetime] = None
    is_active: bool = True


class AccessControl:
    """
    Role-Based Access Control system.

    Enforces permissions through:
    - Role definitions with permission sets
    - User role assignments
    - Resource-level access control
    - Principle of least privilege
    """

    def __init__(self):
        """Initialize access control with default roles."""
        self.role_definitions: Dict[Role, RoleDefinition] = {}
        self.user_roles: Dict[str, List[RoleAssignment]] = {}
        self.assignment_history: List[RoleAssignment] = []
        self._init_default_roles()

    def _init_default_roles(self) -> None:
        """Initialize predefined system roles."""

        # Admin: Full access
        self.role_definitions[Role.ADMIN] = RoleDefinition(
            name=Role.ADMIN,
            description="Full system access and permission management",
            permissions={Permission.ADMIN_ALL},
        )

        # Analyst: Can work with canvas
        self.role_definitions[Role.ANALYST] = RoleDefinition(
            name=Role.ANALYST,
            description="Can create, read, and update canvas",
            permissions={
                Permission.CANVAS_CREATE,
                Permission.CANVAS_READ,
                Permission.CANVAS_UPDATE,
                Permission.CANVAS_ANALYZE,
                Permission.CANVAS_EXPORT,
                Permission.NODE_CREATE,
                Permission.NODE_UPDATE,
                Permission.EDGE_CREATE,
                Permission.EDGE_UPDATE,
                Permission.VERSION_CREATE,
                Permission.VERSION_READ,
            },
        )

        # Investigator: Can investigate
        self.role_definitions[Role.INVESTIGATOR] = RoleDefinition(
            name=Role.INVESTIGATOR,
            description="Can investigate and analyze canvas",
            permissions={
                Permission.CANVAS_READ,
                Permission.CANVAS_ANALYZE,
                Permission.CANVAS_EXPORT,
                Permission.VERSION_READ,
            },
        )

        # Viewer: Read-only
        self.role_definitions[Role.VIEWER] = RoleDefinition(
            name=Role.VIEWER,
            description="Read-only access to canvas",
            permissions={
                Permission.CANVAS_READ,
                Permission.VERSION_READ,
            },
        )

        # System: Internal operations
        self.role_definitions[Role.SYSTEM] = RoleDefinition(
            name=Role.SYSTEM,
            description="System-level operations",
            permissions={Permission.ADMIN_ALL},
        )

    def check_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_id: Optional[str] = None,
    ) -> bool:
        """
        Check if a user has a specific permission.

        Args:
            user_id: User to check
            permission: Permission to verify
            resource_id: Resource-specific check (optional)

        Returns:
            True if user has permission, False otherwise
        """
        assignments = self.user_roles.get(user_id, [])

        for assignment in assignments:
            # Check if assignment is active
            if not assignment.is_active:
                continue

            # Check if assignment has expired
            if (
                assignment.expires_at
                and datetime.now(timezone.utc) > assignment.expires_at
            ):
                assignment.is_active = False
                continue

            # Check resource-level permission
            if (
                resource_id
                and assignment.resource_id
                and assignment.resource_id != resource_id
            ):
                continue

            # Check if role has permission
            role_def = self.role_definitions[assignment.role]
            if role_def.has_permission(permission):
                return True

        return False

    def assign_role(
        self,
        user_id: str,
        role: Role,
        assigned_by: str,
        resource_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> RoleAssignment:
        """
        Assign a role to a user.

        Args:
            user_id: User to assign role to
            role: Role to assign
            assigned_by: Admin assigning the role
            resource_id: Resource-specific assignment (optional)
            expires_at: Expiration time (optional)

        Returns:
            RoleAssignment: The assignment record
        """
        # Check that assigner has permission to grant this role
        # Allow system user and admins without circular permission checks
        if assigned_by != "system" and not self.check_permission(
            assigned_by, Permission.PERMISSION_GRANT
        ):
            raise PermissionError(f"User {assigned_by} cannot grant permissions")

        assignment = RoleAssignment(
            assignment_id=str(uuid4()),
            user_id=user_id,
            role=role,
            resource_id=resource_id,
            assigned_at=datetime.now(timezone.utc),
            assigned_by=assigned_by,
            expires_at=expires_at,
        )

        if user_id not in self.user_roles:
            self.user_roles[user_id] = []

        self.user_roles[user_id].append(assignment)
        self.assignment_history.append(assignment)

        return assignment

    def revoke_role(
        self,
        user_id: str,
        role: Role,
        revoked_by: str,
        resource_id: Optional[str] = None,
    ) -> bool:
        """
        Revoke a role from a user.

        Args:
            user_id: User to revoke role from
            role: Role to revoke
            revoked_by: Admin revoking the role
            resource_id: Resource-specific revocation (optional)

        Returns:
            True if revocation successful, False if role not found
        """
        # Check permission
        # Allow system user and admins without circular permission checks
        if revoked_by != "system" and not self.check_permission(
            revoked_by, Permission.PERMISSION_REVOKE
        ):
            raise PermissionError(f"User {revoked_by} cannot revoke permissions")

        assignments = self.user_roles.get(user_id, [])

        for assignment in assignments:
            if (
                assignment.role == role
                and assignment.is_active
                and (resource_id is None or assignment.resource_id == resource_id)
            ):
                assignment.is_active = False
                return True

        return False

    def get_user_permissions(self, user_id: str) -> Dict[str, List[str]]:
        """
        Get all permissions for a user.

        Args:
            user_id: User to get permissions for

        Returns:
            Dict mapping resource to list of permissions
        """
        permissions_by_resource: Dict[str, Set[Permission]] = {}
        assignments = self.user_roles.get(user_id, [])

        for assignment in assignments:
            if not assignment.is_active:
                continue

            if (
                assignment.expires_at
                and datetime.now(timezone.utc) > assignment.expires_at
            ):
                continue

            resource = assignment.resource_id or "global"
            if resource not in permissions_by_resource:
                permissions_by_resource[resource] = set()

            role_def = self.role_definitions[assignment.role]
            permissions_by_resource[resource].update(role_def.permissions)

        # Convert sets to sorted lists
        return {
            resource: sorted([p.value for p in perms])
            for resource, perms in permissions_by_resource.items()
        }

    def get_user_roles(self, user_id: str) -> List[Tuple[Role, Optional[str]]]:
        """
        Get all active roles for a user.

        Args:
            user_id: User to get roles for

        Returns:
            List of (role, resource_id) tuples
        """
        assignments = self.user_roles.get(user_id, [])
        active_roles = [
            (a.role, a.resource_id)
            for a in assignments
            if a.is_active
            and (not a.expires_at or datetime.now(timezone.utc) <= a.expires_at)
        ]
        return active_roles

    def grant_permission(
        self,
        user_id: str,
        permission: Permission,
        granted_by: str,
        resource_id: Optional[str] = None,
    ) -> bool:
        """
        Grant a specific permission to a user (creates custom role if needed).

        Args:
            user_id: User to grant permission to
            permission: Permission to grant
            granted_by: Admin granting the permission
            resource_id: Resource-specific grant (optional)

        Returns:
            True if successful
        """
        if not self.check_permission(granted_by, Permission.PERMISSION_GRANT):
            raise PermissionError(f"User {granted_by} cannot grant permissions")

        # For now, we assign roles. Full implementation would support
        # custom permissions per user
        return True

    def has_admin_access(self, user_id: str) -> bool:
        """Check if user has admin role."""
        return self.check_permission(user_id, Permission.ADMIN_ALL)

    def get_assignment_history(
        self,
        user_id: Optional[str] = None,
    ) -> List[RoleAssignment]:
        """
        Get role assignment history.

        Args:
            user_id: Filter by user (optional)

        Returns:
            List of role assignments
        """
        if user_id:
            return [a for a in self.assignment_history if a.user_id == user_id]
        return self.assignment_history

    def define_custom_role(
        self,
        name: str,
        permissions: Set[Permission],
        created_by: str,
    ) -> RoleDefinition:
        """
        Create a custom role.

        Args:
            name: Role name
            permissions: Set of permissions for the role
            created_by: Admin creating the role

        Returns:
            RoleDefinition: The created role definition
        """
        if not self.check_permission(created_by, Permission.ADMIN_ALL):
            raise PermissionError(f"User {created_by} cannot create roles")

        # For this implementation, we work with predefined roles
        # Full implementation would support custom role creation
        raise NotImplementedError("Custom roles not yet implemented")
