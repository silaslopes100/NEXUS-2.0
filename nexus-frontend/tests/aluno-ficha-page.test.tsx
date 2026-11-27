// @vitest-environment jsdom
import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AlunoFichaPage } from '@/features/alunos/pages/AlunoFichaPage';
import { alunosGestaoApi } from '@/features/alunos/api';

vi.mock('@/features/alunos/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/features/alunos/api')>();
  return { ...original, alunosGestaoApi: { ficha: vi.fn() } };
});

const ficha = {
  id: 'u1',
  nome: 'Bruna',
  sobrenome: 'Lima',
  email: 'bruna@example.test',
  cpf: '12345678901',
  celular: '11987654321',
  foto_url: null,
  status: 'ativo',
  permissoes: [],
  dados: {
    cidade: 'Campinas',
    uf: 'SP',
    logradouro: 'Rua A',
    numero: '10',
    contato_emergencia_nome: 'Maria Lima',
    contato_emergencia_telefone: '11911112222',
  },
  aluno: {
    id: 'a1',
    usuario_id: 'u1',
    numero_matricula: '2026001',
    modalidade: 'polo',
    status: 'ativo',
    polo_nome: 'Polo Centro',
    escola_nome: 'Escola Modelo',
  },
};

const renderizar = (url = '/polo/alunos/a1/ficha') =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/polo/alunos/:alunoId/ficha" element={<AlunoFichaPage />} />
        <Route path="/escola/alunos/:alunoId/ficha" element={<AlunoFichaPage />} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(cleanup);

describe('AlunoFichaPage (Polo/Escola)', () => {
  it('mostra a ficha do aluno sem permitir edição', async () => {
    vi.mocked(alunosGestaoApi.ficha).mockResolvedValue(ficha as never);
    renderizar();

    expect(await screen.findByRole('heading', { name: 'Bruna Lima' })).toBeTruthy();
    expect(alunosGestaoApi.ficha).toHaveBeenCalledWith('a1');
    expect(screen.getByText('Somente leitura')).toBeTruthy();
    expect(screen.getByText('Maria Lima')).toBeTruthy();
    expect(screen.getByText('Polo Centro')).toBeTruthy();
    expect(screen.getByText('2026001')).toBeTruthy();
    expect(screen.queryByRole('button', { name: /Editar/ })).toBeNull();
    expect(screen.getByRole('button', { name: /Voltar para alunos/ })).toBeTruthy();
  });

  it('mostra o erro do backend para aluno fora da unidade', async () => {
    vi.mocked(alunosGestaoApi.ficha).mockRejectedValue({ response: { data: { detail: 'Aluno fora da sua unidade' } } });
    renderizar('/escola/alunos/a9/ficha');

    expect((await screen.findByRole('alert')).textContent).toContain('Aluno fora da sua unidade');
  });
});
