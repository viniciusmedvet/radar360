# RADAR365 — O mundo como ele é

**Missão:** informar profissionais da saúde e das ciências biológicas sobre tudo o que acontece no
mundo e mostrar, com fonte, como cada fato chega à rotina de cada profissão.

Telejornal diário automatizado: investigação, checagem, roteiros, vídeos e publicação no YouTube, Facebook, Instagram e X.

**Para incluir temas:** edite `grade_diaria` em `config/fontes.json`.
**Fontes de imagem/vídeo permitidas:** `config/fontes-midia.json`.

## Produção diária

Este sistema faz a pesquisa, a checagem e os roteiros do canal todos os dias, e depois agenda a
publicação no YouTube:

- **5 vídeos por dia** (10:00, 12:00, 15:00, 18:00 e 21:00, horário de Brasília): geopolítica
  (Ucrânia, Rússia, EUA), Oriente Médio (Irã, Ormuz, petróleo), **ciência e saúde** (seg/qua/sex/sáb: clínica médica e nutrição de cães e gatos;
  ter/qui/dom: Saúde Única),
  bastidores do STF e dos Três Poderes, e dinheiro/negócios.
- **Público:** médicos veterinários (com foco em clínica médica, nutrição e nutrologia de cães e gatos), médicos, enfermeiros, biólogos, estudantes da saúde e curiosos
  de saúde, medicina e tecnologia, além de quem acompanha geopolítica, poder e dinheiro.
- **5 textos por dia** para Instagram, TikTok e Facebook, um para cada vídeo.
- **Verificação obrigatória:** cada fato precisa de 2 fontes independentes. O que não é
  confirmado vai para a seção "Não confirmado — não usar". Roteiro que não passa no controle de
  qualidade é salvo como `REPROVADO-video-N.md` e fica fora da publicação.

## Identidade do canal

- Nome: **RADAR365 | Ciência e Mundo** · slogan "O mundo como ele é — com fonte."
- Banner (2560×1440) e foto de perfil (800×800) em `assets/canal/`, gerados por
  `python3 scripts/gerar-identidade.py` (cores e fontes do renderizador).

## Fluxo

A rotina diária do Claude ("RADAR365 — produção e publicação diária") começa às **06:30**:

```
06:30  Rotina do Claude  →  pesquisa, checagem, 4 roteiros + publicacao.json
08:15  (prazo)           →  commit em saida/AAAA-MM-DD/ na main
                         →  GitHub Actions "renderizar vídeos" → Release radar365-AAAA-MM-DD
09:30  (prazo)           →  vídeos .mp4/.jpg prontos
```

### Agenda diária de publicação (horário de Brasília)

**Canal do YouTube (exclusivo):** [RADAR365 | Ciência e Mundo](https://www.youtube.com/@curiosidadeiltda)
(`UCuUUqOrl94UCYcvjObiaEWA`). Antes de cada envio, a rotina confere esse ID e, se não bater, não publica.

**Contas de publicação:** só as listadas em `config/redes.json`. Facebook e Instagram estão
**suspensos** até existir conta própria do RADAR365 (as conectadas são perfis profissionais do Vinícius).

Cada vídeo segue a mesma ordem: YouTube primeiro, porque as redes levam o link dele.

| Vídeo | YouTube | Facebook | Instagram (Reels) | X | TikTok |
|---|---|---|---|---|---|
| 1 · geopolítica | 09:50 | 10:00 | 10:05 | 10:10 | 10:15 |
| 2 · Oriente Médio | 11:50 | 12:00 | 12:05 | 12:10 | 12:15 |
| 5 · ciência e saúde | 14:50 | 15:00 | 15:05 | 15:10 | 15:15 |
| 3 · STF e Três Poderes | 17:50 | 18:00 | 18:05 | 18:10 | 18:15 |
| 4 · dinheiro e poder | 20:50 | 21:00 | 21:05 | 21:10 | 21:15 |

**Formato por plataforma** (todos gerados do mesmo roteiro pelo renderizador):

| Arquivo | Formato | Vai para |
|---|---|---|
| `video-N.mp4` | 16:9, 1920×1080, completo | YouTube, Facebook |
| `video-N-vertical.mp4` | 9:16, 1080×1920, até ~58 s a partir do gancho | Instagram Reels, TikTok, YouTube Shorts (1/dia se houver cota) |
| `video-N.jpg` | 1280×720 | miniatura do YouTube |
| `video-N-capitulos.txt` | capítulos | descrição do YouTube |

Imagens: o renderizador troca o fundo a cada frase usando trechos de **vídeo** e fotos de licença
livre (Wikimedia Commons; Pexels se o segredo `PEXELS_API_KEY` existir), escolhidos pelas
marcações `busca:`/`pessoa:` do roteiro. Fotos ganham movimento lento; o âncora só entra quando
não há imagem adequada.

21:30: relatório do dia (`saida/AAAA-MM-DD/relatorio.md`) e resumo com os links.

**TikTok (exclusivo):** só a conta criada para o RADAR365 (alias `radar365-tiktok` no Composio, @usuário em
`agenda_publicacao`). Se o TikTok recusar o modo público (app não auditado), o vídeo fica privado e a rotina avisa.

X e TikTok entram quando forem conectados no Composio; até lá a rotina pula e registra no relatório.
A ordem e os minutos ficam em `agenda_publicacao`, em `config/fontes.json`.

| Pasta/arquivo | Conteúdo |
|---|---|
| `config/fontes.json` | Canais de referência e grade de horários. **Para indicar novos canais, edite este arquivo.** |
| `config/linha-editorial.md` | Tom, estrutura dos 10 minutos, regras de verificação e de segurança jurídica |
| `saida/AAAA-MM-DD/` | `coleta.md`, `video-N.md`, `publicacao.json`, `relatorio.md` |

## Configuração (uma vez só)

1. **Canal do YouTube**: crie o canal na sua conta Google (youtube.com → Criar canal). A criação
   de contas exige você, porque envolve verificação por telefone e aceite dos termos.
2. **Google Cloud Console**: crie um projeto e ative a *YouTube Data API v3*. Depois gere:
   - uma **chave de API**, que vira o segredo `YOUTUBE_API_KEY`;
   - uma credencial **OAuth "App para computador"**. No seu computador, rode
     `npm install && YT_CLIENT_ID=... YT_CLIENT_SECRET=... npm run token-youtube` para obter o
     `YT_REFRESH_TOKEN`.
   - Envie o projeto para a **auditoria da API do YouTube**. Sem ela, todo vídeo enviado pela API
     fica travado como privado. A cota padrão é de 10.000 unidades por dia e cada upload consome
     cerca de 1.600, o que dá para os 4 vídeos diários.
3. **Anthropic**: gere uma chave em console.anthropic.com, que vira o segredo `ANTHROPIC_API_KEY`.
4. **GitHub**: em Settings → Secrets and variables → Actions, cadastre os segredos acima.
   Workflows agendados só rodam na branch padrão, então este código precisa ser mesclado na `main`.

## Limites reais (sem promessas vazias)

- **Vídeo**: o sistema entrega roteiro, título, descrição, tags e texto de miniatura. A
  gravação ou renderização (voz + imagens) é uma etapa separada. Pode ser feita com a sua voz,
  que dá o conteúdo mais autêntico, ou com uma ferramenta de narração e edição. Se a voz ou as
  imagens forem geradas por IA de forma realista, use `CONTEUDO_SINTETICO=true`: o YouTube exige
  esse rótulo.
- **Monetização**: o Programa de Parcerias do YouTube exige 1.000 inscritos e 4.000 horas de
  exibição em 12 meses, ou 10 milhões de visualizações de Shorts em 90 dias. Canais com vídeos
  repetitivos ou produzidos em massa sem contribuição original são recusados pela política de
  "conteúdo inautêntico". Por isso a revisão humana e a análise própria são obrigatórias no fluxo.
- **Alcance**: nenhum sistema garante milhões de visualizações. O que aumenta a chance é
  constância, gancho forte, títulos honestos e a leitura semanal do YouTube Studio (retenção,
  CTR, horários do público).
- **TikTok e Instagram**: o TikTok (Content Posting API) só publica em modo público depois que o
  app é auditado. O Instagram (Graph API) exige uma conta Profissional ligada a uma Página do
  Facebook e o vídeo hospedado em uma URL pública. Enquanto isso, publique os textos e cortes pelo
  agendador nativo (Meta Business Suite e TikTok Studio).
- **Segurança jurídica**: citados em investigação são sempre "investigados", nunca "corruptos"
  (arts. 138–140 do Código Penal; direito de resposta, Lei 13.188/2015). Em período eleitoral,
  nada de conteúdo sabidamente falso nem de áudio ou imagem sintética de candidatos.

## Comandos

```bash
npm install
npm run coletar            # precisa de YOUTUBE_API_KEY
npm run gerar              # precisa de ANTHROPIC_API_KEY
npm run publicar:simular   # confere o que será enviado, sem publicar
npm run publicar           # envia e agenda (precisa de YT_CLIENT_ID/SECRET/REFRESH_TOKEN)
```
