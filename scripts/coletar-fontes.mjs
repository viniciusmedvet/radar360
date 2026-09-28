// Coleta os vídeos recentes dos canais de referência (YouTube Data API v3) e ranqueia
// por velocidade de visualização (views/hora), para identificar os temas que o público
// está assistindo agora. Saída: saida/<data>/coleta.json e coleta.md
import fs from "node:fs/promises";
import path from "node:path";
import { RAIZ, pastaDoDia, lerJson, exigirEnv, agoraBrasilia } from "./comum.mjs";

exigirEnv("YOUTUBE_API_KEY");
const API = "https://www.googleapis.com/youtube/v3";
const JANELA_HORAS = Number(process.env.JANELA_HORAS ?? 48);

async function yt(recurso, params) {
  const url = new URL(`${API}/${recurso}`);
  for (const [k, v] of Object.entries({ ...params, key: process.env.YOUTUBE_API_KEY })) {
    url.searchParams.set(k, v);
  }
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`YouTube ${recurso} HTTP ${resp.status}: ${await resp.text()}`);
  return resp.json();
}

async function resolverCanal(canal) {
  if (canal.channelId) {
    const r = await yt("channels", { part: "contentDetails,snippet", id: canal.channelId });
    return r.items?.[0];
  }
  if (canal.handle) {
    const r = await yt("channels", { part: "contentDetails,snippet", forHandle: canal.handle });
    if (r.items?.[0]) return r.items[0];
  }
  // Fallback por busca (custa 100 unidades de cota): o resultado precisa ser conferido.
  const busca = await yt("search", { part: "snippet", q: canal.busca, type: "channel", maxResults: 1 });
  const id = busca.items?.[0]?.id?.channelId;
  if (!id) return undefined;
  const r = await yt("channels", { part: "contentDetails,snippet", id });
  return r.items?.[0];
}

function duracaoEmMinutos(iso) {
  const m = /PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/.exec(iso ?? "");
  if (!m) return null;
  return Math.round(((+m[1] || 0) * 3600 + (+m[2] || 0) * 60 + (+m[3] || 0)) / 60);
}

const { canais } = await lerJson(path.join(RAIZ, "config", "fontes.json"));
const { data, pasta } = await pastaDoDia();
const corte = Date.now() - JANELA_HORAS * 3_600_000;
const resultado = { geradoEm: agoraBrasilia(), janelaHoras: JANELA_HORAS, canais: [], videos: [] };

for (const canal of canais) {
  try {
    const info = await resolverCanal(canal);
    if (!info) {
      resultado.canais.push({ nome: canal.nome, status: "NÃO ENCONTRADO — revisar handle/busca" });
      continue;
    }
    resultado.canais.push({
      nome: canal.nome,
      encontrado: info.snippet.title,
      channelId: info.id,
      status: canal.confirmar ? "CONFERIR se é o canal certo e fixar channelId em fontes.json" : "ok",
    });
    const uploads = info.contentDetails.relatedPlaylists.uploads;
    const lista = await yt("playlistItems", { part: "contentDetails", playlistId: uploads, maxResults: 25 });
    const ids = (lista.items ?? [])
      .filter((i) => new Date(i.contentDetails.videoPublishedAt).getTime() >= corte)
      .map((i) => i.contentDetails.videoId);
    if (!ids.length) continue;
    const det = await yt("videos", { part: "snippet,statistics,contentDetails", id: ids.join(",") });
    for (const v of det.items ?? []) {
      const horas = Math.max(1, (Date.now() - new Date(v.snippet.publishedAt).getTime()) / 3_600_000);
      const views = Number(v.statistics.viewCount ?? 0);
      resultado.videos.push({
        canal: canal.nome,
        eixo: canal.eixo,
        titulo: v.snippet.title,
        url: `https://www.youtube.com/watch?v=${v.id}`,
        publicadoEm: v.snippet.publishedAt,
        minutos: duracaoEmMinutos(v.contentDetails.duration),
        views,
        comentarios: Number(v.statistics.commentCount ?? 0),
        viewsPorHora: Math.round(views / horas),
        descricao: (v.snippet.description ?? "").slice(0, 1200),
      });
    }
  } catch (erro) {
    resultado.canais.push({ nome: canal.nome, status: `ERRO: ${erro.message}` });
  }
}

resultado.videos.sort((a, b) => b.viewsPorHora - a.viewsPorHora);
await fs.writeFile(path.join(pasta, "coleta.json"), JSON.stringify(resultado, null, 2));

const linhas = [
  `# Coleta de referências — ${data}`,
  `Gerado em ${resultado.geradoEm} · janela de ${JANELA_HORAS} h`,
  "",
  "## Canais",
  ...resultado.canais.map((c) => `- **${c.nome}** → ${c.encontrado ?? "—"} (${c.channelId ?? "—"}): ${c.status}`),
  "",
  "## Vídeos por velocidade (views/hora)",
  "| # | Canal | Título | Views | Views/h | Min |",
  "|---|---|---|---:|---:|---:|",
  ...resultado.videos.map(
    (v, i) => `| ${i + 1} | ${v.canal} | [${v.titulo.replaceAll("|", "/")}](${v.url}) | ${v.views} | ${v.viewsPorHora} | ${v.minutos ?? "?"} |`,
  ),
];
await fs.writeFile(path.join(pasta, "coleta.md"), linhas.join("\n") + "\n");
console.log(`Coleta salva em ${pasta} — ${resultado.videos.length} vídeos, ${resultado.canais.length} canais.`);
