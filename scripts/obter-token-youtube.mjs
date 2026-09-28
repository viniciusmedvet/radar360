// Execução única, no SEU computador: autoriza o app a enviar vídeos ao seu canal e imprime o
// YT_REFRESH_TOKEN. Pré-requisito: credencial OAuth "App para computador" no Google Cloud Console
// com a YouTube Data API v3 ativada. Uso: YT_CLIENT_ID=... YT_CLIENT_SECRET=... node scripts/obter-token-youtube.mjs
import http from "node:http";
import { google } from "googleapis";
import { exigirEnv } from "./comum.mjs";

exigirEnv("YT_CLIENT_ID", "YT_CLIENT_SECRET");
const PORTA = 53682;
const auth = new google.auth.OAuth2(
  process.env.YT_CLIENT_ID,
  process.env.YT_CLIENT_SECRET,
  `http://127.0.0.1:${PORTA}`,
);
const url = auth.generateAuthUrl({
  access_type: "offline",
  prompt: "consent",
  scope: ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"],
});
console.log(`Abra no navegador, entre com a conta dona do canal e autorize:\n\n${url}\n`);

const servidor = http.createServer(async (req, res) => {
  const codigo = new URL(req.url, `http://127.0.0.1:${PORTA}`).searchParams.get("code");
  if (!codigo) return res.end("Aguardando autorização...");
  const { tokens } = await auth.getToken(codigo);
  res.end("Autorizado. Pode fechar esta aba e voltar ao terminal.");
  console.log(`YT_REFRESH_TOKEN=${tokens.refresh_token}\n\nGuarde como segredo (GitHub > Settings > Secrets). Não publique.`);
  servidor.close();
});
servidor.listen(PORTA, "127.0.0.1");
