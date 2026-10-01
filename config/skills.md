# Gestão de skills, plugins e conectores — RADAR365

Mapa mantido pela skill-maestro. Contas de publicação: `config/redes.json` manda. A rotina diária consulta este arquivo no início, usa o recurso
indicado em cada etapa e registra no `relatorio.md` qualquer lacuna ou falha ("Gestão de skills").
Revisão: a cada 7 dias ou quando uma etapa falhar 2 vezes seguidas.

Legenda: ✅ ativo · 🟡 disponível, falta instalar/conectar · ❌ lacuna (sem recurso adequado)

## Mapa por etapa

| Etapa | Recurso recrutado | Status | Por quê |
|---|---|---|---|
| Pauta: o que o público está vendo | `scripts/coletar-fontes.mjs` (YouTube Data API) | 🟡 precisa do segredo `YOUTUBE_API_KEY` | ranking de vídeos por views/hora nos canais de referência |
| Pauta: tendências e SEO no YouTube | Plugin **TubeAlfred YouTube** (keyword-ideas, competitor, seo-audit, shorts) | 🟡 instalar | dados reais de busca e concorrência, cada número rotulado como observado/inferido |
| Notícias de 24 h | WebSearch + WebFetch (nativo) | ✅ | leitura integral das matérias |
| Ciência e saúde: artigos | Conector **PubMed** | ✅ conectado | DOI/PMID, metadados e texto completo quando aberto |
| Ciência e saúde: síntese de evidências | Conector **Consensus** | ✅ conectado | panorama de estudos com citação |
| Ensaios clínicos | Conector **Clinical Trials** | ✅ conectado | estudos registrados (humanos) |
| Conformidade em saúde (sem promessa, sem marca, sem prescrição) | Plugin **Marketing for Life Sciences** (regulatory-compliance, mlr-review) | 🟡 instalar | revisão de conformidade antes de publicar |
| Roteiro e checagem | `config/linha-editorial.md` + skill-maestro (camadas Gerente → Auditor) | ✅ | portão de qualidade e zero fictício |
| Imagens e vídeos de fundo | `scripts/renderizar-video.py` (Wikimedia Commons + Pexels) | ✅ Commons · 🟡 Pexels precisa de `PEXELS_API_KEY` | trechos de vídeo de licença livre |
| Narração | edge-tts (voz neural pt-BR) | ✅ | sem custo |
| Renderização | GitHub Actions (um job por vídeo) | ✅ testado em 01/10/2026 | 16:9 + vertical 9:16 + miniatura + capítulos |
| Miniaturas e artes especiais | Conector **Canva** | ✅ conectado | quando a miniatura automática não bastar |
| Identidade do canal | `scripts/gerar-identidade.py` | ✅ | banner e foto de perfil |
| Publicação YouTube | Composio `youtube_singey-cheap` (@curiosidadeiltda) | ✅ conectado · 🟡 ativar o Composio na rotina | canal exclusivo |
| Publicação Facebook e Instagram | conta própria do RADAR365 (a criar) | ❌ suspenso: as contas conectadas são perfis profissionais do Vinícius e estão proibidas em `config/redes.json` | — |
| Publicação TikTok | Composio TikTok (alias `radar365-tiktok`) | ❌ conta ainda não criada | — |
| Publicação X | Composio Twitter | 🟡 conectar | — |
| Texto para redes e SEO | Plugin **Marketing** (Anthropic: content-creation, seo-audit, performance-report) | 🟡 instalar | títulos, descrições e relatório de desempenho |
| Métricas e aprendizado semanal | YouTube Studio (manual) + plugin Marketing `performance-report` | 🟡 | ajustar horários e temas com dados reais |
| Agenda e lembretes do Vinícius | Conector **Google Calendar** | ✅ conectado | pendências 🟣 com data |

## Avaliados e não recrutados

| Recurso | Motivo |
|---|---|
| Ayrshare (publicação em 13 redes) | serviço pago à parte; a regra é não gastar sem aprovação. Reavaliar se o Composio falhar. |
| AdWhispr, Dataslayer, Kopi, Brandvane | foco em anúncios pagos, e-mail ou SEO de sites, fora da necessidade atual |
| YouTube Transcriber | o TubeAlfred cobre transcrição e muito mais |
| Owkin, Synthesize Bio | pesquisa de biologia computacional, não jornalismo |

## Skill dedicada proposta (aguardando aprovação do Vinícius)

**radar365-redacao**: concentraria a missão, a linha editorial, as regras de cães e gatos, as
marcações de imagem e o checklist de publicação numa skill própria, ativada sempre que o assunto
for o RADAR365. Só será criada com o "sim" do Vinícius (regra 4 da skill-maestro).

## Histórico

- 01/10/2026: mapa criado. Teste de renderização v3 no GitHub Actions: 4 de 4 vídeos ok.
