from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import Perfil


def perfil_required(view_func):
    """Exige login e perfil; superusuário sem perfil fica no Admin do Django."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        try:
            perfil = request.user.perfil
        except Perfil.DoesNotExist:
            if request.user.is_superuser:
                messages.info(
                    request,
                    'Crie um perfil e associe sua conta a uma organização para usar o sistema.',
                )
                return redirect('admin:index')
            raise PermissionDenied('Sua conta ainda não está associada a uma organização.')

        request.perfil = perfil
        request.organizacao = perfil.organizacao
        return view_func(request, *args, **kwargs)

    return _wrapped


def papel_required(*papeis):
    def decorator(view_func):
        @wraps(view_func)
        @perfil_required
        def _wrapped(request, *args, **kwargs):
            if request.perfil.papel not in papeis:
                raise PermissionDenied('Seu perfil não pode executar esta ação.')
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


admin_required = papel_required(Perfil.ADMIN)
