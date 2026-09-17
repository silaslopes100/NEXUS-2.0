"""Testes dos mappers de usuarios/polos/escolas/alunos/professores."""
from batch.legacy_sync.mappers.alunos_mapper import AlunoMapper
from batch.legacy_sync.mappers.escolas_mapper import EscolaMapper
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


def test_usuario_perfil_heuristica_sem_role():
    reg = FakeRegistry()
    m = UsuarioMapper(registry=reg)
    # sem role mapeada: user com polo e sem escola -> polo
    assert m.map(_usuario_row(role_id=None))["perfil_id"] == "u-polo"
    # staff central -> admin
    assert m.map(_usuario_row(role_id=None, is_pedag=1))["perfil_id"] == "u-admin"
    # instrutor -> professor
    assert m.map(_usuario_row(role_id=None, is_instructor=1))["perfil_id"] == "u-prof"
    # com escola -> escola
    assert m.map(_usuario_row(role_id=None, polo=0, escola=9))["perfil_id"] == "u-escola"
    # resto -> aluno
    assert m.map(_usuario_row(role_id=None, polo=0))["perfil_id"] == "u-aluno"


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
    assert m.map(r1)["cpf"] == "037.060.304-46"
    assert m.map(r2)["cpf"] is None
    assert any("cpf duplicado" in w for w in m.warnings)


def test_usuario_mesmo_id_mantem_cpf_e_email_em_update():
    m = UsuarioMapper(registry=FakeRegistry())
    r1 = _usuario_row(id=1, email="user@x.com", cpf="037.060.304-46")
    assert m.map(r1)["cpf"] == "037.060.304-46"
    assert m.map(r1)["email"] == "user@x.com"
    # Re-mapeamento do mesmo usuario (ex.: incremental update) nao deve anular os campos
    r1_updated = _usuario_row(id=1, first_name="Joao Alterado", email="user@x.com", cpf="037.060.304-46")
    mapped = m.map(r1_updated)
    assert mapped["cpf"] == "037.060.304-46"
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


def test_escola_mapeia_com_polo():
    reg = FakeRegistry(mapping={("polos", "users", 5): "polo-uuid"})
    m = EscolaMapper(registry=reg)
    out = m.map({"id": 1, "escola": 9, "nome_escola": "Escola Luz",
                 "polo": 5, "first_name": "C", "last_name": "D",
                 "email": "c@x", "cpf": None, "status": 1})
    assert out["nome"] == "Escola Luz"
    assert out["polo_id"] == "polo-uuid"
    assert m.current_legacy_id({"escola": 9}) == 9


def test_aluno_modalidade_e_matricula():
    reg = FakeRegistry(mapping={("usuarios", "users", 1): "usuario-uuid",
                                ("usuarios", "users", 2): "usuario-uuid2",
                                ("polos", "users", 5): "polo-uuid"})
    m = AlunoMapper(registry=reg)
    out = m.map(_usuario_row(id=1, polo=5, codigo="MAT-01"))
    assert out["modalidade"] == "polo"
    assert out["numero_matricula"] == "MAT-01"
    assert out["status"] == "ativo"

    out_ead = m.map(_usuario_row(id=2, polo=0, codigo=None, revalidacao="sim"))
    assert out_ead["modalidade"] == "ead"
    assert out_ead["numero_matricula"] == "legacy-2"
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