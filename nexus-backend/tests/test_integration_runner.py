"""Teste de integracao do pipeline contra um PostgreSQL real (embarcado via pgserver).

Cobertura: ensure_schema -> perfis padrao -> mappers (polos/usuarios/alunos) ->
resolucao de FK (usuario.polo_id, aluno.usuario_id) -> idempotencia (2a execucao
nao duplica). Pula silenciosamente se `pgserver` nao estiver instalado.
"""
import pytest

pgserver = pytest.importorskip("pgserver")
import psycopg2

from batch.legacy_sync.etl_sync_log import RunLogger
from batch.legacy_sync.mappers.alunos_mapper import AlunoMapper, gerar_matriculas_nx
from batch.legacy_sync.mappers.perfis_mapper import ensure_defaults
from batch.legacy_sync.mappers.polos_mapper import PoloMapper
from batch.legacy_sync.mappers.usuarios_mapper import UsuarioMapper
from batch.legacy_sync.registry import IdRegistry
from batch.legacy_sync.runner import MapperRunner
from batch.legacy_sync.target_postgres import PostgresTarget

from conftest import FakeRegistry  # noqa: F401  (importar caminho dos fakes)


class FakeMySQLSource:
    """Substituto de MySQLSource: stream() alimentado por dicts."""

    def __init__(self, tabelas: dict[str, list[dict]]):
        self.tabelas = tabelas

    def stream(self, table, columns, where=None, params=(), order=None, offset=0):
        import re

        roles = None
        if where:
            m = re.search(r"role_id IN \(([\d, ]+)\)", where) or re.search(r"role_id = (\d+)", where)
            if m:
                roles = {int(x) for x in m.group(1).split(",")}
        for row in self.tabelas.get(table, []):
            if roles is not None and row.get("role_id") not in roles:
                continue
            yield row


@pytest.fixture(scope="module")
def pg():
    import tempfile
    from pathlib import Path

    workdir = Path(tempfile.mkdtemp(prefix="nexus_pg_"))
    server = pgserver.get_server(workdir / "pgdata", cleanup_mode="delete")
    target = PostgresTarget(server.get_uri())
    target.ensure_schema()
    ensure_defaults(target)
    yield target
    target.close()
    server.cleanup()


def _contagem(target, tabela):
    with target.conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {tabela}")
        return cur.fetchone()[0]


def _usuarios_linha(**kw):
    row = {
        "id": 1, "first_name": "Joao", "last_name": "Silva", "email": "j@x.com",
        "password": "h", "role_id": None, "status": 1, "is_instructor": 0,
        "is_vendedor": 0, "polo": 5, "escola": None, "is_secret": 0,
        "is_exec": 0, "is_pedag": 0, "cpf": "11111111111", "telefone": None,
        "celular": None, "image": None, "nascimento": None, "revalidacao": None,
        "last_modified": 1700000000,
    }
    row.update(kw)
    return row


def _rodar(target, registry, run_log, tabelas, mappers):
    source = FakeMySQLSource(tabelas)
    runner = MapperRunner(source, target, registry, run_log, batch_size=50)
    for cls in mappers:
        runner.run(cls(registry=registry))
    return runner


def test_pipeline_completo_e_idempotente(pg):
    tabelas = {
        "users": [
            # representante do polo (user distinto; id 10 so serve p/ o polo)
            {"id": 10, "role_id": 3, "polo": 5, "nome_polo": "Polo Centro",
             "first_name": "Ana", "last_name": "R", "email": "ana@x",
             "cpf": "1", "cep": "01000-000", "uf": "SP", "telefone": None,
             "status": 1},
            # Joao: role 2 com polo 5 -> aluno do polo (regra da migracao)
            _usuarios_linha(id=1, role_id=2, polo=5, email="joao@x.com"),
            # Bia: role 2 sem polo/escola -> aluno EAD
            _usuarios_linha(id=2, role_id=2, polo=0, email="bia@x.com", cpf="2",
                            codigo="MAT-9"),
        ],
    }

    registry = IdRegistry(pg)
    run_log = RunLogger(pg, "full")
    run_log.start()

    # 1a execucao: cria tudo
    _rodar(pg, registry, run_log, tabelas, [PoloMapper, UsuarioMapper, AlunoMapper])

    assert _contagem(pg, "polos") == 1
    assert _contagem(pg, "usuarios") == 2  # so role 2
    assert _contagem(pg, "alunos") == 2  # Joao (polo) e Bia (EAD)
    gerar_matriculas_nx(pg)

    # FKs resolvidas
    with pg.conn.cursor() as cur:
        cur.execute("SELECT nome FROM polos")
        assert cur.fetchone()[0] == "Polo Centro"
        cur.execute(
            "SELECT u.nome, (u.polo_id IS NOT NULL) FROM usuarios u "
            "WHERE u.email='joao@x.com'"
        )
        assert cur.fetchone()[1] is True
        cur.execute(
            "SELECT a.numero_matricula FROM alunos a "
            "JOIN usuarios u ON u.id = a.usuario_id WHERE u.email='bia@x.com'"
        )
        assert cur.fetchone()[0].startswith("NX-")  # padrao NEXUS, sem codigo legado

    # 2a execucao: idempotente (atualiza, nao duplica)
    registry2 = IdRegistry(pg)
    run_log2 = RunLogger(pg, "full")
    run_log2.start()
    _rodar(pg, registry2, run_log2, tabelas, [PoloMapper, UsuarioMapper, AlunoMapper])

    assert _contagem(pg, "polos") == 1
    assert _contagem(pg, "usuarios") == 2  # so role 2
    assert _contagem(pg, "alunos") == 2

    # a 2a execucao atualizou (inseridos=0)
    assert run_log2.total_inserido == 0
    assert run_log2.total_atualizado > 0

    run_log2.finish("ok")
    run_log.finish("ok")