<?php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!isset($_GET['filename'])) {
        http_response_code(400);
        echo "❌ 'filename' 파라미터가 필요합니다.";
        exit;
    }

    $filename = basename($_GET['filename']);
    $uploadDir = __DIR__ . '/'; // 현재 폴더에 저장
    $savePath = $uploadDir . $filename;

    $rawData = file_get_contents("php://input");
    if (file_put_contents($savePath, $rawData) !== false) {
        http_response_code(200);
        echo "✅ 저장 완료: $filename";
    } else {
        http_response_code(500);
        echo "❌ 저장 실패";
    }
} else {
    http_response_code(405);
    echo "❌ 유효하지 않은 요청";
}
?>
