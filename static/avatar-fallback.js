document.addEventListener('error', (event) => {
  const img = event.target;

  if (!(img instanceof HTMLImageElement)) return;
  if (!img.dataset.fallback || img.dataset.fallbackApplied) return;

  img.dataset.fallbackApplied = 'true';
  img.src = img.dataset.fallback;
}, true);
