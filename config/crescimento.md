# Crescimento do canal — RADAR365

Autorização do Vinícius (01/10/2026): a redação pode editar livremente imagens e comunicações do
canal @curiosidadeiltda e acompanhar todos os números para fazê-lo crescer, sempre com excelência.

## Métrica principal e metas

- **Norte:** inscritos ganhos por semana. Apoio: visualizações por vídeo nas primeiras 48 h,
  curtidas por visualização, comentários, vídeos adicionados às playlists.
- Ponto de partida (01/10/2026): 6 inscritos, 918 visualizações, 10 vídeos públicos antigos.
- Marcos do Programa de Parcerias (para referência, regra oficial do YouTube): 1.000 inscritos e
  4.000 horas assistidas em 12 meses, ou 10 milhões de visualizações de Shorts em 90 dias.
- Metas de trabalho, revisadas todo domingo com os dados reais: 100 inscritos → 1.000 → 10.000.

## Medição (automática, pela rotina diária)

- **Todo dia, 21:30:** `saida/metricas/AAAA-MM-DD.json` com inscritos, visualizações e número de
  vídeos do canal (YOUTUBE_GET_CHANNEL_STATISTICS) e, para os vídeos dos últimos 7 dias,
  visualizações, curtidas e comentários (YOUTUBE_GET_VIDEO_DETAILS_BATCH). Sempre account
  youtube_singey-cheap.
- **Domingo (revisão semanal):** comparar com 7 dias antes; ranquear os vídeos por visualizações
  por hora desde a publicação e por curtidas/visualização; registrar abaixo, em "Aprendizados",
  o que funcionou (tema, título, miniatura, horário, profissão citada) e o que muda na semana.
- Dados que a API pública não dá (retenção, CTR da miniatura, origem do tráfego): só pela leitura
  manual do YouTube Studio pelo Vinícius. O vidIQ (pago) foi RECUSADO por ele em 02/10/2026: não
  conectar nem sugerir de novo. Nunca estimar esses números.

## Alavancas aplicadas a cada vídeo

1. **Título** (≤ 70 caracteres): fato forte + quem é afetado ("o que muda para o veterinário").
   Testar 3 opções no roteiro; usar a mais concreta. Proibido prometer o que o vídeo não entrega.
2. **Miniatura:** até 4 palavras, alto contraste, rosto/objeto reconhecível quando houver imagem
   licenciada. Domingo: comparar miniaturas dos vídeos com mais e menos visualizações por hora.
3. **Gancho de 30 s** que funciona sozinho (abre o corte vertical).
4. **Chamada para inscrição** no fim da promessa (0:30–1:00) e na tela final "Inscreva-se"
   (6 s, gerada pelo renderizador). No YouTube Studio, a tela final pode ganhar o botão de
   inscrição — ação manual, a API não permite.
5. **Playlist** do eixo (`playlists` em `config/fontes.json`) logo após o upload.
6. **Comentário do canal** logo após o upload: uma pergunta para a profissão mais atingida
   ("Veterinários: vocês já sentiram isso no preço da ração na clínica?") + link das fontes.
   Fixar o comentário é manual (a API não permite).
7. **Descrição:** 2 primeiras linhas com o fato e a profissão; capítulos; fontes; link das
   playlists; hashtags das profissões (#medicinaveterinaria #enfermagem #biologia #biomedicina).
8. **Shorts** (1 por dia, se houver cota): o corte vertical do vídeo com gancho mais forte.
9. **Identidade do canal:** a redação pode reescrever descrição e palavras-chave do canal quando
   os aprendizados indicarem; banner e foto: regenerar com `scripts/gerar-identidade.py` e pedir
   ao Vinícius o envio (a API não troca essas imagens).

## Proibido (políticas do YouTube e credibilidade)

- Comprar inscritos/visualizações, troca "inscreve que eu inscrevo", bots, comentários falsos.
- Clickbait enganoso, títulos sensacionalistas sobre saúde, números exagerados.
- Pedir inscrição em troca de prêmio. Publicar em contas fora de `config/redes.json`.

## Aprendizados (atualizado todo domingo)

- 01/10/2026: catálogo antigo fora da linha tornado privado (lista e como desfazer em
  `saida/metricas/catalogo-antigo.json`); fica pública só a Medusa (biologia).
- 01/10/2026: canal parte de 6 inscritos e catálogo antigo fora da linha editorial. Primeira
  semana: medir qual eixo traz mais inscritos por vídeo.
