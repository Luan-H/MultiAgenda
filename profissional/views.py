# ==========================================================
# IMPORTAÇÃO DAS BIBLIOTECAS
# ==========================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.contrib.auth.hashers import check_password, make_password
import datetime
from datetime import timedelta, datetime as dt_calc

# ==========================================================
# VALIDAÇÃO DE UNICIDADE DE LOGIN
# ==========================================================
def login_ja_existe(login_digitado):
    with connection.cursor() as cursor:
        query = """
            SELECT 1 FROM cliente WHERE login = %s
            UNION
            SELECT 1 FROM profissional WHERE login = %s
            UNION
            SELECT 1 FROM usuario WHERE login = %s
        """
        cursor.execute(query, [login_digitado, login_digitado, login_digitado])
        resultado = cursor.fetchone()
        return resultado is not None

# ==========================================================
# VIEW DE GERENCIAMENTO DE PROFISSIONAIS
# ==========================================================
def gerenciar_profissionais_view(request, id_edit=None):

    # Recupera os dados do usuário logado
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")

    # Permite acesso apenas para administradores e secretários
    if not login_sessao or perfil_sessao not in ["admin", "secretario"]:
        return redirect("login")

    profissional_para_editar = None
    
    # Variável para armazenar erro de login duplicado
    erro_login = None

    # Data atual utilizada em consultas da agenda
    hoje = datetime.date.today()

    # ==========================================================
    # CARREGAMENTO DOS DADOS PARA EDIÇÃO
    # ==========================================================
    if id_edit:

        with connection.cursor() as cursor:

            # Busca os dados do profissional selecionado
            cursor.execute(
                """
                SELECT id_profissional, nome, email, telefone, login
                FROM profissional
                WHERE id_profissional = %s
            """,
                [id_edit],
            )

            row = cursor.fetchone()

            # Monta o objeto utilizado para preencher o formulário
            if row:
                profissional_para_editar = {
                    "id": row[0],
                    "nome": row[1],
                    "email": row[2],
                    "telefone": row[3],
                    "login": row[4],
                }

    # ==========================================================
    # CADASTRO E EDIÇÃO DE PROFISSIONAIS
    # ==========================================================
    if request.method == "POST":

        # Recupera os dados enviados pelo formulário
        nome = request.POST.get("nome")
        email = request.POST.get("email")
        telefone = request.POST.get("telefone")
        login_prof = request.POST.get("login")
        senha_crua = request.POST.get("senha")

        with connection.cursor() as cursor:

            # ==========================================================
            # EDIÇÃO DE PROFISSIONAL EXISTENTE
            # ==========================================================
            if id_edit:

                # Atualiza a senha apenas se uma nova foi informada
                if senha_crua:

                    senha_hash = make_password(senha_crua)

                    cursor.execute(
                        """
                        UPDATE profissional
                        SET nome=%s,
                            email=%s,
                            telefone=%s,
                            login=%s,
                            senha=%s
                        WHERE id_profissional=%s
                    """,
                        [nome, email, telefone, login_prof, senha_hash, id_edit],
                    )

                else:

                    cursor.execute(
                        """
                        UPDATE profissional
                        SET nome=%s,
                            email=%s,
                            telefone=%s,
                            login=%s
                        WHERE id_profissional=%s
                    """,
                        [nome, email, telefone, login_prof, id_edit],
                    )

            # ==========================================================
            # CADASTRO DE NOVO PROFISSIONAL
            # ==========================================================
            else:
                # Validação preventiva para impedir credenciais duplicadas no sistema
                if login_ja_existe(login_prof):
                    erro_login = "Este login ja esta sendo usado por outra pessoa."
                else:
                    # Criptografa a senha antes de salvar
                    senha_hash = make_password(senha_crua) if senha_crua else ""
    
                    # Obtém a empresa do usuário logado
                    cursor.execute(
                        "SELECT id_empresa FROM usuario WHERE login = %s", [login_sessao]
                    )
    
                    id_empresa = cursor.fetchone()[0]
    
                    # Cadastra o profissional vinculado à empresa
                    cursor.execute(
                        """
                        INSERT INTO profissional (
                            nome,
                            email,
                            telefone,
                            login,
                            senha,
                            ativo,
                            id_empresa
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            '1',
                            %s
                        )
                    """,
                        [nome, email, telefone, login_prof, senha_hash, id_empresa],
                    )

        # Se não houve erro de duplicidade de login, retorna para a listagem limpa
        if not erro_login:
            return redirect("gerenciar_profissionais")

    # ==========================================================
    # FILTRO DE PESQUISA
    # ==========================================================
    termo_busca = request.GET.get("q", "")

    with connection.cursor() as cursor:

        # ==========================================================
        # CONSULTA DA LISTA DE PROFISSIONAIS
        # ==========================================================
        if termo_busca:

            query_list = """
                SELECT p.id_profissional AS id,
                       p.nome,
                       p.email,
                       p.telefone,
                       EXISTS(
                           SELECT 1
                           FROM agenda a
                           WHERE a.id_profissional = p.id_profissional
                           AND a.dt_agenda >= %s
                       ) as tem_agenda
                FROM profissional p
                WHERE p.id_empresa = (
                    SELECT id_empresa
                    FROM usuario
                    WHERE login = %s
                )
                AND p.ativo = '1'
                AND (
                    p.nome ILIKE %s
                    OR p.email ILIKE %s
                    OR p.telefone ILIKE %s
                )
                ORDER BY p.nome
            """

            param_busca = f"%{termo_busca}%"

            cursor.execute(
                query_list, [hoje, login_sessao, param_busca, param_busca, param_busca]
            )

        else:

            query_list = """
                SELECT p.id_profissional AS id,
                       p.nome,
                       p.email,
                       p.telefone,
                       EXISTS(
                           SELECT 1
                           FROM agenda a
                           WHERE a.id_profissional = p.id_profissional
                           AND a.dt_agenda >= %s
                       ) as tem_agenda
                FROM profissional p
                WHERE p.id_empresa = (
                    SELECT id_empresa
                    FROM usuario
                    WHERE login = %s
                )
                AND p.ativo = '1'
                ORDER BY p.nome
            """

            cursor.execute(query_list, [hoje, login_sessao])

        # Converte os resultados para uma lista de dicionários
        colunas = [col[0] for col in cursor.description]
        profissionais_lista = [dict(zip(colunas, row)) for row in cursor.fetchall()]

        # Relaciona os números dos dias da semana aos seus nomes
        mapa_dias = {
            1: "segunda",
            2: "terca",
            3: "quarta",
            4: "quinta",
            5: "sexta",
            6: "sabado",
            7: "domingo",
        }

        # ==========================================================
        # CARREGAMENTO DAS CONFIGURAÇÕES DE AGENDA
        # ==========================================================
        for prof in profissionais_lista:

            # Configuração padrão da agenda
            config = {
                "segunda": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
                "terca": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
                "quarta": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
                "quinta": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
                "sexta": {"ativo": True, "inicio": "08:00", "fim": "18:00"},
                "sabado": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
                "domingo": {"ativo": False, "inicio": "08:00", "fim": "12:00"},
            }

            # Se já possuir agenda cadastrada, desativa o padrão
            if prof["tem_agenda"]:
                for dia in config:
                    config[dia]["ativo"] = False

            # Busca os horários cadastrados para cada dia da semana
            cursor.execute(
                """
                SELECT
                    EXTRACT(ISODOW FROM dt_agenda) as dia_semana,
                    MIN(hr_agenda) as inicio,
                    MAX(hr_agenda) as fim
                FROM agenda
                WHERE id_profissional = %s
                AND dt_agenda >= %s
                GROUP BY EXTRACT(ISODOW FROM dt_agenda)
            """,
                [prof["id"], hoje],
            )

            for row in cursor.fetchall():

                dia_num = int(row[0])
                dia_nome = mapa_dias.get(dia_num)

                if dia_nome:

                    hr_ini = row[1]
                    hr_fim = row[2]

                    str_ini = (
                        hr_ini.strftime("%H:%M")
                        if hasattr(hr_ini, "strftime")
                        else str(hr_ini)[:5]
                    )

                    # Soma 30 minutos ao último horário encontrado
                    if hr_fim:

                        if hasattr(hr_fim, "hour"):

                            dt_temp = datetime.datetime.combine(
                                datetime.date.today(), hr_fim
                            ) + datetime.timedelta(minutes=30)

                            str_fim = dt_temp.strftime("%H:%M")

                        else:

                            t = datetime.datetime.strptime(
                                str(hr_fim)[:5], "%H:%M"
                            ) + datetime.timedelta(minutes=30)

                            str_fim = t.strftime("%H:%M")

                    else:
                        str_fim = "18:00"

                    config[dia_nome] = {
                        "ativo": True,
                        "inicio": str_ini,
                        "fim": str_fim,
                    }

            # Adiciona a configuração ao profissional
            prof["agenda_config"] = config

    # ==========================================================
    # DADOS ENVIADOS PARA O TEMPLATE
    # ==========================================================
    contexto = {
        "perfil": perfil_sessao,
        "profissionais": profissionais_lista,
        "profissional_edit": profissional_para_editar,
        "termo_busca": termo_busca,
    }
    
    # Adiciona o erro ao contexto apenas se ele existir
    if erro_login:
        contexto["erro_login"] = erro_login

    return render(request, "profissional/profissional.html", contexto)


# ==========================================================
# SALVAMENTO DA AGENDA DO PROFISSIONAL
# ==========================================================
def salvar_agenda_profissional_view(request, id_profissional):

    # ==========================================================
    # VALIDAÇÃO DA SESSÃO E SEGURANÇA
    # ==========================================================
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")

    # Impede acessos diretos por URL de usuários não autorizados
    if not login_sessao or perfil_sessao not in ["admin", "secretario"]:
        return redirect("gerenciar_profissionais")

    if request.method == "POST":

        # Relaciona os nomes dos dias ao índice utilizado pelo Python
        dias_mapeamento = {
            "segunda": 0,
            "terca": 1,
            "quarta": 2,
            "quinta": 3,
            "sexta": 4,
            "sabado": 5,
            "domingo": 6,
        }

        hoje = datetime.date.today()

        with connection.cursor() as cursor:

            # Remove horários futuros que ainda não possuem agendamento
            cursor.execute(
                """
                DELETE FROM agenda
                WHERE id_profissional = %s
                AND id_agendamento IS NULL
                AND dt_agenda >= %s
            """,
                [id_profissional, hoje],
            )

            # Gera a agenda para os próximos 30 dias
            for i in range(30):

                data_alvo = hoje + timedelta(days=i)

                dia_semana_nome = list(dias_mapeamento.keys())[data_alvo.weekday()]

                is_ativo = request.POST.get(f"{dia_semana_nome}_ativo")

                if is_ativo:

                    hr_inicio_str = request.POST.get(f"{dia_semana_nome}_inicio")

                    hr_fim_str = request.POST.get(f"{dia_semana_nome}_fim")

                    if hr_inicio_str:
                        hr_inicio_str = hr_inicio_str[:5]

                    if hr_fim_str:
                        hr_fim_str = hr_fim_str[:5]

                    atual = dt_calc.strptime(hr_inicio_str, "%H:%M")

                    fim = dt_calc.strptime(hr_fim_str, "%H:%M")

                    # Cria horários de 30 em 30 minutos
                    while atual < fim:

                        cursor.execute(
                            """
                            INSERT INTO agenda (
                                dt_agenda,
                                hr_agenda,
                                id_profissional
                            )
                            VALUES (%s, %s, %s)
                        """,
                            [data_alvo, atual.strftime("%H:%M"), id_profissional],
                        )

                        atual += timedelta(minutes=30)

        return redirect("gerenciar_profissionais")

    return redirect("gerenciar_profissionais")


# ==========================================================
# EXCLUSÃO LÓGICA DE PROFISSIONAIS
# ==========================================================
def excluir_profissional_view(request, id_profissional):

    # Permite exclusão apenas para administradores e secretários
    if request.session.get("usuario_perfil") not in ["admin", "secretario"]:
        return redirect("dashboard_admin")

    with connection.cursor() as cursor:

        # Desativa o profissional sem removê-lo do banco
        cursor.execute(
            """
            UPDATE profissional
            SET ativo = '0'
            WHERE id_profissional = %s
        """,
            [id_profissional],
        )

    return redirect("gerenciar_profissionais")