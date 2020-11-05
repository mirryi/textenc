import "core-js/stable";
import "regenerator-runtime/runtime";

class Renderer {
  pdf: pdfjs.PDFDocumentProxy;
  canvas: HTMLCanvasElement;
  ctx: CanvasRenderingContext2D;

  rendering: boolean;
  pending: number | null;
  pageN: number;
  scale: number;

  constructor(pdf: pdfjs.PDFDocumentProxy, canvas: HTMLCanvasElement) {
    this.pdf = pdf;

    this.canvas = canvas;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      throw new Error('could not get context of canvas');
    }
    this.ctx = ctx;

    this.rendering = false;
    this.pending = null;
    this.pageN = 1;
    this.scale = 2;
  }

  async render() {
    this.rendering = false;
    const page = await this.pdf.getPage(this.pageN);
    const viewport = page.getViewport({scale: this.scale});
    this.canvas.width = viewport.width;
    this.canvas.height = viewport.height;

    const renderContext = {
      canvasContext: this.ctx,
      viewport: viewport,
    };

    await page.render(renderContext).promise;
    this.rendering = false;
    if (this.pending !== null) {
      await this.render();
      this.pending = null;
    }
  }

  async queuePage(n: number) {
    if (this.rendering) {
      this.pending = n;
    } else {
      this.pageN = n;
      await this.render();
    }
  }
}


async function main() {
  const pdfjs = await import("pdfjs-dist/build/pdf.js");
  const pdfjsWorker = await import("pdfjs-dist/build/pdf.worker.js");
  pdfjs.GlobalWorkerOptions.workerPort = new pdfjsWorker();
  
  const pdf = await pdfjs.getDocument('presentation.pdf').promise;
  const canvas = document.getElementById('canvas') as HTMLCanvasElement | null;
  if (!canvas) {
    return;
  }

  const renderer = new Renderer(pdf, canvas);
  renderer.render();
}

main();
