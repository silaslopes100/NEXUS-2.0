# Foto de perfil do aluno

O perfil do aluno aceita uma única foto enviada por `POST /alunos/meu-perfil/foto`
como formulário multipart no campo `foto`. São aceitos JPEG, PNG e WebP até 5 MB.
O backend valida e reprocessa a imagem, normaliza a orientação, redimensiona para
no máximo 1024 × 1024 e remove metadados embutidos.

A foto é armazenada em `nexus-backend/uploads/profile_photos/`. O banco mantém
somente o nome gerado do arquivo em `usuarios.foto_url`; a leitura é feita por
`GET /alunos/meu-perfil/foto` e exige autenticação do próprio aluno. O diretório
é ignorado pelo Git e deve ser persistido entre reinicializações e incluído nos
backups da instalação. Em implantações com mais de uma instância, o diretório
precisa ser compartilhado entre instâncias ou substituído por storage comum.
