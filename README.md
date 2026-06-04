# MultiAgenda

Sistema de agendamento e gerenciamento corporativo desenvolvido na faculdade para as matérias de Programação de Banco de Dados e Programação Web Back-End.

O projeto utiliza uma arquitetura híbrida no back-end, mesclando o framework Django com consultas SQL puras.

## Tecnologias Utilizadas

* **Back-end:** Python, Django
* **Banco de Dados:** PostgreSQL
* **Front-end:** HTML5, CSS3 e Bootstrap 5
* **Segurança:** Hashes de senha do Django (make_password) e controle de sessão por perfil.

## Funcionalidades Principais

* **Gestão de Usuários:** Controle de acesso hierárquico com perfis de Administrador e Secretário.
* **Gestão de Profissionais:** Cadastro de equipe com exclusão lógica (soft delete) para preservação de integridade referencial do histórico de agendamentos.
* **Motor Dinâmico de Agenda:** Geração automatizada de slots de tempo (blocos de 30 minutos) no banco de dados para os próximos 30 dias, baseada na rotina semanal configurada individualmente para cada profissional.
* **Gestão de Clientes:** Cadastro otimizado de clientes, incluindo controle de credenciais (login/senha criptografada) e campo para observações internas.
* **Interface Responsiva:** Modais independentes e validação em tempo real utilizando JavaScript e componentes do Bootstrap.