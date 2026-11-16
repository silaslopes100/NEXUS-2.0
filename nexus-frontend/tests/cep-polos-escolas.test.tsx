// @vitest-environment jsdom
import React, { useState } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PoloEditModal } from '@/features/polos_escolas/components/PoloEditModal';
import { EscolaEditModal } from '@/features/polos_escolas/components/EscolaEditModal';
import { PolosEscolasPage } from '@/features/polos_escolas/pages/PolosEscolasPage';
import { EscolasPage } from '@/features/polos_escolas/pages/EscolasPage';
import { useCepAddress } from '@/features/polos_escolas/useCepAddress';
import { polosEscolasApi } from '@/features/polos_escolas/api';
import { EnderecoCompleto } from '@/types/polos';

vi.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({ user: { perfil: { nome: 'admin' } } }),
}));

vi.mock('@/features/polos_escolas/api', () => ({
  polosEscolasApi: {
    listarUsuariosVinculaveis: vi.fn().mockResolvedValue({ items: [{ id: 'coord', nome: 'Coordenador' }], total: 1 }),
    listarPolos: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    listarEscolas: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    criarPolo: vi.fn().mockResolvedValue({ id: 'p1' }),
  },
}));

const addressResponse = {
  logradouro: 'Rua Teste', bairro: 'Centro', localidade: 'São Paulo', uf: 'SP',
};
const jsonResponse = (data: object) => ({ ok: true, json: async () => data });

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(addressResponse)));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function Harness() {
  const [address, setAddress] = useState<EnderecoCompleto>({ numero: '42', complemento: 'Sala' });
  const { changeAddress, lookup } = useCepAddress(setAddress, 'test');
  return (
    <>
      {(['cep', 'logradouro', 'bairro', 'cidade', 'estado', 'numero', 'complemento'] as const).map((field) => (
        <input key={field} aria-label={field} value={address[field] || ''} onChange={(e) => changeAddress(field, e.target.value)} />
      ))}
      <span role="status">{lookup.message}</span>
    </>
  );
}

describe('consulta de CEP', () => {
  it('consulta somente CEP completo e mantém número e complemento', async () => {
    render(<Harness />);
    fireEvent.change(screen.getByLabelText('cep'), { target: { value: '01000' } });
    expect(fetch).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('cep'), { target: { value: '01000000' } });
    await waitFor(() => expect((screen.getByLabelText('logradouro') as HTMLInputElement).value).toBe('Rua Teste'));
    expect((screen.getByLabelText('cep') as HTMLInputElement).value).toBe('01000-000');
    expect((screen.getByLabelText('estado') as HTMLInputElement).value).toBe('SP');
    expect((screen.getByLabelText('numero') as HTMLInputElement).value).toBe('42');
    expect((screen.getByLabelText('complemento') as HTMLInputElement).value).toBe('Sala');
  });

  it('preserva edição manual e ignora resposta obsoleta', async () => {
    let resolveFirst!: (response: ReturnType<typeof jsonResponse>) => void;
    let resolveSecond!: (response: ReturnType<typeof jsonResponse>) => void;
    vi.mocked(fetch)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve as typeof resolveFirst; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveSecond = resolve as typeof resolveSecond; }));
    render(<Harness />);
    fireEvent.change(screen.getByLabelText('cep'), { target: { value: '01000000' } });
    fireEvent.change(screen.getByLabelText('cep'), { target: { value: '02000000' } });
    fireEvent.change(screen.getByLabelText('logradouro'), { target: { value: 'Digitado' } });
    await act(async () => resolveSecond(jsonResponse(addressResponse)));
    await act(async () => resolveFirst(jsonResponse({ ...addressResponse, bairro: 'Antigo' })));
    expect((screen.getByLabelText('logradouro') as HTMLInputElement).value).toBe('Digitado');
    expect((screen.getByLabelText('bairro') as HTMLInputElement).value).toBe('Centro');
  });

  it('informa CEP não encontrado e mantém entrada manual', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ erro: true }) as Response);
    render(<Harness />);
    fireEvent.change(screen.getByLabelText('cep'), { target: { value: '01000000' } });
    await waitFor(() => expect(screen.getByRole('status').textContent).toContain('CEP não encontrado'));
    fireEvent.change(screen.getByLabelText('cidade'), { target: { value: 'Manual' } });
    expect((screen.getByLabelText('cidade') as HTMLInputElement).value).toBe('Manual');
  });

  it('avisa quando a consulta falha e cancela ao desmontar', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new Error('rede'));
    const { unmount } = render(<Harness />);
    fireEvent.change(screen.getByLabelText('cep'), { target: { value: '01000000' } });
    await waitFor(() => expect(screen.getByRole('status').textContent).toContain('manualmente'));
    vi.mocked(fetch).mockImplementationOnce(() => new Promise(() => {}));
    fireEvent.change(screen.getByLabelText('cep'), { target: { value: '02000000' } });
    const signal = vi.mocked(fetch).mock.calls.at(-1)?.[1]?.signal;
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});

it('cria polo com usuário existente e atualiza a listagem', async () => {
  render(<PolosEscolasPage />);
  fireEvent.click(screen.getByText('Novo polo'));
  fireEvent.change(screen.getByPlaceholderText('Nome da unidade'), { target: { value: 'Polo novo' } });
  fireEvent.change(screen.getByPlaceholderText('Cidade'), { target: { value: 'São Paulo' } });
  await screen.findByText(/Coordenador —/);
  fireEvent.change(screen.getByRole('listbox'), { target: { value: 'coord' } });
  fireEvent.click(screen.getByText('Salvar'));
  await waitFor(() => expect(polosEscolasApi.criarPolo).toHaveBeenCalledWith(
    expect.objectContaining({ nome: 'Polo novo', coordenador_usuario_id: 'coord' }),
  ));
  await waitFor(() => expect(polosEscolasApi.listarPolos).toHaveBeenCalled());
  expect(screen.getByText('Polo cadastrado e coordenador vinculado com sucesso.')).toBeTruthy();
});

it('mostra erro de criação dentro do formulário', async () => {
  vi.mocked(polosEscolasApi.criarPolo).mockRejectedValueOnce({
    response: { data: { detail: 'Usuário já é coordenador de outro polo' } },
  });
  render(<PolosEscolasPage />);
  fireEvent.click(screen.getByText('Novo polo'));
  fireEvent.change(screen.getByPlaceholderText('Nome da unidade'), { target: { value: 'Polo novo' } });
  fireEvent.change(screen.getByPlaceholderText('Cidade'), { target: { value: 'São Paulo' } });
  await screen.findByText(/Coordenador —/);
  fireEvent.change(screen.getByRole('listbox'), { target: { value: 'coord' } });
  fireEvent.click(screen.getByText('Salvar'));
  expect((await screen.findByRole('alert')).textContent).toContain('Usuário já é coordenador');
});

describe.each([
  ['cadastro de polo', () => {
    render(<PolosEscolasPage />);
    fireEvent.click(screen.getByText('Novo polo'));
  }, false],
  ['cadastro de escola no polo', () => {
    render(<PolosEscolasPage />);
    fireEvent.click(screen.getByText('Nova escola'));
  }, false],
  ['cadastro na página de escolas', () => {
    render(<MemoryRouter><EscolasPage /></MemoryRouter>);
    fireEvent.click(screen.getByText('Cadastrar escola'));
  }, false],
  ['edição de polo', () => {
    render(<PoloEditModal polo={{ id: 'p1', nome: 'Polo', endereco: {}, status: 'ativo' }} onClose={() => {}} onSuccess={() => {}} />);
  }, true],
  ['edição de escola', () => {
    render(<EscolaEditModal escola={{ id: 'e1', polo_id: 'p1', nome: 'Escola', endereco: {}, status: 'ativo' }} polos={[]} onClose={() => {}} onSuccess={() => {}} />);
  }, true],
] as const)('%s', (_name, open, editing) => {
  it('preenche o endereço ao informar o CEP', async () => {
    open();
    const field = (name: string): HTMLInputElement => {
      if (!editing) return screen.getByPlaceholderText(name) as HTMLInputElement;
      const label = Array.from(document.querySelectorAll('label')).find((item) => item.textContent?.toLowerCase() === name.toLowerCase());
      const input = label?.parentElement?.querySelector('input');
      if (!input) throw new Error(`Campo ${name} não encontrado`);
      return input;
    };
    expect(fetch).not.toHaveBeenCalled();
    fireEvent.change(field('Cep'), { target: { value: '01000000' } });
    await waitFor(() => expect(field('Cidade').value).toBe('São Paulo'));
    expect(field('Estado').value).toBe('SP');
  });
});
