from rest_framework.permissions import BasePermission
from orgs.models import Organization
from users.models import UserProfile


class HasOwnership(BasePermission):
    """
    The request is authenticated, and the user is a member of the referenced organization
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if request.user.is_authenticated and hasattr(request.user, 'get_profile'):
            userprofile = request.user.get_profile()
            if isinstance(obj, UserProfile):
                return obj == userprofile
            elif isinstance(obj, Organization):
                return userprofile.id in obj.members
            return True
        return False


class HasPrivateAccess(BasePermission):
    """
    Current user is authenticated as a staff user, or is designated as the referenced object's owner,
    or belongs to an organization that is designated as the referenced object's owner.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        if request.user == obj.owner:
            return True
        if request.user.is_authenticated and hasattr(request.user, 'get_profile'):
            profile = request.user.get_profile()
            if obj.parent_id in profile.organizations:
                return True
        return False


class HasAccessToVersionedObject(BasePermission):
    """
    Current user is authenticated as a staff user, or is designated as the owner of the object
    that is versioned by the referenced object, or is a member of an organization
    that is designated as the owner of the object that is versioned by the referenced object.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        versioned_object = obj.versioned_object
        if request.user == versioned_object.owner:
            return True
        if request.user.is_authenticated and hasattr(request.user, 'get_profile'):
            profile = request.user.get_profile()
            if versioned_object.parent_id in profile.organizations:
                return True
        return False