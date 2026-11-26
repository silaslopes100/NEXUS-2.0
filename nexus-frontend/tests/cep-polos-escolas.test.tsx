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
    listarUsuariosVinculaveis: vi.fn().mockImplementation(({ perfil }) => Promise.resolve(perfil === 'escola'
      ? { items: [
          { id: 'secretaria', nome: 'Ana', sobrenome: 'Silva', email: 'ana@example.test', status: 'ativo' },
          { id: 'ocupado', nome: 'Ocupado', status: 'ativo', escola_id: 'outra' },
          { id: 'outro', nome: 'Outro', status: 'ativo', polo_id: 'p2' },
        ], total: 3 }
      : { items: [{ id: 'coord', nome: 'Coordenador' }], total: 1 })),
    listarPolos: vi.fn().mockResolvedValue({ items: [{ id: 'p1', nome: 'Polo teste', endereco: {}, status: 'ativo' }], total: 1 }),
    listarEscolas: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    criarPolo: vi.fn().mockResolvedValue({ id: 'p1' }),
    criarEscola: vi.fn().mockResolvedValue({ id: 'e1' }),
  },
}));

const addressResponse = {
  logradouro: 'Rua Teste', bairro: 'Centro', localidade: 'São Paulo', uf: 'SP',
};
const jsonResponse = (data: object) => ({ ok: true, json: async () => data });

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(addressResponse)));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

/** Opção "Polo teste" do formulário de cadastro (ignora o filtro de polo da listagem). */
async function opcaoPoloDoCadastro() {
  const options = await screen.findAllByRole('option', { name: 'Polo teste' });
  const doCadastro = options.find(
    (option) => option.parentElement?.getAttribute('aria-label') !== 'Filtrar por polo',
  );
  if (!doCadastro) throw new Error('select de polo do cadastro não encontrado');
  return doCadastro;
}

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
  render(<MemoryRouter><PolosEscolasPage /></MemoryRouter>);
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
  render(<MemoryRouter><PolosEscolasPage /></MemoryRouter>);
  fireEvent.click(screen.getByText('Novo polo'));
  fireEvent.change(screen.getByPlaceholderText('Nome da unidade'), { target: { value: 'Polo novo' } });
  fireEvent.change(screen.getByPlaceholderText('Cidade'), { target: { value: 'São Paulo' } });
  await screen.findByText(/Coordenador —/);
  fireEvent.change(screen.getByRole('listbox'), { target: { value: 'coord' } });
  fireEvent.click(screen.getByText('Salvar'));
  expect((await screen.findByRole('alert')).textContent).toContain('Usuário já é coordenador');
});

describe.each([
  ['polos e escolas', async () => {
    render(<MemoryRouter><PolosEscolasPage /></MemoryRouter>);
    fireEvent.click(screen.getByText('Nova escola'));
    fireEvent.change(screen.getByPlaceholderText('Nome da unidade'), { target: { value: 'Escola nova' } });
    fireEvent.change(screen.getByPlaceholderText('Cidade'), { target: { value: 'Recife' } });
  }],
  ['gestão de escolas', async () => {
    render(<MemoryRouter><EscolasPage /></MemoryRouter>);
    await screen.findByText('Cadastrar escola');
    fireEvent.click(screen.getByText('Cadastrar escola'));
    fireEvent.change(screen.getByPlaceholderText('Nome da escola'), { target: { value: 'Escola nova' } });
  }],
] as const)('cadastro de escola em %s', (_name, open) => {
  it('consulta usuários de escola e vincula o responsável selecionado', async () => {
    await open();
    const option = await opcaoPoloDoCadastro();
    fireEvent.change(option.parentElement!, { target: { value: 'p1' } });
    await screen.findByRole('option', { name: /Ana Silva/ });
    expect(vi.mocked(polosEscolasApi.listarUsuariosVinculaveis)).toHaveBeenCalledWith(
      expect.objectContaining({ perfil: 'escola' }),
    );
    expect((screen.getByRole('option', { name: /Ocupado/ }) as HTMLOptionElement).disabled).toBe(true);
    expect((screen.getByRole('option', { name: /Outro/ }) as HTMLOptionElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText('Usuário responsável da escola'), { target: { value: 'secretaria' } });
    fireEvent.change(screen.getByLabelText('Buscar usuário de escola'), { target: { value: 'Ana' } });
    await waitFor(() => expect(polosEscolasApi.listarUsuariosVinculaveis).toHaveBeenCalledWith(
      expect.objectContaining({ perfil: 'escola', q: 'Ana' }),
    ));
    fireEvent.click(screen.getByRole('button', { name: /^(Salvar|Cadastrar)$/ }));
    await waitFor(() => expect(polosEscolasApi.criarEscola).toHaveBeenCalledWith(
      'p1', expect.objectContaining({ nome: 'Escola nova', secretario_usuario_id: 'secretaria' }),
    ));
  });

  it('mantém a opção de criar um responsável novo', async () => {
    await open();
    const option = await opcaoPoloDoCadastro();
    fireEvent.change(option.parentElement!, { target: { value: 'p1' } });
    fireEvent.click(screen.getByLabelText('Criar usuário'));
    fireEvent.change(screen.getByPlaceholderText('Nome'), { target: { value: 'Secretária' } });
    fireEvent.change(screen.getByPlaceholderText('CPF'), { target: { value: '12345678900' } });
    fireEvent.change(screen.getByPlaceholderText('E-mail'), { target: { value: 'sec@example.test' } });
    fireEvent.change(screen.getByPlaceholderText('Senha inicial'), { target: { value: 'senha123' } });
    fireEvent.click(screen.getByRole('button', { name: /^(Salvar|Cadastrar)$/ }));
    await waitFor(() => expect(polosEscolasApi.criarEscola).toHaveBeenCalledWith(
      'p1', expect.objectContaining({ secretario_nome: 'Secretária', secretario_usuario_id: '' }),
    ));
  });
});

it('permite tentar novamente quando a consulta de usuários falha', async () => {
  vi.mocked(polosEscolasApi.listarUsuariosVinculaveis).mockRejectedValueOnce(new Error('rede'));
  render(<MemoryRouter><EscolasPage /></MemoryRouter>);
  fireEvent.click(screen.getByText('Cadastrar escola'));
  expect((await screen.findByRole('alert')).textContent).toContain('Não foi possível consultar os usuários');
  fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }));
  await screen.findByRole('option', { name: /Ana Silva/ });
});

describe.each([
  ['cadastro de polo', () => {
    render(<MemoryRouter><PolosEscolasPage /></MemoryRouter>);
    fireEvent.click(screen.getByText('Novo polo'));
  }, false],
  ['cadastro de escola no polo', () => {
    render(<MemoryRouter><PolosEscolasPage /></MemoryRouter>);
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
    if (!editing) {
      expect(field('Cep').compareDocumentPosition(field('Logradouro')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
    fireEvent.change(field('Cep'), { target: { value: '01000000' } });
    await waitFor(() => expect(field('Cidade').value).toBe('São Paulo'));
    expect(field('Estado').value).toBe('SP');
  });
});

describe('listagem de escolas', () => {
  it('mostra a coluna do polo e filtra por polo e por escolas sem polo', async () => {
    vi.mocked(polosEscolasApi.listarEscolas).mockResolvedValue({
      items: [
        { id: 'e1', polo_id: 'p1', polo_nome: 'Polo teste', nome: 'Escola Um', endereco: {}, status: 'ativo' },
        { id: 'e2', polo_id: null, polo_nome: null, nome: 'Escola Órfã', endereco: {}, status: 'ativo' },
      ],
      total: 2,
    });
    render(<MemoryRouter><EscolasPage /></MemoryRouter>);

    expect(await screen.findByRole('columnheader', { name: 'Polo' })).toBeTruthy();
    const linhaUm = (await screen.findByText('Escola Um')).closest('tr')!;
    expect(linhaUm.textContent).toContain('Polo teste');
    expect(screen.getByText('Escola Órfã').closest('tr')!.textContent).toContain('Sem polo');

    const filtro = screen.getByLabelText('Filtrar por polo');
    await screen.findAllByRole('option', { name: 'Polo teste' });
    fireEvent.change(filtro, { target: { value: 'p1' } });
    await waitFor(() => expect(polosEscolasApi.listarEscolas).toHaveBeenLastCalledWith(
      expect.objectContaining({ polo_id: 'p1', sem_polo: undefined, offset: 0 }),
    ));

    fireEvent.change(filtro, { target: { value: '__sem_polo__' } });
    await waitFor(() => expect(polosEscolasApi.listarEscolas).toHaveBeenLastCalledWith(
      expect.objectContaining({ polo_id: undefined, sem_polo: true }),
    ));
  });
});
