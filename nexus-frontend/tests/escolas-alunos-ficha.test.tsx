// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation, useParams } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EscolasPage } from '@/features/polos_escolas/pages/EscolasPage';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { alunosApi } from '@/features/alunos/api';

const perfil = vi.hoisted(() => ({ nome: 'admin' }));

vi.mock('@/stores/authStore', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/stores/authStore')>();
  return { ...original, useAuthStore: () => ({ user: { perfil, polo_id: 'p1' } }) };
});

vi.mock('@/features/polos_escolas/api', () => ({
  polosEscolasApi: {
    listarEscolas: vi.fn(),
    listarPolos: vi.fn().mockResolvedValue({ items: [{ id: 'p1', nome: 'Polo Centro' }], total: 1 }),
    obterPolo: vi.fn().mockResolvedValue({ id: 'p1', nome: 'Polo Centro' }),
    obterEscola: vi.fn(),
    getResumoOperacionalEscola: vi.fn(),
    listarUsuariosVinculaveis: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}));

vi.mock('@/features/alunos/api', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/features/alunos/api')>();
  return { ...original, alunosApi: { ...original.alunosApi, listar: vi.fn() } };
});

const escola = { id: 'e1', nome: 'Escola Modelo', polo_id: 'p1', status: 'ativo', endereco: {} };
const resumo = {
  alunos: 1, aulas: 0, licencas_estoque: 0, licencas_alunos: 0, licencas_atribuidas: 0,
  licencas_movimentacoes: 0, pedidos_licencas: 0, pedidos_livros: 0, professores: 0, turmas: 0,
};

/** Ficha falsa: mostra qual rota abriu e o destino do "Voltar". */
const FichaSonda: React.FC = () => {
  const { id } = useParams();
  const location = useLocation();
  const voltar = (location.state as { voltar?: { to: string } } | null)?.voltar?.to;
  return <p>ficha {location.pathname} id {id} voltar {voltar}</p>;
};

const renderizar = (url: string) =>
  render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/admin/escolas" element={<EscolasPage />} />
        <Route path="/polo/escolas/gestao" element={<EscolasPage />} />
        <Route path="/admin/usuarios/:id" element={<FichaSonda />} />
        <Route path="/polo/alunos/:id/ficha" element={<FichaSonda />} />
      </Routes>
    </MemoryRouter>,
  );

const abrirListaDeAlunos = async () => {
  fireEvent.click(await screen.findByRole('button', { name: 'Detalhes' }));
  fireEvent.click(await screen.findByRole('button', { name: /Alunos/ }));
  return screen.findByRole('link', { name: 'Bruna Lima' });
};

beforeEach(() => {
  vi.clearAllMocks();
  perfil.nome = 'admin';
  vi.mocked(polosEscolasApi.listarEscolas).mockResolvedValue({ items: [escola], total: 1 });
  vi.mocked(polosEscolasApi.obterEscola).mockResolvedValue(escola);
  vi.mocked(polosEscolasApi.getResumoOperacionalEscola).mockResolvedValue(resumo);
  vi.mocked(alunosApi.listar).mockResolvedValue({
    items: [{ id: 'a1', usuario_id: 'u1', nome: 'Bruna Lima', email: 'bruna@example.test', numero_matricula: '2026001', status: 'ativo' }],
    total: 1,
  } as never);
});

afterEach(cleanup);

describe('EscolasPage → lista de alunos → ficha cadastral', () => {
  it('admin abre a ficha completa do usuário e volta para a escola com a lista', async () => {
    renderizar('/admin/escolas');
    const link = await abrirListaDeAlunos();
    expect(link.getAttribute('href')).toBe('/admin/usuarios/u1');

    fireEvent.click(screen.getByText('2026001'));
    expect(await screen.findByText('ficha /admin/usuarios/u1 id u1 voltar /admin/escolas?escola=e1&lista=alunos')).toBeTruthy();
  });

  it('polo abre a ficha somente leitura da própria área', async () => {
    perfil.nome = 'polo';
    renderizar('/polo/escolas/gestao');
    const link = await abrirListaDeAlunos();
    expect(link.getAttribute('href')).toBe('/polo/alunos/a1/ficha');

    fireEvent.click(link);
    expect(await screen.findByText('ficha /polo/alunos/a1/ficha id a1 voltar /polo/escolas/gestao?escola=e1&lista=alunos')).toBeTruthy();
  });

  it('ao voltar da ficha reabre a escola com a lista de alunos', async () => {
    renderizar('/admin/escolas?escola=e1&lista=alunos');
    expect(await screen.findByRole('link', { name: 'Bruna Lima' })).toBeTruthy();
    expect(polosEscolasApi.obterEscola).toHaveBeenCalledWith('e1');
    expect(alunosApi.listar).toHaveBeenCalledWith('p1', expect.objectContaining({ escola_id: 'e1' }));
  });
});
