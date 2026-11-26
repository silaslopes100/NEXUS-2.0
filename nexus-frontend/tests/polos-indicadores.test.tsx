// @vitest-environment jsdom
import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PolosEscolasPage } from '@/features/polos_escolas/pages/PolosEscolasPage';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import {
  formatarEndereco,
  rotasIndicadoresEscola,
  rotasIndicadoresPolo,
} from '@/features/polos_escolas/indicadores';

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({ user: { perfil: { nome: 'admin' } } }),
}));

const polo = {
  id: 'p1',
  nome: 'Polo Centro',
  status: 'ativo',
  endereco: { logradouro: 'Rua A', numero: '10', bairro: 'Centro', cidade: 'Campinas', estado: 'SP', cep: '13000-000' },
  coordenador_nome: 'Carla',
  coordenador_email: 'carla@example.test',
};
const poloInativo = { id: 'p2', nome: 'Polo Norte', status: 'inativo', endereco: { cidade: 'Recife', estado: 'PE' } };

vi.mock('@/features/polos_escolas/api', () => ({
  polosEscolasApi: {
    listarPolos: vi.fn(),
    obterPolo: vi.fn(),
    getResumoOperacionalPolo: vi.fn(),
    listarEscolasDoPolo: vi.fn(),
    getResumoOperacionalEscola: vi.fn(),
    listarUsuariosVinculaveis: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}));

const resumo = {
  escolas: 2, turmas: 3, professores: 4, alunos: 50, aulas: 7,
  licencas_estoque: 8, licencas_atribuidas: 9, licencas_movimentacoes: 10, pedidos_licencas: 1, pedidos_livros: 2,
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.mocked(polosEscolasApi.listarPolos).mockResolvedValue({ items: [polo, poloInativo], total: 2, limit: 200, offset: 0 });
  vi.mocked(polosEscolasApi.obterPolo).mockResolvedValue(polo);
  vi.mocked(polosEscolasApi.getResumoOperacionalPolo).mockResolvedValue(resumo);
  vi.mocked(polosEscolasApi.listarEscolasDoPolo).mockResolvedValue({ items: [], total: 0 });
});

afterEach(cleanup);

describe('rotas dos indicadores', () => {
  it('admin abre as telas administrativas filtradas pelo polo', () => {
    const rotas = rotasIndicadoresPolo('admin', 'p1');
    expect(rotas.escolas).toBe('/admin/escolas?polo_id=p1');
    expect(rotas.turmas).toBe('/admin/turmas-calendarios?polo_id=p1');
    expect(rotas.aulas).toBe('/admin/aulas?polo=p1');
    expect(rotas.pedidos_licencas).toBe('/admin/pedidos?polo_id=p1&tipo=licenca');
    expect(rotas.pedidos_livros).toBe('/admin/pedidos?polo_id=p1&tipo=livro');
  });

  it('perfil Polo usa as rotas /polo e não linka telas que não existem para ele', () => {
    const rotas = rotasIndicadoresPolo('polo', 'p1');
    expect(rotas.turmas).toBe('/polo/turmas');
    expect(rotas.licencas_estoque).toBe('/polo/licencas');
    expect(rotas.professores).toBeUndefined();
    expect(rotas.aulas).toBeUndefined();
  });

  it('escola filtra por polo e escola, e licenças abrem a gestão da escola', () => {
    const admin = rotasIndicadoresEscola('admin', { id: 'e1', polo_id: 'p1' });
    expect(admin.alunos).toBe('/admin/alunos?polo_id=p1&escola_id=e1');
    expect(admin.licencas_estoque).toBe('/admin/escolas/e1/licencas');
    expect(admin.pedidos_livros).toBe('/admin/pedidos?polo_id=p1&escola_id=e1&tipo=livro');

    const semPolo = rotasIndicadoresEscola('admin', { id: 'e1', polo_id: null });
    expect(semPolo.aulas).toBeUndefined();
    expect(semPolo.turmas).toBe('/admin/turmas-calendarios?escola_id=e1');

    expect(rotasIndicadoresEscola('polo', { id: 'e1', polo_id: 'p1' }).licencas_alunos).toBe('/polo/escolas/e1/licencas');
  });

  it('formata o endereço em uma linha, ignorando campos vazios', () => {
    expect(formatarEndereco(polo.endereco)).toBe('Rua A, 10 · Centro · Campinas/SP · CEP 13000-000');
    expect(formatarEndereco({})).toBe('');
  });
});

describe('PolosEscolasPage', () => {
  const renderizar = () => render(<MemoryRouter><PolosEscolasPage /></MemoryRouter>);

  it('carrega os polos ao abrir, sem precisar buscar', async () => {
    renderizar();
    expect(await screen.findByText('Polo Centro')).toBeTruthy();
    expect(polosEscolasApi.listarPolos).toHaveBeenCalledTimes(1);
    expect(screen.getByText('carla@example.test')).toBeTruthy();
  });

  it('filtra por status no cliente', async () => {
    renderizar();
    await screen.findByText('Polo Norte');
    fireEvent.change(screen.getByLabelText('Filtrar por status'), { target: { value: 'ativo' } });
    expect(screen.queryByText('Polo Norte')).toBeNull();
    expect(screen.getByText('Polo Centro')).toBeTruthy();
  });

  it('alterna para tabela e lembra a escolha', async () => {
    renderizar();
    await screen.findByText('Polo Centro');
    fireEvent.click(screen.getByRole('button', { name: /Tabela/ }));
    expect(screen.getByRole('table')).toBeTruthy();
    expect(localStorage.getItem('nexus.polos.visualizacao')).toBe('tabela');
  });

  it('abre o detalhe e os indicadores levam às telas filtradas', async () => {
    renderizar();
    fireEvent.click(await screen.findByRole('button', { name: 'Abrir polo Polo Centro' }));
    await waitFor(() => expect(polosEscolasApi.getResumoOperacionalPolo).toHaveBeenCalledWith('p1'));
    const turmas = await screen.findByRole('link', { name: 'Turmas: 3, abrir' });
    expect(turmas.getAttribute('href')).toBe('/admin/turmas-calendarios?polo_id=p1');
    expect(screen.getByRole('link', { name: 'De livros: 2, abrir' }).getAttribute('href'))
      .toBe('/admin/pedidos?polo_id=p1&tipo=livro');
    expect(screen.getByText('Rua A, 10 · Centro · Campinas/SP · CEP 13000-000')).toBeTruthy();
  });

  it('reabre o detalhe quando o polo vem na URL', async () => {
    render(<MemoryRouter initialEntries={['/admin/polos-escolas?polo=p1']}><PolosEscolasPage /></MemoryRouter>);
    expect(await screen.findByRole('link', { name: 'Escolas: 2, abrir' })).toBeTruthy();
    expect(polosEscolasApi.obterPolo).toHaveBeenCalledWith('p1');
  });
});
