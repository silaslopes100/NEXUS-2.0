import { useEffect, useRef, useState } from 'react';
import { formatCep, onlyDigits } from '@/features/alunos/profileSchema';
import { lookupAddressByCep } from '@/features/alunos/viacep';
import { EnderecoCompleto } from '@/types/polos';

type AddressUpdate = (update: (address: EnderecoCompleto) => EnderecoCompleto) => void;
type AddressField = keyof EnderecoCompleto;
type LookupStatus = 'idle' | 'loading' | 'success' | 'error';

export function useCepAddress(updateAddress: AddressUpdate, formKey: string | null) {
  const updateRef = useRef(updateAddress);
  updateRef.current = updateAddress;
  const controller = useRef<AbortController | null>(null);
  const requestId = useRef(0);
  const revisions = useRef<Partial<Record<AddressField, number>>>({});
  const [lookup, setLookup] = useState<{ status: LookupStatus; message: string }>({
    status: 'idle',
    message: '',
  });

  useEffect(() => {
    setLookup({ status: 'idle', message: '' });
    return () => {
      requestId.current += 1;
      controller.current?.abort();
      controller.current = null;
    };
  }, [formKey]);

  const changeAddress = (field: AddressField, rawValue: string) => {
    const value = field === 'cep' ? formatCep(rawValue) : rawValue;
    revisions.current[field] = (revisions.current[field] || 0) + 1;
    updateRef.current((address) => ({ ...address, [field]: value }));
    if (field !== 'cep') return;

    const id = ++requestId.current;
    controller.current?.abort();
    controller.current = null;
    setLookup({ status: 'idle', message: '' });
    const cep = onlyDigits(value);
    if (cep.length !== 8) return;

    const version = { ...revisions.current };
    const currentController = new AbortController();
    controller.current = currentController;
    setLookup({ status: 'loading', message: 'Consultando CEP...' });
    void lookupAddressByCep(cep, currentController.signal)
      .then((result) => {
        if (currentController.signal.aborted || id !== requestId.current) return;
        const fields = {
          logradouro: result.logradouro,
          bairro: result.bairro,
          cidade: result.cidade,
          estado: result.uf,
        };
        updateRef.current((address) => {
          if (onlyDigits(address.cep || '') !== cep) return address;
          const updated = { ...address };
          for (const key of Object.keys(fields) as Array<keyof typeof fields>) {
            if (revisions.current[key] === version[key]) updated[key] = fields[key];
          }
          return updated;
        });
        setLookup({ status: 'success', message: 'Endereço consultado. Confira os dados e informe número e complemento.' });
      })
      .catch((error: unknown) => {
        if (currentController.signal.aborted || id !== requestId.current) return;
        setLookup({
          status: 'error',
          message: error instanceof Error ? error.message : 'Não foi possível consultar o CEP. Preencha o endereço manualmente.',
        });
      })
      .finally(() => {
        if (id === requestId.current) controller.current = null;
      });
  };

  return { changeAddress, lookup };
}
