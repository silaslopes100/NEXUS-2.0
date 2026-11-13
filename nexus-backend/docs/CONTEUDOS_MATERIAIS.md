# Conteudos e materiais academicos

Docentes podem cadastrar e editar links HTTP/HTTPS ou arquivos em conteudos
disciplinares e materiais vinculados a uma turma. Conteudos disciplinares ficam
visiveis aos alunos matriculados nos cursos associados; materiais de turma sao
restritos aos docentes atualmente vinculados a turma.

Uploads aceitam PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX e imagens JPEG, PNG ou WebP,
com limite de 4 MiB por arquivo. A API valida extensao, MIME, assinatura e,
quando aplicavel, a estrutura do documento. Downloads exigem autenticacao e
autorizacao para o conteudo ou vinculo academico correspondente.

A migracao `scripts/migrations/009_conteudos_materiais_arquivos.sql` deve ser
aplicada antes da implantacao. Em desenvolvimento, os arquivos ficam em
`uploads/academic_materials/`. Em producao no Vercel, a API usa Vercel Blob
privado; configure o Blob e suas credenciais no projeto da API antes de habilitar
uploads. As chaves internas de armazenamento nao sao expostas pela API.

Conteudos disciplinares podem ser abertos no visualizador integrado da plataforma.
PDFs e imagens enviados sao exibidos diretamente pelo navegador; documentos
Office permanecem disponiveis para download, pois a API serverless do Vercel nao
inclui um conversor local de Office para PDF. Links externos sao incorporados
quando o provedor permite; caso contrario, o visualizador oferece uma alternativa
para abrir o link externamente.
