# Protocolo de atualização de conteúdo

Este documento descreve o fluxo futuro; o aplicativo ainda não implementa este protocolo.

## Publicação no servidor

O monitor consulta fontes diariamente, enquanto o aplicativo continuará consultando o manifesto em três janelas mensais. Uma mudança integralmente `SAFE_AUTOMATIC` gera um JSON UTF-8 não executável, com precondições, chaves idempotentes, hash lógico das operações e versão patch. A Release é criada e verificada antes de `manifest.json`; SHA-256 integral e tamanho ficam no manifesto. Se a atualização do manifesto falhar, a Release criada pela mesma execução é removida ou uma Issue operacional deve registrar a falha.

O manifesto mantém até as dez versões mais recentes, ordenadas semanticamente e sem duplicidades. `no_changes`, `REVIEW_REQUIRED` e `BLOCKED` não incrementam versão. Artifacts operacionais e timestamps não geram commit.

## Fluxo transacional previsto

1. O aplicativo consulta `manifest.json`.
2. Compara `contentVersion` com a versão instalada.
3. Verifica `minimumAppVersion`.
4. Apresenta a atualização disponível.
5. Baixa o pacote para um arquivo temporário.
6. Confirma o tamanho recebido.
7. Calcula o SHA-256 localmente.
8. Compara o hash com o manifesto.
9. Valida o JSON e seu esquema.
10. Faz backup do conteúdo atual.
11. Abre uma transação local.
12. Aplica as operações idempotentes.
13. Registra a versão instalada.
14. Finaliza a transação.
15. Remove arquivos temporários.
16. Em qualquer falha, executa rollback e restaura o backup.

## Regras operacionais e de segurança

- A verificação automática ocorrerá no máximo uma vez a cada 24 horas.
- Haverá um botão manual **Verificar atualizações**.
- Poderão existir futuramente atualizações obrigatórias e canais `stable` e `beta`.
- Nenhum pacote poderá baixar ou executar código, scripts ou comandos.
- O aplicativo não armazenará token do GitHub.
- Questões anuladas não serão apagadas: permanecerão no histórico com seu estado.
- Novas questões deverão receber IDs novos e estáveis.
- A origem oficial de cada conteúdo deverá ser preservada.
- Todas as operações deverão ser idempotentes e seguras para repetição.
- A validação detalhada dos campos das questões será definida somente após o mapeamento integral do modelo atual do aplicativo.
