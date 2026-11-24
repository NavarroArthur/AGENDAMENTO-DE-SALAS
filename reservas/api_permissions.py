from rest_framework.permissions import BasePermission, SAFE_METHODS

from core.models import Perfil


def tem_perfil_organizacional(usuario):
    return bool(
        usuario.is_authenticated
        and getattr(usuario, 'perfil', None) is not None
    )


class PerfilOrganizacionalRequired(BasePermission):
    def has_permission(self, request, view):
        return tem_perfil_organizacional(request.user)


class AdminParaEscrita(BasePermission):
    """Leitura para os membros da organização; escrita só para administradores."""

    def has_permission(self, request, view):
        if not tem_perfil_organizacional(request.user):
            return False
        return request.method in SAFE_METHODS or request.user.perfil.papel == Perfil.ADMIN


class DonoOuAdminDaOrganizacao(BasePermission):
    def has_permission(self, request, view):
        return tem_perfil_organizacional(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return (
            request.user.perfil.papel == Perfil.ADMIN
            or obj.criado_por_id == request.user.pk
        )
