// Renew only the existing same-origin loopback viewer credential. Never persist
// it or send it to a public Site, a different port, or a URL query string.
export async function localViewerToken(origin,{signal,fetchImpl=globalThis.fetch,locationOrigin=globalThis.location?.origin}={}){
 if(origin!==locationOrigin||!/^http:\/\/(?:127\.0\.0\.1|localhost):\d+$/.test(origin))return null;
 try{
  const response=await fetchImpl(origin+'/',{method:'GET',cache:'no-store',credentials:'omit',redirect:'error',signal});
  if(!response.ok||Number(response.headers?.get?.('content-length')||0)>2*1024*1024)return null;
  const html=await response.text();if(html.length>2*1024*1024)return null;
  const tag=html.match(/<script\b[^>]*\bid=["']ax-release-bootstrap["'][^>]*>([^<]*)<\/script>/i);
  const config=tag?JSON.parse(tag[1]):null;
  return config?.kind==='lgax_local_release_connection'&&config.url===origin&&typeof config.token==='string'&&/^[A-Za-z0-9_-]{32,128}$/.test(config.token)?config.token:null;
 }catch{return null;}
}
