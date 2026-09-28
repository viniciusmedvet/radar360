// Gera os 4 roteiros de ~10 min + 4 textos de redes do dia, com pesquisa e checagem na web
// feitas pelo Claude (web_search / web_fetch). Cada saída passa por um portão de qualidade;
// o que não passa é salvo como REPROVADO e não entra no manifesto de publicação.
import fs from "node:fs/promises";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { RAIZ, pastaDoDia, lerJson, exigirEnv, agoraBrasilia } from "./comum.mjs";

exigirEnv("ANTHROPIC_API_KEY");
const client = new Anthropic();
const MODELO = process.env.MODELO_CLAUDE ?? "claude-opus-5-5";

const sistema = await fs.readFile(path.join(RAIZ, "config", "linha-editorial.md"), "utf8");
const { grade_diaria: grade } = await lerJson(path.join(RAIZ, "config", "fontes.json"));
const { data, pasta } = await pastaDoDia();
const coleta = await lerJson(path.join(pasta, "coleta.json"), { videos: [] });

async function gerar(pedido) {
  const messages = [{ role: "user", content: pedido }];
  // Ferramentas de servidor podem pausar a vez (pause_turn); reenviamos para continuar.
  for (let rodada = 0; rodada < 8; rodada++) {
    const resposta = await client.beta.messages
      .stream({
        model: MODELO,
        max_tokens: 64000,
        betas: ["server-side-fallback-2026-07-01"],
        fallbacks: "default",
        thinking: { type: "adaptive" },
        output_config: { effort: "high" },
        system: [{ type: "text", text: sistema, cache_control: { type: "ephemeral" } }],
        tools: [
          { type: "web_search_20260209", name: "web_search", max_uses: 15, user_location: { type: "approximate", country: "BR" } },
          { type: "web_fetch_20260209", name: "web_fetch", max_uses: 10 },
        ],
        messages,
      })
      .finalMessage();

    if (resposta.stop_reason === "pause_turn") {
      messages.push({ role: "assistant", content: resposta.content });
      continue;
    }
    if (resposta.stop_reason === "refusal") {
      throw new Error(`Recusa do modelo (${resposta.stop_details?.category ?? "sem categoria"})`);
    }
    return resposta.content
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("");
  }
  throw new Error("Limite de rodadas de pesquisa atingido");
}

function secao(md, titulo) {
  const inicio = md.indexOf(`## ${titulo}`);
  if (inicio < 0) return "";
  const resto = md.slice(inicio + titulo.length + 3);
  const fim = resto.search(/\n## /);
  return (fim < 0 ? resto : resto.slice(0, fim)).trim();
}

// Portão de qualidade: estrutura completa, >= 2 fontes distintas, roteiro no tamanho de 10 min
// e nenhum rótulo criminal sem atribuição.
function auditar(md) {
  const problemas = [];
  for (const s of ["Títulos", "Descrição do YouTube", "Roteiro narrado", "Texto para redes sociais", "Fontes verificadas"]) {
    if (!secao(md, s)) problemas.push(`seção ausente: ${s}`);
  }
  const urls = new Set(secao(md, "Fontes verificadas").match(/https?:\/\/[^\s)>\]]+/g) ?? []);
  if (urls.size < 2) problemas.push(`apenas ${urls.size} fonte(s) verificada(s)`);
  const palavras = secao(md, "Roteiro narrado").replace(/\[[^\]]*\]/g, "").split(/\s+/).filter(Boolean).length;
  if (palavras < 1100) problemas.push(`roteiro curto para 10 min (${palavras} palavras)`);
  if (/\b(é|são) (corrupt[oa]s?|bandid[oa]s?|criminos[oa]s?)\b/i.test(md)) {
    problemas.push("rótulo criminal direto — reescrever com atribuição");
  }
  return { problemas, palavras, fontes: urls.size };
}

const pautasDoPublico = coleta.videos
  .slice(0, 25)
  .map((v) => `- [${v.canal}] "${v.titulo}" — ${v.viewsPorHora} views/h — ${v.url}`)
  .join("\n");

const manifesto = { data, videos: [] };
const relatorio = [`# Relatório de geração — ${data}`, `Executado em ${agoraBrasilia()} · modelo ${MODELO}`, ""];

for (const slot of grade) {
  const pedido = [
    `Agora é ${agoraBrasilia()} (horário de Brasília). Publicação prevista: ${data} às ${slot.horario_brt} BRT.`,
    `Produza o VÍDEO ${slot.slot} do dia. Eixo: ${slot.eixo}. Tema: ${slot.tema}.`,
    "",
    "Temas que mais estão sendo assistidos agora nos canais de referência (use como termômetro de interesse, NÃO como prova):",
    pautasDoPublico || "- (coleta indisponível hoje — levante você mesmo as principais notícias das últimas 24–48 h)",
    "",
    "Passos: (1) pesquise as notícias mais relevantes das últimas 24–48 h deste eixo; (2) escolha a história de maior",
    "impacto e interesse; (3) confirme cada fato em pelo menos duas fontes independentes, abrindo as páginas;",
    "(4) escreva no formato obrigatório da linha editorial, com roteiro narrado de 1.300 a 1.450 palavras.",
    "Não repita a mesma história dos outros slots do dia.",
    manifesto.videos.length ? `Histórias já usadas hoje: ${manifesto.videos.map((v) => v.titulo).join(" | ")}` : "",
  ].join("\n");

  try {
    const md = await gerar(pedido);
    const { problemas, palavras, fontes } = auditar(md);
    const aprovado = problemas.length === 0;
    const nome = `${aprovado ? "" : "REPROVADO-"}video-${slot.slot}.md`;
    await fs.writeFile(path.join(pasta, nome), md);
    relatorio.push(`- Vídeo ${slot.slot}: ${aprovado ? "APROVADO" : "REPROVADO"} · ${palavras} palavras · ${fontes} fontes${aprovado ? "" : ` · ${problemas.join("; ")}`}`);
    if (aprovado) {
      const titulo = (secao(md, "Títulos").match(/^\s*(?:\d+[.)]|[-*])\s*(.+)$/m)?.[1] ?? `Vídeo ${slot.slot}`).replace(/\*\*/g, "").trim();
      manifesto.videos.push({
        slot: slot.slot,
        arquivo: `video-${slot.slot}.mp4`,
        miniatura: `video-${slot.slot}.jpg`,
        titulo: titulo.slice(0, 100),
        descricao: secao(md, "Descrição do YouTube").slice(0, 4900),
        tags: secao(md, "Tags").split(/[,\n#]/).map((t) => t.replace(/^[-*\s]+/, "").trim()).filter(Boolean).slice(0, 15),
        publicarEm: `${data}T${slot.horario_brt}:00-03:00`,
      });
    }
  } catch (erro) {
    relatorio.push(`- Vídeo ${slot.slot}: FALHOU — ${erro.message}`);
  }
}

await fs.writeFile(path.join(pasta, "publicacao.json"), JSON.stringify(manifesto, null, 2));
await fs.writeFile(path.join(pasta, "relatorio.md"), relatorio.join("\n") + "\n");
console.log(relatorio.join("\n"));
