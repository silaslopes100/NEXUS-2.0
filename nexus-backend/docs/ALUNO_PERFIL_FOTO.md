# Foto de perfil do aluno

O perfil do aluno aceita uma única foto enviada por `POST /alunos/meu-perfil/foto`
como formulário multipart no campo `foto`. São aceitos JPEG, PNG e WebP até 4 MB.
O backend valida e reprocessa a imagem, normaliza a orientação, redimensiona para
no máximo 1024 × 1024 e remove metadados embutidos.

O banco mantém somente o nome gerado do arquivo em `usuarios.foto_url`; a leitura
é feita por `GET /alunos/meu-perfil/foto` no perfil do aluno, ou por
`GET /auth/me/foto` nos avatares compartilhados do layout. Ambos exigem
autenticação e retornam somente a foto do próprio usuário.
Em desenvolvimento, os arquivos ficam em `nexus-backend/uploads/profile_photos/`.
Em produção no Vercel, são armazenados em um Blob privado conectado ao projeto da
API. O Blob deve estar configurado antes de receber uploads em produção.
