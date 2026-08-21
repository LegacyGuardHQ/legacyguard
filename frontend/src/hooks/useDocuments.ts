import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createDocument, fetchDocuments, uploadDocument } from '../api/documents';

const documentsQueryKey = ['documents'] as const;

export function useDocuments() {
  return useQuery({ queryKey: documentsQueryKey, queryFn: fetchDocuments });
}

export function useCreateDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createDocument,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: documentsQueryKey });
    },
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ documentId, file }: { documentId: string; file: File }) => uploadDocument(documentId, file),
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: documentsQueryKey });
    },
  });
}
