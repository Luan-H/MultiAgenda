from django.db import models
from profissional.models import Profissional
from agendamento.models import Agendamento

class Agenda(models.Model):
    id_agenda = models.AutoField(primary_key=True)
    dt_agenda = models.DateField()
    hr_agenda = models.TimeField()
    id_profissional = models.ForeignKey(Profissional, on_delete=models.CASCADE, db_column='id_profissional')
    id_agendamento = models.ForeignKey(Agendamento, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_agendamento')

    class Meta:
        db_table = 'agenda'