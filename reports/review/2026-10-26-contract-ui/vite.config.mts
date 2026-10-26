import base from "../../../frontend/vite.config";

// 専用試験だけのproxy。製品側の固定設定を変更しない。
export default {
  ...base,
  server: {
    ...base.server,
    host: "127.0.0.1",
    port: Number(process.env.E2E_UI_PORT),
    strictPort: true,
    proxy: { "/api": { target: process.env.E2E_API_URL, changeOrigin: false } },
  },
};
