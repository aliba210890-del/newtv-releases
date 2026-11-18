// Сайт newtvglobal.online: статика + страницы активации и оплаты прямо на нашем адресе (без перехода на workers.dev).
// /activate/КОД → страница активации плеера, /pay/КОД → оплата PayPal; отвечает сервер newtv-api через прямую связь (service binding).
const PROXY = /^\/(activate|a|pay|c|i)(\/|$)|^\/api\/web\//;
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (PROXY.test(url.pathname)) {
      const u = new URL(url.pathname.replace(/^\/activate(?=\/|$)/, "/a") + url.search, "https://newtv-api.aliba210890.workers.dev");
      return env.NEWTV_API.fetch(new Request(u, request));
    }
    return env.ASSETS.fetch(request);
  },
};
