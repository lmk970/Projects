// api.js
export async function shortenUrl(longUrl) {
  const apiKey = 'X3t0nQCzFPd8Rm4JTKVrgFS7uAHPuKl6GfmNHQWcMc5nW9zVGTdoCmf03hbZ'; // 여기에 발급받은 키 입력
  const res = await fetch("https://api.tinyurl.com/create", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      url: longUrl,
      domain: "tinyurl.com"
    })
  });

  if (!res.ok) throw new Error("TinyURL 단축 실패");
  const json = await res.json();
  return json.data.tiny_url;
}
