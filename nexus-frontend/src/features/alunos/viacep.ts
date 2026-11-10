export interface ViaCepAddress {
  logradouro: string;
  bairro: string;
  cidade: string;
  uf: string;
}

interface ViaCepResponse {
  erro?: boolean;
  logradouro: string;
  bairro: string;
  localidade: string;
  uf: string;
}

function isViaCepResponse(value: unknown): value is ViaCepResponse {
  if (!value || typeof value !== 'object') return false;
  const response = value as Record<string, unknown>;
  return (
    typeof response.logradouro === 'string' &&
    typeof response.bairro === 'string' &&
    typeof response.localidade === 'string' &&
    typeof response.uf === 'string'
  );
}

export async function lookupAddressByCep(
  cep: string,
  signal: AbortSignal
): Promise<ViaCepAddress> {
  if (!/^\d{8}$/.test(cep)) {
    throw new Error('Informe um CEP com 8 dígitos.');
  }

  let response: Response;
  try {
    response = await fetch(`https://viacep.com.br/ws/${cep}/json/`, { signal });
  } catch (error) {
    if (signal.aborted) throw error;
    throw new Error('Não foi possível consultar o ViaCEP. Preencha o endereço manualmente.');
  }

  if (!response.ok) {
    throw new Error('O ViaCEP está indisponível. Preencha o endereço manualmente.');
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new Error('O ViaCEP retornou uma resposta inválida. Preencha o endereço manualmente.');
  }

  if (data && typeof data === 'object' && 'erro' in data && data.erro === true) {
    throw new Error('CEP não encontrado. Confira o número ou preencha o endereço manualmente.');
  }
  if (!isViaCepResponse(data)) {
    throw new Error('O ViaCEP retornou uma resposta inválida. Preencha o endereço manualmente.');
  }

  return {
    logradouro: data.logradouro,
    bairro: data.bairro,
    cidade: data.localidade,
    uf: data.uf,
  };
}
