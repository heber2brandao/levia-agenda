# Painel conectado e logo do espaço

`/conta` agora abre o painel com nome do espaço, logo e contagens reais do catálogo.
Os links **Painel**, **Meu perfil** e **Serviços e horários** permanecem disponíveis.
As páginas `/conta/perfil` e `/conta/servicos` podem ser recarregadas e acessadas
pelo histórico do navegador. Agenda e clientes ainda pertencem à próxima etapa;
o painel não mostra métricas fictícias dessas funcionalidades.

Em **Meu perfil → Aparência → Logo do espaço**, selecionar uma imagem salva
automaticamente na conta. É necessário ter salvo o perfil antes. A imagem aparece
também no painel e na prévia privada dos serviços. O botão **Remover logo** remove
a imagem persistida. Salvar o perfil não substitui nem apaga a logo.

Upload autenticado por `PUT /api/v1/me/logo`, remoção por `DELETE /api/v1/me/logo`.
Aceita PNG, JPG e WebP estáticos de até 2 MiB e 4096 × 4096 pixels. O servidor
decodifica e reencoda como PNG, remove metadados e reduz para até 256 × 256 pixels,
preservando proporção/transparência. Não aceita SVG, arquivos inválidos ou animações.
O limite de corpo ampliado vale apenas para esse PUT; outros endpoints mantêm 32 KiB.

Uma imagem pequena por profissional fica em `professionals.logo_png`, com limite
de 270.000 bytes e a RLS existente. Isso evita bucket público e permissões adicionais
nesta fase. Migração `0004_professional_logo` aplicada ao Supabase, preservando o
perfil existente. Para outro ambiente: instalar dependências e `alembic upgrade head`.

Validação executada: 42 testes Pytest com PostgreSQL local, incluindo persistência,
remoção, isolamento entre contas, preservação após editar o perfil, limites de upload
e normalização da imagem; 8 testes Playwright de regressão da demonstração; build,
Ruff e pip check aprovados. Migração e permissão de UPDATE verificadas no Supabase.
O upload via navegador na sessão real do responsável ainda precisa ser experimentado.

Referência: [processamento de imagens Pillow](https://pillow.readthedocs.io/en/stable/reference/Image.html).
