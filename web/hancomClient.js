// hancomClient.js
const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');
const config = require('./config');

async function uploadToHancom(localPath, originalName) {
  const form = new FormData();
  form.append('file', fs.createReadStream(localPath), originalName);

  const res = await axios.post(config.HANCOM_UPLOAD_API, form, {
    headers: form.getHeaders()
  });

  const data = res.data;
  console.log("📦 한컴 업로드 응답 전체:", data);

  if (data.code !== '0000') {
    throw new Error(`업로드 실패: ${JSON.stringify(data)}`);
  }

  const fullPath =
    data.upload_file_full_path ||              // ✅ 최우선
    data.resource_file_path ||                 // 혹시 있다면
    data.real_file_name
      ? `${data.upload_file_path}/${data.real_file_name}`
      : `${data.upload_file_path}/${originalName}`; // 마지막 fallback

  return fullPath;
}


function buildViewerUrl(rawFilePath) {
  const encoded = encodeURIComponent(rawFilePath);
  return `${config.HANCOM_VIEWER_BASE}?file_path=${encoded}&ext_to=jpg`;
}

module.exports = { uploadToHancom, buildViewerUrl };
