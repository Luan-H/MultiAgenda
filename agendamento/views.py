# ==========================================================
# IMPORTAÇÃO DAS BIBLIOTECAS
# ==========================================================

import datetime
from datetime import timedelta
from django.shortcuts import render, redirect
from django.db import connection

# ==========================================================
# VIEW 1: EXIBIÇÃO E GERENCIAMENTO DA AGENDA
# ==========================================================
def gerenciar_agendamentos_view(request):
    # Recupera os dados do usuário logado
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")

    # Valida se existe uma sessão ativa e um perfil autorizado
    if not login_sessao:
        return redirect("login")

    if perfil_sessao not in ["admin", "secretario", "profissional", "cliente"]:
        return redirect("login")

    # ==========================================================
    # IDENTIFICAÇÃO DA EMPRESA DO USUÁRIO
    # ==========================================================
    with connection.cursor() as cursor:
        # Busca a empresa vinculada ao login, independente do tipo de usuário
        cursor.execute(
            """
            SELECT id_empresa FROM usuario WHERE login = %s
            UNION
            SELECT id_empresa FROM profissional WHERE login = %s
            UNION
            SELECT id_empresa FROM cliente WHERE login = %s
        """,
            [login_sessao, login_sessao, login_sessao],
        )
        row_empresa = cursor.fetchone()

        if not row_empresa:
            return redirect("login")

        id_empresa = row_empresa[0]

    # ==========================================================
    # CONTROLE DA DATA EXIBIDA NA AGENDA
    # ==========================================================
    data_str = request.GET.get("data")

    try:
        data_atual = (
            datetime.datetime.strptime(data_str, "%Y-%m-%d").date()
            if data_str
            else datetime.date.today()
        )
    except ValueError:
        data_atual = datetime.date.today()

    data_anterior = data_atual - timedelta(days=1)
    data_proxima = data_atual + timedelta(days=1)

    # Formatação amigável da data para exibição na tela
    meses = [
        "",
        "Jan",
        "Fev",
        "Mar",
        "Abr",
        "Mai",
        "Jun",
        "Jul",
        "Ago",
        "Set",
        "Out",
        "Nov",
        "Dez",
    ]
    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    data_atual_formatada = (
        f"{dias_semana[data_atual.weekday()]}, "
        f"{data_atual.day:02d} "
        f"{meses[data_atual.month]} "
        f"{data_atual.year}"
    )

    with connection.cursor() as cursor:
        # ==========================================================
        # CARREGAMENTO DOS DADOS NECESSÁRIOS PARA A TELA
        # ==========================================================
        
        # Cliente visualiza apenas seus próprios dados
        if perfil_sessao == "cliente":
            cursor.execute(
                "SELECT id_cliente, nome FROM cliente WHERE login = %s AND ativo = '1'",
                [login_sessao],
            )
        else:
            cursor.execute(
                "SELECT id_cliente, nome FROM cliente WHERE id_empresa = %s AND ativo = '1' ORDER BY nome",
                [id_empresa],
            )
        clientes_lista = [{"id": row[0], "nome": row[1]} for row in cursor.fetchall()]
        
        # Lista de profissionais disponíveis
        cursor.execute(
            """
            SELECT id_profissional, nome
            FROM profissional
            WHERE id_empresa = %s
            AND ativo = '1'
            ORDER BY nome
        """,
            [id_empresa],
        )
        profissionais_lista = [
            {"id": row[0], "nome": row[1]} for row in cursor.fetchall()
        ]

        # Lista de serviços disponíveis para agendamento
        cursor.execute(
            """
            SELECT id_servico, nome, duracao_em_min
            FROM servico
            WHERE id_empresa = %s
            AND ativo = '1'
            ORDER BY nome
        """,
            [id_empresa],
        )
        servicos_lista = [
            {"id": row[0], "nome": row[1], "duracao_minutos": row[2]}
            for row in cursor.fetchall()
        ]

        # ==========================================================
        # CONSULTA DOS HORÁRIOS DA AGENDA
        # ==========================================================
        query_agenda = """
            SELECT 
                a.hr_agenda,
                a.id_profissional,
                a.id_agendamento,
                c.nome as cliente_nome,
                s.nome as servico_nome,
                s.duracao_em_min as servico_duracao
            FROM agenda a
            JOIN profissional p ON a.id_profissional = p.id_profissional
            LEFT JOIN agendamento ag ON a.id_agendamento = ag.id_agendamento
            LEFT JOIN cliente c ON ag.id_cliente = c.id_cliente
            LEFT JOIN servico s ON ag.id_servico = s.id_servico
            WHERE a.dt_agenda = %s
            AND p.id_empresa = %s
            AND p.ativo = '1'
        """
        cursor.execute(query_agenda, [data_atual, id_empresa])

        # Organiza os horários em um dicionário para facilitar consultas
        slots_dict = {}

        for row in cursor.fetchall():
            hr_str = (
                row[0].strftime("%H:%M")
                if hasattr(row[0], "strftime")
                else str(row[0])[:5]
            )

            slots_dict[(hr_str, row[1])] = {
                "id_agendamento": row[2],
                "cliente_nome": row[3],
                "servico_nome": row[4],
                "servico_duracao": row[5],
            }
        # Recupera os horários disponíveis do dia
        cursor.execute(
            """
            SELECT DISTINCT a.hr_agenda
            FROM agenda a
            JOIN profissional p ON a.id_profissional = p.id_profissional
            WHERE a.dt_agenda = %s
            AND p.id_empresa = %s
            AND p.ativo = '1'
            ORDER BY a.hr_agenda
        """,
            [data_atual, id_empresa],
        )
        linhas_horarios = cursor.fetchall()

        # Caso não existam horários cadastrados, gera uma grade padrão
        if linhas_horarios:
            horarios = [
                (
                    row[0].strftime("%H:%M")
                    if hasattr(row[0], "strftime")
                    else str(row[0])[:5]
                )
                for row in linhas_horarios
            ]
        else:
            horarios = [f"{h:02d}:{m:02d}" for h in range(8, 19) for m in (0, 30)]

            if horarios[-1] == "18:30":
                horarios.pop()

    # ==========================================================
    # MONTAGEM DA GRADE VISUAL DE HORÁRIOS
    # ==========================================================
    grade_horarios = []

    # Controla quantas linhas devem ser ignoradas em serviços longos
    skip_dict = {prof["id"]: 0 for prof in profissionais_lista}

    for hr in horarios:
        linha = {"hora": hr, "celulas": []}
        for prof in profissionais_lista:
            prof_id = prof["id"]
            if skip_dict[prof_id] > 0:
                linha["celulas"].append({"tipo": "ignorar"})
                skip_dict[prof_id] -= 1
                continue
            
            slot = slots_dict.get((hr, prof_id))
            # Horário indisponível
            if not slot:
                linha["celulas"].append({"tipo": "indisponivel"})
            # Horário disponível
            elif not slot["id_agendamento"]:
                linha["celulas"].append({"tipo": "vazio"})
            # Horário ocupado por um agendamento
            else:
                duracao = slot["servico_duracao"] or 30
                rowspan = max(1, int(duracao) // 30)

                linha["celulas"].append(
                    {
                        "tipo": "evento",
                        "rowspan": rowspan,
                        "cliente_nome": slot["cliente_nome"],
                        "servico_nome": slot["servico_nome"],
                    }
                )
                skip_dict[prof_id] = rowspan - 1
        grade_horarios.append(linha)
        
    # Dados enviados para o template HTML
    contexto = {
        "perfil": perfil_sessao,
        "data_atual_iso": data_atual.strftime("%Y-%m-%d"),
        "data_atual_formatada": data_atual_formatada,
        "data_anterior": data_anterior.strftime("%Y-%m-%d"),
        "data_proxima": data_proxima.strftime("%Y-%m-%d"),
        "profissionais": profissionais_lista,
        "clientes_lista": clientes_lista,
        "servicos_lista": servicos_lista,
        "grade_horarios": grade_horarios,
    }

    return render(request, "agendamento/agendamentos.html", contexto)


# ==========================================================
# VIEW 2: SALVAMENTO DE NOVOS AGENDAMENTOS
# ==========================================================
def salvar_agendamento_view(request):
    # Executa apenas quando o formulário é enviado
    if request.method == "POST":
        
        # ==========================================================
        # VALIDAÇÃO DA SESSÃO E SEGURANÇA
        # ==========================================================
        login_sessao = request.session.get("usuario_login")
        perfil_sessao = request.session.get("usuario_perfil")
        
        # Trava: expulsa requisições sem autenticação
        if not login_sessao:
            return redirect("login")

        # Recupera os dados informados no formulário
        id_profissional = request.POST.get("id_profissional")
        id_servico = request.POST.get("id_servico")
        data_agenda = request.POST.get("data_agenda")
        hora_agenda = request.POST.get("hora_agenda")

        # ==========================================================
        # IDENTIFICAÇÃO DO CLIENTE E REGRAS DE NEGÓCIO
        # ==========================================================
        with connection.cursor() as cursor:
            # Clientes utilizam o próprio cadastro
            if perfil_sessao == "cliente":
                cursor.execute(
                    "SELECT id_cliente FROM cliente WHERE login = %s", [login_sessao]
                )
                id_cliente = cursor.fetchone()[0]
            # Funcionários escolhem o cliente pelo formulário
            else:
                id_cliente = request.POST.get("id_cliente")
                
            if hora_agenda:
                hora_agenda = hora_agenda[:5]
                
            # ==========================================================
            # VALIDAÇÃO DOS HORÁRIOS DISPONÍVEIS
            # ==========================================================
            cursor.execute(
                "SELECT duracao_em_min FROM servico WHERE id_servico = %s", [id_servico]
            )
            resultado_duracao = cursor.fetchone()

            if not resultado_duracao:
                return redirect("gerenciar_agendamentos")

            # Calcula quantos blocos de 30 minutos serão necessários
            duracao = int(resultado_duracao[0])
            blocos_necessarios = max(1, duracao // 30)

            query_busca = """
                SELECT id_agenda, id_agendamento
                FROM agenda
                WHERE dt_agenda = %s
                AND id_profissional = %s
                AND hr_agenda >= %s
                ORDER BY hr_agenda ASC
                LIMIT %s
            """

            cursor.execute(
                query_busca,
                [data_agenda, id_profissional, hora_agenda, blocos_necessarios],
            )
            slots = cursor.fetchall()

            # Verifica se todos os horários necessários estão livres
            if len(slots) == blocos_necessarios and all(slot[1] is None for slot in slots):
                # Cria o registro do agendamento
                cursor.execute(
                    """
                    INSERT INTO agendamento (status, id_servico, id_cliente)
                    VALUES ('A', %s, %s)
                    RETURNING id_agendamento
                """,
                    [id_servico, id_cliente],
                )
                novo_id_agendamento = cursor.fetchone()[0]
                
                # Vincula o agendamento aos horários reservados
                ids_agenda = tuple(slot[0] for slot in slots)

                cursor.execute(
                    """
                    UPDATE agenda
                    SET id_agendamento = %s
                    WHERE id_agenda IN %s
                """,
                    [novo_id_agendamento, ids_agenda],
                )
            else:
                print(
                    f"ATTENCAO: Tentativa falhou. "
                    f"Precisava de {blocos_necessarios} blocos livres."
                )

        return redirect("gerenciar_agendamentos")

    return redirect("dashboard_admin")