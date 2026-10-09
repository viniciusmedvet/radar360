# Relatório RADAR365 — quinta, 08/10/2026

## Produção
- 5 roteiros verificados (2 fontes por fato) e 5 vídeos renderizados com o renderizador v3:
  imagens reais trocadas a cada frase, crédito na tela e na descrição, âncora só na saudação.
- Release: https://github.com/viniciusmedvet/radar360/releases/tag/radar360-2026-10-08

| Vídeo | Duração | Fotos | Trechos de vídeo | Frases com âncora |
|---|---|---|---|---|
| 1 — Ataque russo à energia | 6:21 | 51 | 8 | 13 |
| 2 — Petroleiro perto do Catar | 5:29 | 53 | 6 | 1 |
| 3 — STF e planos de saúde aos 60 | 6:24 | 64 | 2 | 1 |
| 4 — Bolsa cai, dólar a R$ 5,01 | 5:21 | 44 | 6 | 5 |
| 5 — Vacina contra malária vivax | 5:41 | 42 | 22 | 1 |

## Publicação no YouTube
- **Nenhum vídeo publicado.** Todas as chamadas à API do YouTube pela conta youtube_singey-cheap retornaram
  `403 quotaExceeded` (cota diária do projeto Google usado pelo Composio, compartilhada com outros usuários).
- Única chamada bem-sucedida do dia: leitura do canal às ~14h (confirmou o nome RADAR365 e o channelId).
- Loop de reenvio ativo no workbench do Composio a cada 10 min (a cota renova por volta de 04:00 BRT).

## Métricas
- Não lidas: a API do YouTube recusou por cota. Nenhum número estimado.

## Lacunas
- Cota do YouTube: bloqueio estrutural; precisa de credenciais próprias do Google (ver pendências).
- Trechos de vídeo do YouTube com licença CC BY: ainda não selecionados (renderizador já confere a licença).
- config/crescimento.md e scripts/gerar-identidade.py: não existem.

## Pendências do Vinícius
- 🟣 Criar credenciais próprias da API do YouTube (Google Cloud, gratuito) para acabar com o bloqueio de cota.
- 🟣 Enquanto isso, se quiser os vídeos no ar hoje, subir manualmente a partir da Release.
