from django.contrib import admin
from django.urls import path
from usuario.views import (
    login_view, 
    dashboard_admin_view, 
    gerenciar_usuarios_view, 
    excluir_usuario_view
)

from profissional.views import (
    gerenciar_profissionais_view, 
    excluir_profissional_view,
    salvar_agenda_profissional_view
)

from cliente.views import gerenciar_clientes_view, excluir_cliente_view

from agendamento.views import gerenciar_agendamentos_view, salvar_agendamento_view

from servico.views import gerenciar_servicos_view, excluir_servico_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),
    path('dashboard/', dashboard_admin_view, name='dashboard_admin'),
    path('usuarios/', gerenciar_usuarios_view, name='gerenciar_usuarios'),
    path('usuarios/editar/<str:login_edit>/', gerenciar_usuarios_view, name='preparar_edicao'),
    path('usuarios/excluir/<str:login_usuario>/', excluir_usuario_view, name='excluir_usuario'),
    path('profissionais/', gerenciar_profissionais_view, name='gerenciar_profissionais'),
    path('profissionais/editar/<int:id_edit>/', gerenciar_profissionais_view, name='preparar_edicao_profissional'),
    path('profissionais/excluir/<int:id_profissional>/', excluir_profissional_view, name='excluir_profissional'),
    path('profissionais/salvar-agenda/<int:id_profissional>/', salvar_agenda_profissional_view, name='salvar_agenda_profissional'),
    path('clientes/', gerenciar_clientes_view, name='gerenciar_clientes'),
    path('clientes/editar/<int:id_edit>/', gerenciar_clientes_view, name='preparar_edicao_cliente'),
    path('clientes/excluir/<int:id_cliente>/', excluir_cliente_view, name='excluir_cliente'),
    path('agendamentos/', gerenciar_agendamentos_view, name='gerenciar_agendamentos'),
    path('agendamentos/salvar/', salvar_agendamento_view, name='salvar_agendamento'),
    path('servicos/', gerenciar_servicos_view, name='gerenciar_servicos'),
    path('servicos/editar/<int:id_edit>/', gerenciar_servicos_view, name='preparar_edicao_servico'),
    path('servicos/excluir/<int:id_servico>/', excluir_servico_view, name='excluir_servico'),
]