# Política de segurança da automação

O sistema detecta e prepara atualizações, mas nunca inventa interpretação jurídica nem altera silenciosamente conteúdo histórico.

- Nunca apaga questão, resumo, ID ou snapshot.
- Nunca reutiliza ID nem altera gabarito, banca, concurso, órgão, cargo, ano, caderno, origem ou enunciado.
- Questão anulada permanece histórica e inelegível.
- Questão pendente permanece inelegível.
- Referência inferida ou ambígua exige revisão.
- Fonte sem HTTPS oficial é bloqueada.
- Pacote candidato não é Release, não altera `manifest.json` e não fica acessível ao aplicativo.
- Nenhum segredo ou credencial é armazenado.

`SAFE_AUTOMATIC` exige referência explícita, confiança máxima, norma ativa, dispositivo inequívoco e operação limitada a metadados, aviso de vigência ou desativação para estudo atual com histórico preservado. `REVIEW_REQUIRED` abre ou atualiza uma Issue deduplicada. `BLOCKED` encerra o workflow.
