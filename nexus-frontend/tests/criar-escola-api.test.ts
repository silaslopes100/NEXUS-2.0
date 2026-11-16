import { beforeEach, expect, it, vi } from 'vitest';
import { polosEscolasApi } from '@/features/polos_escolas/api';

const { post } = vi.hoisted(() => ({ post: vi.fn().mockResolvedValue({ data: {} }) }));
vi.mock('@/api/client', () => ({ apiClient: { post } }));

beforeEach(() => post.mockClear());

const form = {
  polo_id: 'p1',
  nome: 'Escola',
  secretario_nome: 'Nome anterior',
  secretario_cpf: '12345678900',
  secretario_email: 'nome@example.test',
  secretario_senha: 'senha-antiga',
};

it('envia apenas o ID ao vincular um usuário existente', async () => {
  await polosEscolasApi.criarEscola('p1', { ...form, secretario_usuario_id: 'u1' });
  expect(post).toHaveBeenCalledWith('/polos/p1/escolas', { nome: 'Escola', secretario_usuario_id: 'u1' });
});

it('continua enviando os dados ao criar um secretário', async () => {
  await polosEscolasApi.criarEscola('p1', form);
  expect(post).toHaveBeenCalledWith('/polos/p1/escolas', {
    nome: 'Escola',
    secretario_nome: form.secretario_nome,
    secretario_cpf: form.secretario_cpf,
    secretario_email: form.secretario_email,
    secretario_senha: form.secretario_senha,
  });
});
