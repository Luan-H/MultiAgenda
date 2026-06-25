# ==========================================================
# IMPORTAÇÃO DAS BIBLIOTECAS
# ==========================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.contrib.auth.hashers import check_password, make_password
import datetime

# ==========================================================
# BUSCA DE USUÁRIO PARA AUTENTICAÇÃO
# ==========================================================
def buscar_usuario_para_login(login_digitado):
    with connection.cursor() as cursor:
        # Procura o login nas tabelas de clientes,
        # profissionais e usuários administrativos
        query = """
            SELECT login, senha, 'cliente' AS perfil
            FROM cliente
            WHERE login = %s AND ativo = '1'

            UNION

            SELECT login, senha, 'profissional' AS perfil
            FROM profissional
            WHERE login = %s AND ativo = '1'

            UNION

            SELECT login, senha, cargo AS perfil
            FROM usuario
            WHERE login = %s AND ativo = '1';
        """
        cursor.execute(query, [login_digitado, login_digitado, login_digitado])
        return cursor.fetchone()
    
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
# TELA DE LOGIN
# ==========================================================
def login_view(request):
    contexto = {}
    if request.method == "POST":
        login_form = request.POST.get("login")
        senha_form = request.POST.get("senha")
        
        dados_usuario = buscar_usuario_para_login(login_form)
        if dados_usuario:
            login_db, senha_db, perfil = dados_usuario
            if check_password(senha_form, senha_db):
                request.session["usuario_login"] = login_db
                request.session["usuario_perfil"] = perfil
                
                if perfil == "cliente":
                    return redirect("agenda_cliente")
                elif perfil == "profissional":
                    return redirect("gerenciar_agendamentos")
                else:
                    return redirect("dashboard_admin")
            else:
                contexto["erro"] = "Senha incorreta."
        else:
            contexto["erro"] = "Usuario nao encontrado."

    return render(request, "login.html", contexto)


# ==========================================================
# BUSCA O NOME DO USUÁRIO LOGADO
# ==========================================================
def buscar_nome_pelo_login(login):
    with connection.cursor() as cursor:
        query = """
            SELECT nome FROM cliente WHERE login = %s
            UNION
            SELECT nome FROM profissional WHERE login = %s
            UNION
            SELECT nome FROM usuario WHERE login = %s;
        """
        cursor.execute(query, [login, login, login])
        resultado = cursor.fetchone()
        return resultado[0] if resultado else "Utilizador"


# ==========================================================
# DASHBOARD ADMINISTRATIVO
# ==========================================================
def dashboard_admin_view(request):
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")
    
    if not login_sessao or (perfil_sessao != "admin" and perfil_sessao != "secretario"):
        return redirect("login")

    nome = buscar_nome_pelo_login(login_sessao)

    indicadores = {
        "total_clientes": 0,
        "total_profissionais": 0,
        "agendamentos_hoje": 0,
        "servicos_ativos": 0,
    }
    hoje = datetime.date.today()

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id_empresa FROM usuario WHERE login = %s", [login_sessao]
        )
        row_empresa = cursor.fetchone()

        if row_empresa:
            id_empresa = row_empresa[0]
            
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM cliente
                WHERE id_empresa = %s
                AND ativo = '1'
            """,
                [id_empresa],
            )
            indicadores["total_clientes"] = cursor.fetchone()[0]
            
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM profissional
                WHERE id_empresa = %s
                AND ativo = '1'
            """,
                [id_empresa],
            )
            indicadores["total_profissionais"] = cursor.fetchone()[0]
            
            cursor.execute(
                """
                SELECT COUNT(DISTINCT a.id_agendamento)
                FROM agenda a
                JOIN profissional p
                    ON a.id_profissional = p.id_profissional
                WHERE p.id_empresa = %s
                AND a.dt_agenda = %s
                AND a.id_agendamento IS NOT NULL
            """,
                [id_empresa, hoje],
            )
            indicadores["agendamentos_hoje"] = cursor.fetchone()[0]
            
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM servico
                WHERE id_empresa = %s
                AND ativo = '1'
            """,
                [id_empresa],
            )
            indicadores["servicos_ativos"] = cursor.fetchone()[0]
            
            cursor.execute(
                """
                SELECT
                    MIN(a.hr_agenda) as hora,
                    c.nome as cliente_nome,
                    p.nome as profissional_nome,
                    s.nome as servico_nome
                FROM agenda a
                JOIN agendamento ag
                    ON a.id_agendamento = ag.id_agendamento
                JOIN cliente c
                    ON ag.id_cliente = c.id_cliente
                JOIN profissional p
                    ON a.id_profissional = p.id_profissional
                JOIN servico s
                    ON ag.id_servico = s.id_servico
                WHERE p.id_empresa = %s
                AND a.dt_agenda = %s
                AND a.id_agendamento IS NOT NULL
                GROUP BY
                    a.id_agendamento,
                    c.nome,
                    p.nome,
                    s.nome
                ORDER BY hora ASC
                LIMIT 10
            """,
                [id_empresa, hoje],
            )
            proximos_agendamentos = []
            
            for row in cursor.fetchall():
                hora_formatada = (
                    row[0].strftime("%H:%M")
                    if hasattr(row[0], "strftime")
                    else str(row[0])[:5]
                )
                proximos_agendamentos.append(
                    {
                        "hora": hora_formatada,
                        "cliente_nome": row[1],
                        "profissional_nome": row[2],
                        "servico_nome": row[3],
                    }
                )
        else:
            proximos_agendamentos = []

    contexto = {
        "nome_usuario": nome,
        "perfil": perfil_sessao,
        "indicadores": indicadores,
        "proximos_agendamentos": proximos_agendamentos,
    }

    return render(request, "dashboard/dashboard.html", contexto)


# ==========================================================
# GERENCIAMENTO DE USUÁRIOS
# ==========================================================
def gerenciar_usuarios_view(request, login_edit=None):
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")

    if not login_sessao or perfil_sessao != "admin":
        return redirect("login")

    usuario_para_editar = None
    contexto = {}
    erro_login = None

    if login_edit:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT nome, login, cargo
                FROM usuario
                WHERE login = %s
            """,
                [login_edit],
            )
            row = cursor.fetchone()
            if row:
                usuario_para_editar = {"nome": row[0], "login": row[1], "cargo": row[2]}

    if request.method == "POST":
        nome = request.POST.get("nome")
        cargo = request.POST.get("cargo")
        
        if login_edit:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE usuario
                    SET nome=%s, cargo=%s
                    WHERE login=%s
                """,
                    [nome, cargo, login_edit],
                )
            return redirect("gerenciar_usuarios")
        else:
            login_novo = request.POST.get("login_novo")
            
            # Validação preventiva para impedir logins duplicados no ecossistema
            if login_ja_existe(login_novo):
                erro_login = "Este login ja esta sendo usado por outra pessoa."
            else:
                senha_crua = request.POST.get("senha_nova")
                senha_hash = make_password(senha_crua)
                
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id_empresa
                        FROM usuario
                        WHERE login = %s
                    """,
                        [login_sessao],
                    )
                    id_empresa = cursor.fetchone()[0]
                    
                    cursor.execute(
                        """
                        INSERT INTO usuario (
                            nome,
                            login,
                            senha,
                            cargo,
                            ativo,
                            id_empresa
                        )
                        VALUES (%s, %s, %s, %s, '1', %s)
                    """,
                        [nome, login_novo, senha_hash, cargo, id_empresa],
                    )
                    
                # Só redireciona se o cadastro for um sucesso
                return redirect("gerenciar_usuarios")

    # --- LÓGICA DE GET (LISTAGEM COM BUSCA E ORDENAÇÃO) ---
    termo_busca = request.GET.get("q", "")

    with connection.cursor() as cursor:
        if termo_busca:
            query_list = """
                SELECT nome, login, cargo FROM usuario
                WHERE id_empresa = (
                    SELECT id_empresa
                    FROM usuario
                    WHERE login = %s
                )
                AND ativo = '1'
                AND (nome ILIKE %s OR login ILIKE %s)
                ORDER BY nome
            """ 
            param_busca = f"%{termo_busca}%"
            cursor.execute(query_list, [login_sessao, param_busca, param_busca])
        else:
            query_list = """
                SELECT nome, login, cargo FROM usuario
                WHERE id_empresa = (
                    SELECT id_empresa
                    FROM usuario
                    WHERE login = %s
                )
                AND ativo = '1'
                ORDER BY nome
            """
            cursor.execute(query_list, [login_sessao])

        colunas = [col[0] for col in cursor.description]
        usuarios_lista = [dict(zip(colunas, row)) for row in cursor.fetchall()]

    contexto.update({
        "perfil": perfil_sessao,
        "usuarios": usuarios_lista,
        "usuario_edit": usuario_para_editar,
        "termo_busca": termo_busca,
    })
    
    if erro_login:
        contexto["erro_login"] = erro_login

    return render(request, "usuarios/usuarios.html", contexto)


# ==========================================================
# EXCLUSÃO LÓGICA DE USUÁRIOS
# ==========================================================
def excluir_usuario_view(request, login_usuario):
    login_sessao = request.session.get("usuario_login")
    perfil_sessao = request.session.get("usuario_perfil")

    if not login_sessao or perfil_sessao != "admin":
        return redirect("dashboard_admin")
        
    # Trava: Impede que o administrador exclua a própria conta
    if login_usuario == login_sessao:
        return redirect("gerenciar_usuarios")
        
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE usuario
            SET ativo = '0'
            WHERE login = %s
        """, [login_usuario])
        
    return redirect("gerenciar_usuarios")