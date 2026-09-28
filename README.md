# Canal de notícias: produção diária automatizada

Este sistema faz a pesquisa, a checagem e os roteiros do canal todos os dias, e depois agenda a
publicação no YouTube:

- **4 vídeos por dia** (07:00, 12:00, 18:00 e 21:00, horário de Brasília): geopolítica
  (Ucrânia, Rússia, EUA), Oriente Médio (Irã, Ormuz, petróleo), bastidores do STF e dos Três
  Poderes, e dinheiro/negócios.
- **4 textos por dia** para Instagram, TikTok e Facebook, um para cada vídeo.
- **Verificação obrigatória:** cada fato precisa de 2 fontes independentes. O que não é
  confirmado vai para a seção "Não confirmado — não usar". Roteiro que não passa no controle de
  qualidade é salvo como `REPROVADO-video-N.md` e fica fora da publicação.

## Fluxo

```
05:40  GitHub Actions  →  coletar-fontes.mjs  →  vídeos recentes dos canais de referência,
                                                  ordenados por views/hora (o que o público está vendo agora)
                       →  gerar-conteudo.mjs  →  Claude pesquisa, checa e escreve 4 roteiros + 4 textos
                       →  commit em saida/AAAA-MM-DD/
Você   →  revisa → grava ou renderiza os .mp4 → npm run publicar  →  YouTube (privado, estreia agendada)
```

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
cd canal-noticias
npm install
npm run coletar            # precisa de YOUTUBE_API_KEY
npm run gerar              # precisa de ANTHROPIC_API_KEY
npm run publicar:simular   # confere o que será enviado, sem publicar
npm run publicar           # envia e agenda (precisa de YT_CLIENT_ID/SECRET/REFRESH_TOKEN)
```
