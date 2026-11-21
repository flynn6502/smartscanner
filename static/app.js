(() => {
  const form = document.getElementById("upload-form");
  const input = document.getElementById("file-input");
  const dropTarget = document.getElementById("drop-target");
  const fileLabel = document.getElementById("file-label");
  const submitBtn = document.getElementById("submit-btn");
  const meterBar = document.getElementById("meter-bar");
  const errorEl = document.getElementById("error");

  const idle = document.getElementById("scanner-idle");
  const ready = document.getElementById("scanner-ready");
  const busy = document.getElementById("scanner-busy");
  const done = document.getElementById("scanner-done");

  const views = { idle, ready, busy, done };

  function showView(name) {
    Object.entries(views).forEach(([key, el]) => {
      el.hidden = key !== name;
    });
  }

  function showError(message) {
    errorEl.hidden = false;
    errorEl.textContent = message;
  }

  function hideError() {
    errorEl.hidden = true;
    errorEl.textContent = "";
  }

  function setFile(file) {
    if (!file) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      showError("Envie um arquivo PDF.");
      return;
    }
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    fileLabel.textContent = file.name;
    submitBtn.disabled = false;
    form.classList.remove("is-scanning", "is-done");
    meterBar.style.width = "0%";
    showView("ready");
    hideError();
  }

  dropTarget.addEventListener("click", () => {
    if (form.classList.contains("is-scanning")) return;
    input.click();
  });

  dropTarget.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!form.classList.contains("is-scanning")) input.click();
    }
  });

  input.addEventListener("change", () => {
    if (input.files?.[0]) setFile(input.files[0]);
  });

  ["dragenter", "dragover"].forEach((evt) => {
    form.addEventListener(evt, (e) => {
      e.preventDefault();
      if (!form.classList.contains("is-scanning")) form.classList.add("is-dragover");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    form.addEventListener(evt, (e) => {
      e.preventDefault();
      form.classList.remove("is-dragover");
    });
  });

  form.addEventListener("drop", (e) => {
    const file = e.dataTransfer?.files?.[0];
    if (file) setFile(file);
  });

  function animateMeter(target, duration) {
    return new Promise((resolve) => {
      const start = performance.now();
      const from = parseFloat(meterBar.style.width) || 0;

      function tick(now) {
        const t = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - t, 3);
        meterBar.style.width = `${from + (target - from) * eased}%`;
        if (t < 1) requestAnimationFrame(tick);
        else resolve();
      }

      requestAnimationFrame(tick);
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = input.files?.[0];
    if (!file) {
      showError("Selecione um arquivo PDF.");
      return;
    }

    hideError();
    submitBtn.disabled = true;
    form.classList.add("is-scanning");
    form.classList.remove("is-done");
    showView("busy");
    meterBar.style.width = "0%";

    const body = new FormData();
    body.append("file", file);

    const apiUrl = form.dataset.api || "api/split.php";
    const progress = animateMeter(72, 1400);

    try {
      const res = await fetch(apiUrl, { method: "POST", body });
      await progress;

      if (!res.ok) {
        let message = "Não foi possível processar o PDF.";
        try {
          const data = await res.json();
          if (data?.error) message = data.error;
        } catch {
          /* ignore */
        }
        throw new Error(message);
      }

      await animateMeter(100, 280);

      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") || "";
      const match = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
      const filename = match
        ? decodeURIComponent(match[1].replace(/['"]/g, ""))
        : "recibos.zip";

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      form.classList.remove("is-scanning");
      form.classList.add("is-done");
      showView("done");

      window.setTimeout(() => {
        form.classList.remove("is-done");
        meterBar.style.width = "0%";
        showView(input.files?.length ? "ready" : "idle");
        submitBtn.disabled = !input.files?.length;
      }, 1600);
    } catch (err) {
      form.classList.remove("is-scanning");
      meterBar.style.width = "0%";
      showView(input.files?.length ? "ready" : "idle");
      showError(err.message || "Erro inesperado.");
      submitBtn.disabled = !input.files?.length;
    }
  });
})();
