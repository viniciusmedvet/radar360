// Envia ao YouTube os vídeos aprovados do dia e agenda a estreia (privado -> público em publishAt).
// Requer os arquivos .mp4 (e .jpg de miniatura, opcional) em saida/<data>/, conforme publicacao.json.
// Uso: node scripts/publicar-youtube.mjs [--simular]
import fs from "node:fs";
import path from "node:path";
import { google } from "googleapis";
import { pastaDoDia, lerJson, exigirEnv } from "./comum.mjs";

const simular = process.argv.includes("--simular");
if (!simular) exigirEnv("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN");

const { data, pasta } = await pastaDoDia();
const manifesto = await lerJson(path.join(pasta, "publicacao.json"));
const registroArq = path.join(pasta, "publicados.json");
const publicados = await lerJson(registroArq, {});

const auth = new google.auth.OAuth2(process.env.YT_CLIENT_ID, process.env.YT_CLIENT_SECRET);
auth.setCredentials({ refresh_token: process.env.YT_REFRESH_TOKEN });
const youtube = google.youtube({ version: "v3", auth });

for (const v of manifesto.videos) {
  if (publicados[v.slot]) {
    console.log(`Vídeo ${v.slot} já enviado (${publicados[v.slot]}), pulando.`);
    continue;
  }
  const arquivo = path.join(pasta, v.arquivo);
  if (!fs.existsSync(arquivo)) {
    console.warn(`Vídeo ${v.slot}: ${v.arquivo} não encontrado em ${pasta} — renderize/grave o vídeo antes.`);
    continue;
  }
  if (new Date(v.publicarEm).getTime() < Date.now() + 15 * 60_000) {
    console.warn(`Vídeo ${v.slot}: horário ${v.publicarEm} já passou ou está a menos de 15 min — ajuste publicarEm.`);
    continue;
  }
  const requestBody = {
    snippet: {
      title: v.titulo,
      description: v.descricao,
      tags: v.tags,
      categoryId: "25", // Notícias e política
      defaultLanguage: "pt-BR",
      defaultAudioLanguage: "pt-BR",
    },
    status: {
      privacyStatus: "private", // obrigatório para agendar com publishAt
      publishAt: new Date(v.publicarEm).toISOString(),
      selfDeclaredMadeForKids: false,
      containsSyntheticMedia: process.env.CONTEUDO_SINTETICO === "true", // narração/imagem gerada por IA realista
    },
  };
  if (simular) {
    console.log(`[simulação] ${data} slot ${v.slot}:`, JSON.stringify(requestBody, null, 2));
    continue;
  }
  const { data: enviado } = await youtube.videos.insert({
    part: ["snippet", "status"],
    requestBody,
    media: { body: fs.createReadStream(arquivo) },
  });
  const miniatura = path.join(pasta, v.miniatura ?? "");
  if (v.miniatura && fs.existsSync(miniatura)) {
    await youtube.thumbnails.set({ videoId: enviado.id, media: { body: fs.createReadStream(miniatura) } });
  }
  publicados[v.slot] = enviado.id;
  fs.writeFileSync(registroArq, JSON.stringify(publicados, null, 2));
  console.log(`Vídeo ${v.slot} enviado: https://youtu.be/${enviado.id} — estreia ${v.publicarEm}`);
}
