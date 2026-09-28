import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const FUSO = "America/Sao_Paulo";

// Data (AAAA-MM-DD) no horário de Brasília, com deslocamento opcional em dias.
export function dataBrasilia(deslocamentoDias = 0) {
  const d = new Date(Date.now() + deslocamentoDias * 86_400_000);
  return new Intl.DateTimeFormat("en-CA", { timeZone: FUSO }).format(d);
}

export function agoraBrasilia() {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    dateStyle: "full",
    timeStyle: "short",
  }).format(new Date());
}

// Pasta de saída do dia de PUBLICAÇÃO (padrão: hoje em Brasília; a produção roda às 05:40).
export async function pastaDoDia() {
  // `||`: o workflow agendado define DATA_PUBLICACAO como string vazia.
  const data = process.env.DATA_PUBLICACAO || dataBrasilia(Number(process.env.DESLOCAMENTO_DIAS ?? 0));
  const pasta = path.join(RAIZ, "saida", data);
  await fs.mkdir(pasta, { recursive: true });
  return { data, pasta };
}

export async function lerJson(arquivo, padrao) {
  try {
    return JSON.parse(await fs.readFile(arquivo, "utf8"));
  } catch (erro) {
    if (erro.code === "ENOENT" && padrao !== undefined) return padrao;
    throw erro;
  }
}

export function exigirEnv(...nomes) {
  const faltando = nomes.filter((n) => !process.env[n]);
  if (faltando.length) {
    console.error(`Variáveis de ambiente ausentes: ${faltando.join(", ")} (ver canal-noticias/.env.example)`);
    process.exit(1);
  }
}
