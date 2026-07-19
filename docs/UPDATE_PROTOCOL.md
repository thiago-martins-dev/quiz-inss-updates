# Protocolo de atualização de conteúdo

Este documento descreve o fluxo futuro; o aplicativo ainda não implementa este protocolo.

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
