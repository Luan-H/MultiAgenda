from django.db import models
from servico.models import Servico
from cliente.models import Cliente

class Agendamento(models.Model):
    id_agendamento = models.AutoField(primary_key=True)
    status = models.CharField(max_length=1)
    id_servico = models.ForeignKey(Servico, on_delete=models.CASCADE, db_column='id_servico')
    id_cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, db_column='id_cliente')

    class Meta:
        db_table = 'agendamento'