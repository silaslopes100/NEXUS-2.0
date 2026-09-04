"""Testes: cursos, disciplinas, matriculas, notas, pagamentos, cupons, certificados, chat."""
from batch.legacy_sync.mappers.certificados_mapper import CertificadoMapper
from batch.legacy_sync.mappers.cupons_mapper import CupomMapper
from batch.legacy_sync.mappers.cursos_mapper import CursoMapper, _normalize_modalidade
from batch.legacy_sync.mappers.disciplinas_mapper import DisciplinaConteudoMapper, DisciplinaMapper
from batch.legacy_sync.mappers.matriculas_mapper import MatriculaMapper, _first_int
from batch.legacy_sync.mappers.mensagens_mapper import ConversaMapper, MensagemMapper
from batch.legacy_sync.mappers.notas_mapper import NotaMapper
from batch.legacy_sync.mappers.pagamentos_mapper import PagseguroMapper

from conftest import FakeRegistry


def test_normalize_modalidade():
    assert _normalize_modalidade("Polo") == "polo"
    assert _normalize_modalidade("EAD") == "ead"
    assert _normalize_modalidade("hibrido", None) == "hibrido"
    assert _normalize_modalidade("qualquer") is None


def test_curso_mapper_lê_pacotes():
    m = CursoMapper()
    assert m.source_table == "pacotes"
    out = m.map({"id": 1, "title": "Teologia", "description": "desc",
                 "modalidade": "Polo", "status": "active"})
    assert out["nome"] == "Teologia"
    assert out["modalidade"] == "polo"
    assert out["status"] == "ativo"
    out_inativo = m.map({"id": 2, "title": "X", "modalidade": "ead", "status": "inactive"})
    assert out_inativo["status"] == "inativo"


def test_disciplina_mapper_sem_curso_ignora():
    reg = FakeRegistry()
    m = DisciplinaMapper(registry=reg)
    assert m.map({"id": 1, "title": "D1", "course_id": 99, "order": 2}) is None


def test_disciplina_mapper_com_curso():
    reg = FakeRegistry(mapping={("cursos", "pacotes", 10): "curso-uuid"})
    m = DisciplinaMapper(registry=reg)
    out = m.map({"id": 1, "title": "Hermeneutica", "course_id": 10,
                 "order": 2, "qtd_aulas": 12})
    assert out["curso_id"] == "curso-uuid"
    assert out["semestre"] == 2
    assert out["qtd_aulas_prevista"] == 12


def test_conteudo_mapeia_lesson():
    reg = FakeRegistry(mapping={("disciplinas", "section", 3): "disc-uuid"})
    m = DisciplinaConteudoMapper(registry=reg)
    out = m.map({"id": 1, "title": "Aula 1", "section_id": 3,
                 "lesson_type": "video", "video_url": "http://v", "order": 0})
    assert out["disciplina_id"] == "disc-uuid"
    assert out["url_arquivo"] == "http://v"
    assert out["tipo_midia"] == "video"


def test_first_int():
    assert _first_int("12") == 12
    assert _first_int("12,13") == 12
    assert _first_int(None) is None
    assert _first_int("abc") is None


def test_matricula_requer_aluno():
    reg = FakeRegistry(mapping={("alunos", "users", 5): "aluno-uuid"})
    m = MatriculaMapper(registry=reg)
    out = m.map({"id": 1, "user_id": "5", "course_id": "10",
                 "date_added": 1700000000, "licence_id": 8})
    assert out["aluno_id"] == "aluno-uuid"
    assert out["data_matricula"] is not None


def test_nota_mapper():
    reg = FakeRegistry(mapping={("alunos", "users", 5): "aluno-uuid",
                                ("disciplinas", "section", 3): "disc-uuid"})
    m = NotaMapper(registry=reg)
    out = m.map({"id": 1, "user_id": "5", "section_id": "3",
                 "result": "7.5", "data": "2024-01-10"})
    assert out["origem"] == "ava"
    assert out["valor"] == 7.5


def test_nota_sem_aluno_ignora():
    m = NotaMapper(registry=FakeRegistry())
    assert m.map({"id": 1, "user_id": "999", "section_id": "3", "result": 5.0}) is None


def test_pagseguro_mapper_asaas():
    m = PagseguroMapper()
    out = m.map({"id": 1, "id_user": 5, "amount": 199.9, "gateway": "asaas",
                 "status": 1, "asaas_payment_id": "pay_123",
                 "invoice_url": "http://boleto", "due_date": "2024-03-01",
                 "paid_at": "2024-03-02 10:00:00"})
    assert out["gateway"] == "asaas"
    assert out["status"] == "pago"
    assert out["asaas_payment_id"] == "pay_123"
    assert out["boleto_url"] == "http://boleto"


def test_cupom_mapper():
    m = CupomMapper()
    out = m.map({"id": 1, "code": "PROMO10", "discount_percentage": "10,5",
                 "created_at": 1700000000, "expiry_date": 1730000000})
    assert out["codigo"] == "PROMO10"
    assert out["percentual_desconto"] == 10.5
    assert out["valido_de"] is not None


def test_certificado_mapeia():
    reg = FakeRegistry(mapping={("alunos", "users", 5): "aluno-uuid",
                                ("cursos", "pacotes", 3): "curso-uuid"})
    m = CertificadoMapper(registry=reg)
    out = m.map({"id": 1, "student_id": 5, "course_id": 3, "shareable_url": "http://cert"})
    assert out["aluno_id"] == "aluno-uuid"
    assert out["curso_id"] == "curso-uuid"
    assert out["url_arquivo"] == "http://cert"
    # estagios sao campos novos -> None
    assert out["data_estagio_teologia_ministerio"] is None


def test_conversa_registra_thread_code():
    reg = FakeRegistry()
    m = ConversaMapper(registry=reg)
    out = m.map({"message_thread_id": 7, "message_thread_code": "ABC",
                 "last_message_timestamp": "2024-01-01 12:00:00"})
    assert out["tipo"] == "individual"
    assert reg.get_value("thread_code", "ABC") == 7


def test_mensagem_resolve_conversa_pelo_code():
    reg = FakeRegistry(mapping={("conversas", "message_thread", 7): "conv-uuid"})
    reg.set_value("thread_code", "ABC", "7")
    m = MensagemMapper(registry=reg)
    out = m.map({"message_id": 1, "message_thread_code": "ABC",
                 "message": "oi", "sender": "5", "timestamp": "2024-01-01 12:00:00",
                 "read_status": 1})
    assert out["conversa_id"] == "conv-uuid"
    assert out["texto"] == "oi"