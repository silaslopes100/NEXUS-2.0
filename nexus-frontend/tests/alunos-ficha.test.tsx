// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AlunosPage } from '@/features/alunos/pages/AlunosPage';
import { alunosGestaoApi } from '@/features/alunos/api';

const perfil = vi.hoisted(() => ({ nome: 'admin' }));

vi.mock('@/stores/authStore', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/stores/authStore')>();
  return { ...original, useAuthStore: () => ({ user: { perfil, polo_id: 'p1' } }) };
});

vi.mock('@/features/alunos/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/features/alunos/api')>();
  return {
    ...original,
    alunosApi: {
      listarPolos: vi.fn().mockResolvedValue([{ id: 'p1', nome: 'Polo Centro' }]),
      listarEscolas: vi.fn().mockResolvedValue([]),
    },
    alunosGestaoApi: {
      listar: vi.fn(),
      confirmarChurn: vi.fn(),
      academico: vi.fn().mockResolvedValue({ aluno_id: 'a1', aluno_nome: 'Bruna Lima', cursos: [] }),
    },
  };
});

const aluno = {
  id: 'a1',
  usuario_id: 'u1',
  numero_matricula: '2026001',
  nome: 'Bruna Lima',
  email: 'bruna@example.test',
  modalidade: 'polo',
  status: 'ativo',
  turmas: [],
  percentual_presenca: 90,
  ultimo_acesso_em: null,
  disciplinas_em_curso: 0,
  observacoes: [],
};

/** Ficha falsa: mostra o usuário aberto e o destino do "Voltar" recebido. */
const FichaSonda: React.FC = () => {
  const { usuarioId } = useParams();
  const location = useLocation();
  const voltar = (location.state as { voltar?: { to: string } } | null)?.voltar?.to;
  return <p>ficha {usuarioId} voltar {voltar}</p>;
};

const renderizar = (url = '/admin/alunos') =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/admin/alunos" element={<AlunosPage />} />
        <Route path="/polo/alunos" element={<AlunosPage />} />
        <Route path="/escola/alunos" element={<AlunosPage />} />
        <Route path="/admin/usuarios/:usuarioId" element={<FichaSonda />} />
        <Route path="/polo/alunos/:usuarioId/ficha" element={<FichaSonda />} />
        <Route path="/escola/alunos/:usuarioId/ficha" element={<FichaSonda />} />
      </Routes>
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  perfil.nome = 'admin';
  vi.mocked(alunosGestaoApi.listar).mockResolvedValue({ items: [aluno], total: 1, limit: 20, offset: 0 });
});

afterEach(cleanup);

describe('AlunosPage → ficha cadastral', () => {
  it('clicar na linha do aluno abre a ficha do usuário', async () => {
    renderizar();
    fireEvent.click(await screen.findByText('2026001'));
    expect(await screen.findByText(/ficha u1/)).toBeTruthy();
  });

  it('o nome do aluno é um link para a ficha e o "Voltar" preserva os filtros', async () => {
    renderizar('/admin/alunos?polo_id=p1&q=bruna');
    const link = await screen.findByRole('link', { name: 'Bruna Lima' });
    expect(link.getAttribute('href')).toBe('/admin/usuarios/u1');
    fireEvent.click(link);
    expect(await screen.findByText('ficha u1 voltar /admin/alunos?polo_id=p1&q=bruna')).toBeTruthy();
  });

  it('botões da linha não abrem a ficha', async () => {
    renderizar();
    await screen.findByText('Bruna Lima');
    fireEvent.click(screen.getByRole('button', { name: 'Abrir boletim de Bruna Lima' }));
    expect(screen.queryByText(/ficha u1/)).toBeNull();
  });

  it.each([
    ['polo', '/polo/alunos/a1/ficha'],
    ['escola', '/escola/alunos/a1/ficha'],
  ])('perfil %s abre a ficha somente leitura da própria área', async (nome, rota) => {
    perfil.nome = nome;
    renderizar(`/${nome}/alunos`);
    const link = await screen.findByRole('link', { name: 'Bruna Lima' });
    expect(link.getAttribute('href')).toBe(rota);
    fireEvent.click(screen.getByText('2026001'));
    expect(await screen.findByText(`ficha a1 voltar /${nome}/alunos`)).toBeTruthy();
  });

  it('perfil sem área de ficha não vê o link', async () => {
    perfil.nome = 'professor';
    renderizar('/polo/alunos');
    await screen.findByText('Bruna Lima');
    expect(screen.queryByRole('link', { name: 'Bruna Lima' })).toBeNull();
  });
});
