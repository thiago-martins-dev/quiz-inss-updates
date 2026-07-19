# Política de segurança da automação

O sistema detecta e prepara atualizações, mas nunca inventa interpretação jurídica nem altera silenciosamente conteúdo histórico.

- Nunca apaga questão, resumo, ID ou snapshot.
- Nunca reutiliza ID nem altera gabarito, banca, concurso, órgão, cargo, ano, caderno, origem ou enunciado.
- Questão anulada permanece histórica e inelegível.
- Questão pendente permanece inelegível.
- Referência inferida ou ambígua exige revisão.
- Fonte sem HTTPS oficial é bloqueada.
- Pacotes são JSON declarativo sem scripts, comandos, binários, APK, Dart ou JavaScript.
- Nenhum segredo ou credencial é armazenado.

`SAFE_AUTOMATIC` exige referência explícita, confiança máxima, norma ativa, dispositivo inequívoco e operação limitada a metadados, aviso de vigência ou desativação para estudo atual com histórico preservado. O pacote inclui `expectedCurrentState` sem gabarito e falha se o cliente futuro encontrar estado inesperado. `REVIEW_REQUIRED` fica em quarentena e abre ou atualiza Issue deduplicada. `BLOCKED` impede Release e manifesto e encerra o workflow com falha. A publicação não significa instalação: o cliente Flutter ainda não baixa nem aplica pacotes.
