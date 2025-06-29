// app.js
const express = require('express');
const multer = require('multer');
const path = require('path');
const { uploadToHancom, buildViewerUrl } = require('./hancomClient');

const app = express();
const upload = multer({ dest: 'uploads/' });

app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.get('/', (req, res) => {
  res.render('upload');
});

app.post('/upload', upload.single('file'), async (req, res) => {
  try {
    const originalName = req.file.originalname;
    const localPath = req.file.path;

    // 1. 한컴 서버에 업로드
    const uploadPath = await uploadToHancom(localPath, originalName);
    const filePath = `${uploadPath}/${originalName}`;

    // 2. 변환 없이 바로 뷰어 URL 생성
    const viewerUrl = buildViewerUrl(filePath);

    // 3. 결과 페이지 렌더링
    res.render('viewer', { viewerUrl });
  } catch (err) {
    console.error('🚨 오류 발생:', err.message);
    res.status(500).send('🚨 오류: ' + err.message);
  }
});

app.listen(3000, () => {
  console.log('✅ 서버 실행 중: http://localhost:3000');
});
