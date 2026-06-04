from django.db import models
from empresa.models import Empresa

class Profissional(models.Model):
    id_profissional = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    ativo = models.CharField(max_length=1, default='1')
    id_empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, db_column='id_empresa')

    class Meta:
        db_table = 'profissional'