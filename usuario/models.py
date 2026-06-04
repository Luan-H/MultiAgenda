from django.db import models
from empresa.models import Empresa
from profissional.models import Profissional

class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    login = models.CharField(max_length=100, unique=True)
    senha = models.CharField(max_length=100)
    cargo = models.CharField(max_length=100)
    ativo = models.CharField(max_length=1, default='1')
    id_empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, db_column='id_empresa')
    id_profissional = models.ForeignKey(Profissional, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_profissional')

    class Meta:
        db_table = 'usuario'