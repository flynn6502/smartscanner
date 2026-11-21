<?php
declare(strict_types=1);

header('X-Content-Type-Options: nosniff');

function json_error(string $message, int $status = 400): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['error' => $message], JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    json_error('Método não permitido.', 405);
}

if (!isset($_FILES['file']) || !is_array($_FILES['file'])) {
    json_error('Nenhum arquivo enviado.');
}

$file = $_FILES['file'];
$uploadError = (int) ($file['error'] ?? UPLOAD_ERR_NO_FILE);
if ($uploadError !== UPLOAD_ERR_OK) {
    $messages = [
        UPLOAD_ERR_INI_SIZE => 'O PDF excede o limite do servidor (' . ini_get('upload_max_filesize') . ').',
        UPLOAD_ERR_FORM_SIZE => 'O PDF excede o limite do formulário.',
        UPLOAD_ERR_PARTIAL => 'O upload foi interrompido. Tente novamente.',
        UPLOAD_ERR_NO_FILE => 'Nenhum arquivo enviado.',
        UPLOAD_ERR_NO_TMP_DIR => 'Pasta temporária ausente no servidor.',
        UPLOAD_ERR_CANT_WRITE => 'Falha ao gravar o arquivo no disco.',
        UPLOAD_ERR_EXTENSION => 'Uma extensão do PHP bloqueou o upload.',
    ];
    json_error($messages[$uploadError] ?? 'Falha no upload do arquivo.');
}

$original = (string) ($file['name'] ?? '');
$ext = strtolower(pathinfo($original, PATHINFO_EXTENSION));
if ($ext !== 'pdf') {
    json_error('Envie um arquivo PDF.');
}

if (($file['size'] ?? 0) <= 0) {
    json_error('Arquivo vazio.');
}

$root = dirname(__DIR__);
$venvPython = $root . DIRECTORY_SEPARATOR . '.venv' . DIRECTORY_SEPARATOR . 'Scripts' . DIRECTORY_SEPARATOR . 'python.exe';
$python = is_file($venvPython) ? $venvPython : 'C:\\Python314\\python.exe';
$cli = $root . DIRECTORY_SEPARATOR . 'split_cli.py';

if (!is_file($python)) {
    $python = 'python';
}

$tmpDir = sys_get_temp_dir();
$inPath = tempnam($tmpDir, 'ss_in_');
$outPath = tempnam($tmpDir, 'ss_out_');

if ($inPath === false || $outPath === false) {
    json_error('Não foi possível criar arquivos temporários.', 500);
}

$pdfPath = $inPath . '.pdf';
$zipPath = $outPath . '.zip';
@unlink($inPath);
@unlink($outPath);

if (!move_uploaded_file((string) $file['tmp_name'], $pdfPath)) {
    json_error('Não foi possível salvar o upload.', 500);
}

$cmd = escapeshellarg($python) . ' ' . escapeshellarg($cli) . ' ' . escapeshellarg($pdfPath) . ' ' . escapeshellarg($zipPath) . ' 2>&1';
$output = [];
$exitCode = 0;
exec($cmd, $output, $exitCode);
$joined = trim(implode("\n", $output));

@unlink($pdfPath);

if ($exitCode !== 0 || !is_file($zipPath)) {
    @unlink($zipPath);
    $decoded = json_decode($joined, true);
    $message = is_array($decoded) && isset($decoded['error'])
        ? (string) $decoded['error']
        : ($joined !== '' ? $joined : 'Falha ao processar o PDF.');
    json_error($message, 500);
}

$stem = pathinfo($original, PATHINFO_FILENAME);
$stem = preg_replace('/[^\w\-]+/u', '_', (string) $stem) ?: 'recibos';
$downloadName = $stem . '_recibos.zip';

header('Content-Type: application/zip');
header('Content-Length: ' . (string) filesize($zipPath));
header('Content-Disposition: attachment; filename="' . $downloadName . '"');
header('Cache-Control: no-store');

readfile($zipPath);
@unlink($zipPath);
exit;
