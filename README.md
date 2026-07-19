# Quiz INSS Updates

Repositório público usado pela **TFM Software** para distribuir atualizações de conteúdo do Quiz INSS Premium.

Este repositório não contém o código-fonte principal do aplicativo. O código principal está no repositório [`quiz-inss-app`](https://github.com/thiago-martins-dev/quiz-inss-app). O manifesto público previsto está disponível em:

`https://raw.githubusercontent.com/thiago-martins-dev/quiz-inss-updates/main/manifest.json`

## Funcionamento previsto

Os pacotes futuros serão publicados em GitHub Releases. Antes de qualquer download, o aplicativo verificará o manifesto, a compatibilidade de versão e os metadados. Cada pacote será validado por tamanho e SHA-256 e aplicado com backup e transação; qualquer falha deverá provocar rollback.

Nenhum token será embutido no aplicativo. Este sistema não distribuirá atualizações executáveis, APKs ou código Dart. Ele servirá somente para conteúdo declarativo, como questões, resumos, legislação, notícias, correções e metadados.

## Estrutura

```text
.
├── .github/workflows/validate.yml
├── changelog/pt-BR.json
├── docs/UPDATE_PROTOCOL.md
├── packages/.gitkeep
├── schemas/
│   ├── content-package.schema.json
│   └── manifest.schema.json
├── scripts/validate_manifest.py
├── .gitignore
├── LICENSE
├── README.md
└── manifest.json
```

## Segurança

- O manifesto e os pacotes são públicos e não contêm credenciais.
- Downloads futuros exigirão HTTPS, tamanho esperado e SHA-256 válido.
- Pacotes serão apenas JSON declarativo e nunca executarão código ou comandos.
- Aplicações locais futuras deverão usar backup, transação, idempotência e rollback.
- Tokens do GitHub não serão armazenados no aplicativo.

## Licenciamento e conteúdo de terceiros

A licença MIT cobre os scripts, a estrutura e a documentação produzidos neste repositório. Conteúdos de provas, legislação comentada e materiais de terceiros não são automaticamente licenciados por ela e podem estar sujeitos aos respectivos direitos e termos de uso.

## Status

Em desenvolvimento ativo — estrutura inicial publicada.

TFM Software
