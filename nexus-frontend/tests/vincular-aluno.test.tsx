// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { AlunoFormModal } from '@/features/alunos/components/AlunoFormModal';
import { alunosApi } from '@/features/alunos/api';
import { TurmaAlunosPanel } from '@/features/turmas/components/TurmaAlunosPanel';
import { turmasApi } from '@/features/turmas/api';

vi.mock('@/features/alunos/api', () => ({
  alunosApi: { usuariosDisponiveis: vi.fn(), vincularUsuario: vi.fn() },
  apiErrorMessage: (_err: unknown, fallback: string) => fallback,
}));
vi.mock('@/features/turmas/api', () => ({
  turmasApi: { listarAlunos: vi.fn(), buscarAlunosDisponiveis: vi.fn(), matricularAluno: vi.fn() },
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(alunosApi.usuariosDisponiveis).mockResolvedValue({
    total: 1, items: [{ id: 'u1', nome: 'Ana', sobrenome: 'Silva', email: 'ana@example.test' }],
  });
  vi.mocked(alunosApi.vincularUsuario).mockResolvedValue({
    id: 'a1', usuario_id: 'u1', nome: 'Ana', numero_matricula: 'NX-2026-0000001',
    modalidade: 'escola', status: 'ativo', quantidade_presencas: 0, percentual_presenca: 0,
  });
});
afterEach(cleanup);

it('busca e vincula a conta existente sem solicitar outra senha', async () => {
  const onSuccess = vi.fn();
  render(<AlunoFormModal poloId="p1" escolas={[]} escolaFixaId="e1" inicialExistente onClose={vi.fn()} onSuccess={onSuccess} />);
  fireEvent.change(screen.getByLabelText('Buscar usuário aluno'), { target: { value: 'Ana' } });
  fireEvent.click(await screen.findByText('Ana Silva — ana@example.test'));
  fireEvent.change(screen.getByLabelText('Data de nascimento'), { target: { value: '2000-01-01' } });
  fireEvent.click(screen.getByText('Vincular aluno'));
  await waitFor(() => expect(alunosApi.vincularUsuario).toHaveBeenCalledWith('p1', {
    usuario_id: 'u1', data_nascimento: '2000-01-01', modalidade: 'escola', escola_id: 'e1',
  }));
  expect(alunosApi.usuariosDisponiveis).toHaveBeenCalledWith('p1', { escola_id: 'e1', q: 'Ana', limit: 20, offset: 0 });
  expect(onSuccess).toHaveBeenCalledWith(expect.objectContaining({ id: 'a1' }));
});

it('permite vincular uma conta na turma e depois matricular o aluno acadêmico', async () => {
  vi.mocked(turmasApi.listarAlunos).mockResolvedValue({ items: [], total: 0, limit: 200, offset: 0 });
  vi.mocked(turmasApi.buscarAlunosDisponiveis)
    .mockResolvedValueOnce([])
    .mockResolvedValue([{ aluno_id: 'a1', nome: 'Ana', numero_matricula: 'NX-2026-0000001' }]);
  vi.mocked(turmasApi.matricularAluno).mockResolvedValue();
  render(<TurmaAlunosPanel turma={{ id: 't1', polo_id: 'p1', escola_id: 'e1', nome: 'Turma A', total_alunos: 0 }} onClose={vi.fn()} />);
  await screen.findByText(/Nenhum aluno disponível/);
  fireEvent.click(screen.getByText('Vincular usuário aluno existente'));
  fireEvent.click(await screen.findByText('Ana Silva — ana@example.test'));
  fireEvent.change(screen.getByLabelText('Data de nascimento'), { target: { value: '2000-01-01' } });
  fireEvent.click(screen.getByText('Vincular aluno'));
  await screen.findByText('NX-2026-0000001');
  fireEvent.click(screen.getByRole('button', { name: 'Matricular' }));
  await waitFor(() => expect(turmasApi.matricularAluno).toHaveBeenCalledWith('t1', 'a1'));
});
