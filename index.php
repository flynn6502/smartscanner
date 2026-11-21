<?php
declare(strict_types=1);

$base = rtrim(str_replace('\\', '/', dirname($_SERVER['SCRIPT_NAME'] ?? '')), '/');
if ($base === '' || $base === '/') {
    $base = '';
}
?><!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SmartScanner</title>
  <link rel="icon" href="<?= htmlspecialchars($base, ENT_QUOTES) ?>/static/logo-blue.png" type="image/png" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" />
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="<?= htmlspecialchars($base, ENT_QUOTES) ?>/static/style.css" />
</head>
<body>
  <div class="ambient" aria-hidden="true">
    <div class="ambient__orb ambient__orb--a"></div>
    <div class="ambient__orb ambient__orb--b"></div>
    <div class="ambient__grid"></div>
  </div>

  <div class="app min-vh-100 d-flex flex-column">
    <nav class="navbar px-3 px-md-4 py-3">
      <a class="navbar-brand d-flex align-items-center gap-2 m-0" href="<?= htmlspecialchars($base !== '' ? $base . '/' : './', ENT_QUOTES) ?>">
        <span class="logo-wrap">
          <img src="<?= htmlspecialchars($base, ENT_QUOTES) ?>/static/logo-blue.png" alt="" class="logo-img" width="36" height="36" />
        </span>
        <span class="brand-name">SmartScanner</span>
      </a>
    </nav>

    <main class="flex-grow-1 d-flex align-items-center justify-content-center px-3 pb-5">
      <div class="stage w-100">
       
        <form id="upload-form" class="scanner-card mx-auto" enctype="multipart/form-data" data-api="<?= htmlspecialchars($base, ENT_QUOTES) ?>/api/split.php">
          <input id="file-input" type="file" name="file" accept="application/pdf,.pdf" hidden />

          <div
            id="drop-target"
            class="scanner-bed"
            tabindex="0"
            role="button"
            aria-label="Selecionar PDF"
          >
            <div class="scanner-bed__glass"></div>
            <div class="scan-beam" aria-hidden="true"></div>

            <div class="scanner-idle" id="scanner-idle">
              <div class="paper-stack" aria-hidden="true">
                <span class="paper paper--1"></span>
                <span class="paper paper--2"></span>
                <span class="paper paper--3"></span>
              </div>
              <p class="scanner-cta mb-0">Solte aqui o PDF para separar recibos</p>
            </div>

            <div class="scanner-ready" id="scanner-ready" hidden>
              <div class="ready-chip">
                <i class="bi bi-file-earmark-pdf-fill"></i>
                <span id="file-label"></span>
              </div>
            </div>

            <div class="scanner-busy" id="scanner-busy" hidden>
              <div class="busy-ring"></div>
              <span class="busy-label">Separando</span>
            </div>

            <div class="scanner-done" id="scanner-done" hidden>
              <div class="done-burst" aria-hidden="true">
                <span></span><span></span><span></span><span></span>
                <span></span><span></span><span></span><span></span>
              </div>
              <i class="bi bi-check-lg done-check"></i>
            </div>
          </div>

          <div class="scanner-footer d-flex align-items-center justify-content-between gap-3">
            <div class="meter" id="meter" aria-hidden="true">
              <span class="meter__bar" id="meter-bar"></span>
            </div>
            <button type="submit" class="btn btn-scan" id="submit-btn" disabled>
              <span class="btn-scan__label">Separar</span>
              <i class="bi bi-arrow-right-short"></i>
            </button>
          </div>
        </form>

        <div id="error" class="alert alert-danger border-0 shadow-sm mt-3 mx-auto error-toast" role="alert" hidden></div>
      </div>
    </main>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="<?= htmlspecialchars($base, ENT_QUOTES) ?>/static/app.js"></script>
</body>
</html>
