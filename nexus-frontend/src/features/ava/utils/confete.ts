/** Chuva de confete leve (canvas, sem dependência). Respeita "reduzir movimento". */
export function soltarConfete(duracaoMs = 2200) {
  if (typeof window === 'undefined') return;
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return;
  const canvas = document.createElement('canvas');
  canvas.setAttribute('aria-hidden', 'true');
  Object.assign(canvas.style, { position: 'fixed', inset: '0', width: '100vw', height: '100vh', pointerEvents: 'none', zIndex: '9999' });
  document.body.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    canvas.remove();
    return;
  }
  const dpr = window.devicePixelRatio || 1;
  const ajustar = () => {
    canvas.width = window.innerWidth * dpr;
    canvas.height = window.innerHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  ajustar();
  const cores = ['#FFB800', '#2563EB', '#16A34A', '#DC2626', '#7C3AED', '#0891B2', '#F472B6'];
  const largura = window.innerWidth;
  const pecas = Array.from({ length: 160 }, () => ({
    x: largura / 2 + (Math.random() - 0.5) * largura * 0.4,
    y: window.innerHeight * 0.35,
    vx: (Math.random() - 0.5) * 14,
    vy: -Math.random() * 14 - 4,
    w: 6 + Math.random() * 6,
    h: 8 + Math.random() * 8,
    r: Math.random() * Math.PI,
    vr: (Math.random() - 0.5) * 0.3,
    cor: cores[Math.floor(Math.random() * cores.length)],
  }));
  const inicio = performance.now();
  const quadro = (t: number) => {
    const passou = t - inicio;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const alfa = Math.max(0, 1 - Math.max(0, passou - duracaoMs * 0.6) / (duracaoMs * 0.4));
    for (const p of pecas) {
      p.vy += 0.35;
      p.vx *= 0.99;
      p.x += p.vx;
      p.y += p.vy;
      p.r += p.vr;
      ctx.save();
      ctx.globalAlpha = alfa;
      ctx.translate(p.x, p.y);
      ctx.rotate(p.r);
      ctx.fillStyle = p.cor;
      ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
      ctx.restore();
    }
    if (passou < duracaoMs) requestAnimationFrame(quadro);
    else canvas.remove();
  };
  requestAnimationFrame(quadro);
}
