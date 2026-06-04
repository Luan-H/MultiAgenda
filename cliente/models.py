from django.db import models
from empresa.models import Empresa

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    login = models.CharField(max_length=100, unique=True)
    senha = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)
    observacoes = models.CharField(max_length=100, null=True, blank=True)
    ativo = models.CharField(max_length=1, default='1')
    id_empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, db_column='id_empresa')

    class Meta:
        db_table = 'cliente'