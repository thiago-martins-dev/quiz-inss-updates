# Monitor Legislativo Automático

O monitor diário consulta fontes oficiais às 09:37 UTC. Esse calendário é independente do cliente Flutter, que consulta o manifesto em três janelas mensais. Nesta etapa nenhum pacote chega aos celulares.

## Banco e dependências

`build_legal_dependencies.py` reconstrói exclusivamente as listas concatenadas por `BancoQuestoes.questoes`: 707 questões de produção, 707 IDs únicos, 696 aptas, oito anuladas e três pendentes. O índice guarda somente IDs, localização, norma, dispositivo e flags de segurança. Enunciados, explicações e gabaritos não são copiados.

O repositório do aplicativo é privado. Por isso, o índice é reconstruído localmente, em modo somente leitura, por uma pessoa com acesso ao aplicativo, revisado e versionado neste repositório. O workflow valida a cobertura, a unicidade, a origem e os vínculos do índice já versionado; ele não usa segredo personalizado nem tenta acessar o repositório privado. Uma mudança no banco faz o gerador falhar até que o índice seja reconstruído e revisado.

Vínculos explícitos são criados apenas quando norma e artigo são inequívocos. O catálogo inicial ativo contém Constituição Federal, Lei nº 8.212/1991, Lei nº 8.213/1991 e Decreto nº 3.048/1999. Referências ausentes ou ambíguas permanecem em `unresolved`.

## Coleta, baseline e comparação

A coleta exige HTTPS oficial, User-Agent identificável, timeout, limite de 8 MiB e no máximo três tentativas com backoff limitado. INLABS permanece desativado por autenticação. Os textos consolidados iniciais vêm das páginas oficiais “Texto Atualizado” da Câmara dos Deputados; o coletor remove apenas marcação HTML técnica, exige um marcador inequívoco por norma e bloqueia conteúdo incompatível. O Planalto permanece no registro oficial, mas não é usado no baseline porque reinicia conexões originadas nos runners do GitHub Actions.

O primeiro conteúdo válido vira baseline versionada por SHA-256 e não gera mudança, Issue ou pacote. Execuções futuras comparam documento e dispositivos. Whitespace, quebras e marcação técnica são normalizados; diferenças jurídicas não são descartadas.

## Impacto, Issues e artifacts

Mudanças são cruzadas com o índice. Revisões usam chave estável `normId + dispositivo + hash` em marcador invisível para atualizar uma única Issue. Apenas impactos integralmente `SAFE_AUTOMATIC` podem produzir pacote candidato como artifact. Publicação, Release e atualização de `manifest.json` permanecem desativadas.

O bot pode persistir somente `snapshots/`, `state/` e `impact/latest_report.json`, sem commit vazio e sem force push.
