"""Testes dos mappers de usuarios/polos/escolas/alunos/professores."""
from batch.legacy_sync.mappers.alunos_mapper import AlunoMapper
from batch.legacy_sync.mappers.perfis_mapper import PerfilMapper
from batch.legacy_sync.mappers.polos_mapper import PoloMapper
from batch.legacy_sync.mappers.professores_mapper import ProfessorMapper
from batch.legacy_sync.mappers.usuarios_mapper import UsuarioMapper

from conftest import FakeRegistry


def _usuario_row(**over):
    row = {
        "id": 1, "first_name": "Joao", "last_name": "Silva", "email": "j@x.com",
        "password": "hash_legado", "role_id": 2, "status": 1,
        "is_instructor": 0, "is_vendedor": 0, "polo": 5, "escola": None,
        "is_secret": 0, "is_exec": 0, "is_pedag": 0, "cpf": "11111111111",
        "telefone": None, "celular": None, "image": None, "nascimento": None,
        "revalidacao": None, "last_modified": 1700000000,
    }
    row.update(over)
    return row


def test_usuario_mapeia_campos_base():
    reg = FakeRegistry(
        mapping={
            ("polos", "users", 5): "polo-uuid",
            ("perfis", "role", 2): "u-aluno",
        }
    )
    m = UsuarioMapper(registry=reg)
    out = m.map(_usuario_row())
    assert out["nome"] == "Joao"
    assert out["sobrenome"] == "Silva"
    assert out["email"] == "j@x.com"
    assert out["senha_algoritmo"] == "legacy_bcrypt"
    assert out["senha_hash"] == "hash_legado"
    assert out["polo_id"] == "polo-uuid"
    assert out["status"] == "ativo"


def test_usuario_pula_usuarios_ja_carregados_na_carga_inicial():
    mapper = UsuarioMapper(registry=FakeRegistry())

    assert mapper.initial_offset() == 0


def test_usuario_perfil_regra_da_migracao():
    m = UsuarioMapper(registry=FakeRegistry())
    # role 2 com polo continua aluno (nao vira coordenador por ter polo)
    assert m.map(_usuario_row(id=11, role_id=2, polo=5, cpf=None, email=None))["perfil_id"] == "u-aluno"
    # instrutor -> professor
    assert m.map(_usuario_row(id=12, role_id=2, is_instructor=1, cpf=None, email=None))["perfil_id"] == "u-prof"
    # is_secret / is_exec / is_pedag -> aluno (decisao: nao vira admin)
    for k, lid in (("is_secret", 13), ("is_exec", 14), ("is_pedag", 15)):
        assert m.map(_usuario_row(id=lid, role_id=2, cpf=None, email=None, **{k: 1}))["perfil_id"] == "u-aluno"
    # com escola e sem conta role 4 -> continua aluno
    assert m.map(_usuario_row(id=16, role_id=2, polo=0, escola=9, cpf=None, email=None))["perfil_id"] == "u-aluno"

def test_usuario_email_duplicado_vira_none():
    m = UsuarioMapper(registry=FakeRegistry())
    r1 = _usuario_row(id=1, email="dup@x.com")
    r2 = _usuario_row(id=2, email="dup@x.com")
    assert m.map(r1)["email"] == "dup@x.com"
    assert m.map(r2)["email"] is None
    assert any("duplicado" in w for w in m.warnings)


def test_usuario_cpf_duplicado_vira_none():
    m = UsuarioMapper(registry=FakeRegistry())
    r1 = _usuario_row(id=1, cpf="037.060.304-46")
    r2 = _usuario_row(id=2, cpf="037.060.304-46")
    assert m.map(r1)["cpf"] == "03706030446"
    assert m.map(r2)["cpf"] is None
    assert any("cpf duplicado" in w for w in m.warnings)


def test_usuario_cpf_com_e_sem_mascara_e_mesma_pessoa():
    m = UsuarioMapper(registry=FakeRegistry())
    assert m.map(_usuario_row(id=1, cpf="037.060.304-46"))["cpf"] == "03706030446"
    # mesmo CPF sem mascara e sem o zero a esquerda (salvo como numero)
    assert m.map(_usuario_row(id=2, cpf="3706030446"))["cpf"] is None
    assert any("cpf duplicado" in w for w in m.warnings)


def test_usuario_cpf_invalido_vira_none_com_aviso():
    m = UsuarioMapper(registry=FakeRegistry())
    assert m.map(_usuario_row(id=1, cpf="123"))["cpf"] is None
    assert m.map(_usuario_row(id=2, cpf="000.000.000-00"))["cpf"] is None
    assert any("cpf invalido" in w for w in m.warnings)


def test_usuario_email_minusculo_e_dedup_sem_caixa():
    m = UsuarioMapper(registry=FakeRegistry())
    assert m.map(_usuario_row(id=1, email="Joao@X.com", cpf=None))["email"] == "joao@x.com"
    assert m.map(_usuario_row(id=2, email="JOAO@x.COM", cpf=None))["email"] is None


def test_usuario_reupsert_nao_sobrescreve_dados_do_nexus():
    # senha/algoritmo/ultimo login sao do NEXUS depois do 1o login
    assert "senha_algoritmo" in UsuarioMapper.insert_only_columns
    assert "ultimo_login_em" in UsuarioMapper.insert_only_columns
    assert "legacy_bcrypt" in UsuarioMapper.update_expressions["senha_hash"]
    # NULL da deduplicacao nunca apaga e-mail/CPF ja gravados
    assert UsuarioMapper.update_expressions["email"].startswith("COALESCE({table}.email")
    assert UsuarioMapper.update_expressions["cpf"].startswith("COALESCE({table}.cpf")


def test_preload_role_map_le_tabela_role():
    from batch.legacy_sync.mappers.perfis_mapper import preload_role_map

    class Src:
        def stream(self, table, cols, **kw):
            assert table == "role"
            yield from [
                {"id": 1, "name": "Admin"},
                {"id": 7, "name": "Secretaria"},
                {"id": 9, "name": "coisa_estranha"},
            ]

    reg = FakeRegistry()
    assert preload_role_map(Src(), reg) == 2
    assert reg.role_to_perfil_nome(7) == "admin"
    assert reg.role_to_perfil_nome(9) is None


def test_usuario_mesmo_id_mantem_cpf_e_email_em_update():
    m = UsuarioMapper(registry=FakeRegistry())
    r1 = _usuario_row(id=1, email="user@x.com", cpf="037.060.304-46")
    assert m.map(r1)["cpf"] == "03706030446"
    assert m.map(r1)["email"] == "user@x.com"
    # Re-mapeamento do mesmo usuario (ex.: incremental update) nao deve anular os campos
    r1_updated = _usuario_row(id=1, first_name="Joao Alterado", email="user@x.com", cpf="037.060.304-46")
    mapped = m.map(r1_updated)
    assert mapped["cpf"] == "03706030446"
    assert mapped["email"] == "user@x.com"
    assert mapped["nome"] == "Joao Alterado"


def test_polo_seleciona_apenas_role_de_polo():
    reg = FakeRegistry()
    m = PoloMapper(registry=reg)

    class Src:
         def stream(self, table, cols, where=None, params=(), order=None, offset=0):
             rows = [
              {"id": 10, "role_id": 3, "polo": 5, "nome_polo": "Polo Centro",
                   "first_name": "Ana", "last_name": "R", "email": "ana@x",
                 "cpf": "1", "cep": "01000-000", "uf": "SP", "status": 1},
              {"id": 11, "role_id": 3, "polo": 5, "nome_polo": "Polo Centro",
                   "first_name": "Bia", "last_name": "R", "email": "bia@x",
                 "cpf": "2", "cep": "01000-000", "uf": "SP", "status": 1},
              {"id": 12, "role_id": 2, "polo": 0, "nome_polo": None,
                   "first_name": "X", "last_name": "Y", "email": None,
                 "cpf": None, "cep": None, "uf": None, "status": 1},
             ]
             yield from (row for row in rows if row["role_id"] == 3)

    rows = list(m.iter_source(Src()))
    assert len(rows) == 2  # uma linha por usuario com role_id=3
    out = m.map(rows[0])
    assert out["nome"] == "Polo Centro"
    assert m.current_legacy_id(rows[0]) == 10


def test_aluno_modalidade_e_matricula():
    reg = FakeRegistry(mapping={("usuarios", "users", 1): "usuario-uuid",
                                ("usuarios", "users", 2): "usuario-uuid2",
                                ("polos", "users", 5): "polo-uuid"})
    m = AlunoMapper(registry=reg)
    out = m.map(_usuario_row(id=1, polo=5, codigo="MAT-01"))
    assert out["modalidade"] == "polo"
    # matricula NX e gerada depois (gerar_matriculas_nx); nada do codigo legado
    assert "numero_matricula" not in out
    assert out["status"] == "ativo"

    out_ead = m.map(_usuario_row(id=2, polo=0, codigo=None, revalidacao="sim"))
    assert out_ead["modalidade"] == "ead"
    assert out_ead["status"] == "desistente"


def test_professor_so_instrutores():
    reg = FakeRegistry(mapping={("usuarios", "users", 1): "usuario-uuid"})
    m = ProfessorMapper(registry=reg)
    assert m.map(_usuario_row(id=1, is_instructor=1))["usuario_id"] == "usuario-uuid"


def test_perfil_normaliza_sinonimos():
    assert PerfilMapper.normalize_name("Instructor") == "professor"
    assert PerfilMapper.normalize_name("Coordenador Polo") == "polo"
    assert PerfilMapper.normalize_name("Student") == "aluno"
    assert PerfilMapper.normalize_name("Secretaria Geral") == "admin"
    assert PerfilMapper.normalize_name("coisa_estranha") is None
    # role desconhecida nao vira perfil (cai na heuristica de flags)
    assert PerfilMapper().map({"id": 1, "name": "coisa_estranha"}) is None

def test_incremental_filter_compara_unix_e_datetime():
    from datetime import datetime, timezone

    from batch.legacy_sync.mappers.base import INCREMENTAL_MARGIN

    last_run = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)
    where, params = UsuarioMapper().incremental_filter(last_run)
    assert "REGEXP" in where and where.count("%s") == 2
    unix, texto = params
    # unix int (nao a string '2026-...', que o MySQL converteria em 2026)
    assert unix == int((last_run - INCREMENTAL_MARGIN).timestamp())
    assert isinstance(texto, str) and texto.startswith("2026-11-19")


def test_upsert_sql_protege_colunas_do_nexus(monkeypatch):
    from batch.legacy_sync import target_postgres as tp

    capturado = {}

    def fake_execute_values(cur, sql, chunk, fetch, page_size):
        capturado["sql"] = sql
        return [("uuid-1", True)]

    class Cur:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class Conn:
        closed = False

        def cursor(self):
            return Cur()

    monkeypatch.setattr(tp, "execute_values", fake_execute_values)
    target = tp.PostgresTarget("dsn")
    target._conn = Conn()
    cols = ["nome", "email", "cpf", "senha_hash", "senha_algoritmo", "ultimo_login_em",
            "legacy_table", "legacy_id", "synced_at"]
    target.upsert_rows(
        "usuarios", cols, [[None] * len(cols)],
        insert_only=UsuarioMapper.insert_only_columns,
        update_expressions=UsuarioMapper.update_expressions,
    )
    update = capturado["sql"].split("DO UPDATE SET", 1)[1]
    assert "nome = EXCLUDED.nome" in update
    assert "email = COALESCE(usuarios.email, EXCLUDED.email)" in update
    assert "senha_hash = CASE WHEN usuarios.senha_algoritmo = 'legacy_bcrypt'" in update
    assert "senha_algoritmo = EXCLUDED" not in update
    assert "ultimo_login_em = EXCLUDED" not in update


def test_usuario_le_role_2_e_contas_role_3_4():
    from datetime import datetime, timezone

    chamadas = []

    class Src:
        def stream(self, table, cols, where=None, params=(), order=None, offset=0):
            chamadas.append((where, params))
            return iter(())

    m = UsuarioMapper(registry=FakeRegistry())
    list(m.iter_source(Src()))
    assert chamadas[-1][0] == "role_id IN (2, 3, 4)"
    # no incremental, o filtro de role e combinado com o de data
    list(m.iter_source(Src(), last_run=datetime(2026, 11, 19, tzinfo=timezone.utc)))
    where, params = chamadas[-1]
    assert where.endswith("AND (role_id IN (2, 3, 4))") and "REGEXP" in where and len(params) == 2


class _SrcRoles:
    """users legado por role; entende os filtros usados pelo UsuarioMapper."""

    def __init__(self, users):
        self.users = sorted(users, key=lambda u: u["id"])

    def stream(self, table, cols, where=None, params=(), order=None, offset=0):
        import re

        assert table == "users"
        roles = None
        m = where and (re.search(r"role_id IN \(([\d, ]+)\)", where) or re.search(r"role_id = (\d+)", where))
        if m:
            roles = {int(x) for x in m.group(1).split(",")}
        for u in self.users:
            if roles is None or u.get("role_id") in roles:
                yield u


def _mapear_todos(m, src):
    out = {row["id"]: m.map(row) for row in m.iter_source(src)}
    return {k: v for k, v in out.items() if v is not None}


def test_titular_role2_recebe_vinculo_do_polo_role3_sem_duplicar():
    reg = FakeRegistry(mapping={("polos", "users", 10): "polo-10"})
    src = _SrcRoles([
        _usuario_row(id=1, role_id=2, cpf="037.060.304-46", polo=0, email="a@x"),
        _usuario_row(id=5, role_id=2, cpf="03706030446", polo=0, email="b@x"),  # mesmo CPF
        {"id": 10, "role_id": 3, "cpf": "03706030446", "escola_old": None},
    ])
    m = UsuarioMapper(registry=reg)
    out = _mapear_todos(m, src)
    # so contas role 2 viram usuario (a conta role 3 nao e duplicada)
    assert set(out) == {1, 5}
    # titular = menor users.id role 2 com o CPF
    assert out[1]["perfil_id"] == "u-polo" and out[1]["polo_id"] == "polo-10"
    # o outro role 2 com o mesmo CPF nao recebe o vinculo (e perde o CPF, como antes)
    assert out[5]["polo_id"] is None and out[5]["cpf"] is None


def test_titular_role2_recebe_escola_role4_e_escola_prevalece_sobre_polo():
    reg = FakeRegistry(mapping={
        ("polos", "users", 10): "polo-10",
        ("escolas", "users", 300): "esc-300",
        ("escolas", "users", 301): "esc-301",
    })
    src = _SrcRoles([
        _usuario_row(id=2, role_id=2, cpf="11144477735", polo=0),
        {"id": 10, "role_id": 3, "cpf": "111.444.777-35", "escola_old": None},
        {"id": 20, "role_id": 4, "cpf": "111.444.777-35", "escola_old": 300},
        {"id": 21, "role_id": 4, "cpf": "11144477735", "escola_old": 301},
    ])
    m = UsuarioMapper(registry=reg)
    m._escola_polo = {"esc-300": "polo-da-escola"}
    out = _mapear_todos(m, src)
    assert set(out) == {2}
    assert out[2]["perfil_id"] == "u-escola"
    assert out[2]["escola_id"] == "esc-300"          # menor id legado
    assert out[2]["polo_id"] == "polo-da-escola"     # polo vem da escola
    assert any("2 escolas" in w for w in m.warnings)


def test_escola_sem_polo_usa_polo_coordenado():
    reg = FakeRegistry(mapping={("polos", "users", 10): "polo-10", ("escolas", "users", 300): "esc-300"})
    src = _SrcRoles([
        _usuario_row(id=2, role_id=2, cpf="11144477735", polo=0),
        {"id": 10, "role_id": 3, "cpf": "11144477735", "escola_old": None},
        {"id": 20, "role_id": 4, "cpf": "11144477735", "escola_old": 300},
    ])
    m = UsuarioMapper(registry=reg)
    m._escola_polo = {"esc-300": None}
    out = _mapear_todos(m, src)
    assert out[2]["escola_id"] == "esc-300" and out[2]["polo_id"] == "polo-10"


def test_role2_sem_conta_role3_4_segue_regra_normal():
    reg = FakeRegistry(mapping={("polos", "users", 5): "polo-5"})
    src = _SrcRoles([_usuario_row(id=3, role_id=2, cpf="11144477735", polo=5)])
    out = _mapear_todos(UsuarioMapper(registry=reg), src)
    assert out[3]["polo_id"] == "polo-5"


def test_opcao_b_conta_role4_sem_par_vira_usuario_da_escola():
    reg = FakeRegistry(mapping={("escolas", "users", 300): "esc-300", ("escolas", "users", 301): "esc-301"})
    src = _SrcRoles([
        _usuario_row(id=1, role_id=2, cpf="11144477735", email="pessoa@x"),
        # sem CPF: a propria conta vira usuario da escola
        {**_usuario_row(id=20, role_id=4, cpf=None, email="escola300@x", polo=0), "escola_old": 300},
        # CPF sem role 2: vira usuario (titular por CPF)
        {**_usuario_row(id=21, role_id=4, cpf="52998224725", email="escola301@x", polo=0), "escola_old": 301},
    ])
    m = UsuarioMapper(registry=reg)
    m._escola_polo = {"esc-300": "polo-a", "esc-301": "polo-b"}
    out = _mapear_todos(m, src)
    assert set(out) == {1, 20, 21}
    assert (out[20]["perfil_id"], out[20]["escola_id"], out[20]["polo_id"]) == ("u-escola", "esc-300", "polo-a")
    assert (out[21]["perfil_id"], out[21]["escola_id"], out[21]["cpf"]) == ("u-escola", "esc-301", "52998224725")


def test_opcao_b_conta_com_par_role2_nao_duplica():
    reg = FakeRegistry(mapping={("polos", "users", 10): "polo-10"})
    src = _SrcRoles([
        {**_usuario_row(id=10, role_id=3, cpf="11144477735", email="polo@x", polo=0), "escola_old": None},
        _usuario_row(id=50, role_id=2, cpf="111.444.777-35", email="pessoa@x", polo=0),
    ])
    out = _mapear_todos(UsuarioMapper(registry=reg), src)
    # conta role 3 tem id menor, mas o titular e o role 2: so ele vira usuario
    assert set(out) == {50}
    assert out[50]["polo_id"] == "polo-10" and out[50]["cpf"] == "11144477735"


def test_opcao_b_mesma_pessoa_em_contas_role3_e_role4_sem_role2_vira_um_usuario():
    reg = FakeRegistry(mapping={("polos", "users", 10): "polo-10", ("escolas", "users", 300): "esc-300"})
    src = _SrcRoles([
        {**_usuario_row(id=10, role_id=3, cpf="11144477735", email="polo@x", polo=0), "escola_old": None},
        {**_usuario_row(id=20, role_id=4, cpf="11144477735", email="esc@x", polo=0), "escola_old": 300},
    ])
    m = UsuarioMapper(registry=reg)
    m._escola_polo = {"esc-300": None}
    out = _mapear_todos(m, src)
    assert set(out) == {10}  # menor conta com o CPF
    assert (out[10]["perfil_id"], out[10]["escola_id"], out[10]["polo_id"]) == ("u-escola", "esc-300", "polo-10")


def test_opcao_b_conta_nao_rouba_email_de_role2():
    reg = FakeRegistry(mapping={("polos", "users", 10): "polo-10"})
    src = _SrcRoles([
        {**_usuario_row(id=10, role_id=3, cpf=None, email="Mesmo@x", polo=0), "escola_old": None},
        _usuario_row(id=50, role_id=2, cpf="11144477735", email="mesmo@x", polo=0),
    ])
    m = UsuarioMapper(registry=reg)
    out = _mapear_todos(m, src)
    assert out[10]["email"] is None and out[50]["email"] == "mesmo@x"
    assert out[10]["polo_id"] == "polo-10"


def test_gerar_matriculas_nx_padrao_nexus(monkeypatch):
    from batch.legacy_sync.mappers import alunos_mapper as am

    resultados = iter([
        [("a-1",), ("a-2",)],      # alunos sem matricula (ordem legacy_id)
        [("2026",)],               # ano
        [(6,), (5,)],              # nextval (fora de ordem de proposito)
    ])
    gravado = {}

    class Cur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, sql, params=()): self._r = next(resultados)
        def fetchall(self): return self._r
        def fetchone(self): return self._r[0]

    class Target:
        class conn:
            @staticmethod
            def cursor(): return Cur()
        def commit(self): gravado["commit"] = True

    monkeypatch.setattr(am, "execute_values", lambda cur, sql, vals, page_size: gravado.update(sql=sql, vals=vals))
    assert am.gerar_matriculas_nx(Target()) == 2
    assert gravado["vals"] == [("a-1", "NX-2026-0000005"), ("a-2", "NX-2026-0000006")]
    assert "numero_matricula IS NULL" in gravado["sql"] and gravado["commit"]


def test_only_aceita_lista_e_respeita_ordem_de_dependencia():
    import pytest as _pytest
    from batch.legacy_sync.run_full_load import selecionar_mappers

    nomes = [m.__name__ for m in selecionar_mappers(
        "AlunoMapper, ProfessorMapper,UsuarioMapper,EscolaLegacyMapper,PoloMapper")]
    assert nomes == ["PoloMapper", "EscolaLegacyMapper", "UsuarioMapper", "ProfessorMapper", "AlunoMapper"]
    with _pytest.raises(SystemExit):
        selecionar_mappers("PoloMapper,NaoExiste")


def test_escolas_orfas_de_role4_sao_criadas_sem_polo():
    from batch.legacy_sync.mappers.escolas_legacy_mapper import EscolaLegacyMapper

    class Cur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, sql, params=()): self.params = params
        def fetchall(self):
            return [{"escola_old": 300, "nome_escola": "Escola A", "cep": None, "logradouro": None,
                     "numero": None, "bairro": None, "cidade": None, "uf": None, "complemento": None}]

    class Src:
        class conn:
            @staticmethod
            def cursor(): return Cur()

        def stream(self, table, cols, where=None, params=(), order=None, offset=0):
            if where.startswith("role_id = 3"):
                yield {"id": 10, "role_id": 3, "escolas": "[300]", "polo": None, "cep": "1", "logradouro": None,
                       "numero": None, "bairro": None, "cidade": None, "uf": None, "complemento": None}
            else:
                yield from [
                    {"escola_old": 300, "nome_escola": "Escola A"},          # ja veio pelo polo
                    {"escola_old": 301, "nome_escola": "Escola Orfa", "uf": "SP"},
                    {"escola_old": 301, "nome_escola": "Escola Orfa (dup)"},  # mesma escola
                ]

    reg = FakeRegistry(mapping={("polos", "users", 10): "polo-10"})
    m = EscolaLegacyMapper(registry=reg)
    rows = list(m.iter_source(Src()))
    assert [m.current_legacy_id(r) for r in rows] == [300, 301]
    assert m.map(rows[0])["polo_id"] == "polo-10"
    orfa = m.map(rows[1])
    assert orfa["polo_id"] is None and orfa["nome"] == "Escola Orfa" and orfa["uf"] == "SP"
    assert any("sem polo" in w for w in m.warnings)


def test_usuario_polo_extinto_usa_polo_da_escola():
    reg = FakeRegistry(mapping={("escolas", "users", 9): "esc-9"})
    m = UsuarioMapper(registry=reg)
    m._escola_polo = {"esc-9": "polo-da-escola"}
    out = m.map(_usuario_row(id=40, role_id=2, polo=3742, escola=9, cpf=None, email=None))
    assert (out["polo_id"], out["escola_id"]) == ("polo-da-escola", "esc-9")


def test_aluno_copia_lotacao_do_usuario_migrado():
    reg = FakeRegistry(mapping={("usuarios", "users", 1): "usuario-uuid"})
    m = AlunoMapper(registry=reg)
    m._usuarios = {1: {"perfil": "aluno", "polo_id": "polo-x", "escola_id": "esc-y"}}
    out = m.map(_usuario_row(id=1, polo=3742, escola=None))
    assert (out["polo_id"], out["escola_id"], out["modalidade"]) == ("polo-x", "esc-y", "polo")


def test_update_escolas_polo_id_menor_polo_vence():
    from batch.legacy_sync.run_full_load import update_escolas_polo_id

    updates = []

    class Cur:
        rowcount = 1
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, sql, params=()):
            if sql.strip().startswith("UPDATE"):
                updates.append(params)
        def fetchall(self): return [(10, "polo-10"), (20, "polo-20")]

    class Target:
        class conn:
            @staticmethod
            def cursor(): return Cur()
        def commit(self): pass

    class Src:
        def stream(self, table, cols, where=None, params=(), order=None, offset=0):
            assert order == "id"
            yield {"id": 10, "escolas": "[300,301]"}
            yield {"id": 20, "escolas": "[301,302]"}  # 301 ja e do polo 10

    update_escolas_polo_id(Src(), Target())
    assert updates == [("polo-10", 300, 301, "polo-10"), ("polo-20", 302, "polo-20")]


def test_usuario_polo_da_escola_vence_users_polo_divergente():
    reg = FakeRegistry(mapping={("polos", "users", 10): "polo-10", ("escolas", "users", 9): "esc-9"})
    m = UsuarioMapper(registry=reg)
    m._escola_polo = {"esc-9": "polo-da-escola"}
    out = m.map(_usuario_row(id=41, role_id=2, polo=10, escola=9, cpf=None, email=None))
    assert out["polo_id"] == "polo-da-escola"
    # escola sem polo: mantem o users.polo
    m._escola_polo = {"esc-9": None}
    out = m.map(_usuario_row(id=42, role_id=2, polo=10, escola=9, cpf=None, email=None))
    assert out["polo_id"] == "polo-10"


def test_aluno_sem_polo_escola_vai_para_ead():
    m = UsuarioMapper(registry=FakeRegistry())
    m._ead = ("polo-ead", "esc-ead")
    out = m.map(_usuario_row(id=60, role_id=2, polo=3742, escola=None, cpf=None, email=None))
    assert (out["polo_id"], out["escola_id"]) == ("polo-ead", "esc-ead")
    # professor sem polo nao e afetado
    out = m.map(_usuario_row(id=61, role_id=2, is_instructor=1, polo=0, cpf=None, email=None))
    assert (out["polo_id"], out["escola_id"]) == (None, None)
    # aluno com polo valido nao e afetado
    reg = FakeRegistry(mapping={("polos", "users", 5): "polo-5"})
    m2 = UsuarioMapper(registry=reg)
    m2._ead = ("polo-ead", "esc-ead")
    assert m2.map(_usuario_row(id=62, role_id=2, polo=5, cpf=None, email=None))["polo_id"] == "polo-5"


def test_aluno_na_escola_ead_mantem_modalidade_ead():
    reg = FakeRegistry(mapping={("usuarios", "users", 1): "usuario-uuid"})
    m = AlunoMapper(registry=reg)
    m._usuarios = {1: {"perfil": "aluno", "polo_id": "polo-ead", "escola_id": "esc-ead"}}
    m._escola_ead = "esc-ead"
    out = m.map(_usuario_row(id=1))
    assert (out["polo_id"], out["escola_id"], out["modalidade"]) == ("polo-ead", "esc-ead", "ead")
