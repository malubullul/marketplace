import type { MouseEvent } from "react";
import { Home, ArrowLeft } from "lucide-react";

import { Button } from "@/components/ui/button";

function goBack(event: MouseEvent<HTMLAnchorElement>) {
  // Keep normal link behavior for new tabs, direct visits and external referrers.
  if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  try {
    const previous = new URL(document.referrer);
    if (previous.origin === window.location.origin && previous.href !== window.location.href && window.history.length > 1) {
      event.preventDefault();
      window.history.back();
    }
  } catch {
    // The real href remains a useful fallback even before hydration or without JS.
  }
}

export default function ErrorBlock() {
  return (
    <section aria-labelledby="error-heading" className="flex min-h-svh w-full items-center justify-center bg-background px-6 py-16 text-foreground">
      <div className="mx-auto flex max-w-lg flex-col items-center text-center">
        <span
          className="text-[8rem] leading-none font-semibold tracking-tighter text-foreground tabular-nums select-none sm:text-[11rem]"
          aria-hidden="true"
        >
          404
        </span>
        <h1 id="error-heading" className="-mt-2 font-heading text-2xl font-semibold tracking-tight text-balance sm:text-3xl">
          <span className="sr-only">Error 404. </span>Halaman ini tidak ditemukan
        </h1>
        <p className="mt-3 max-w-sm text-base text-pretty text-muted-foreground">
          Halaman yang kamu cari mungkin sudah dipindahkan atau tidak tersedia.
          Yuk, kembali jelajahi koleksi Anredseller.
        </p>
        <div className="mt-8 flex w-full flex-col gap-3 sm:w-auto sm:flex-row">
          <Button asChild>
            <a href="/">
              <Home data-icon="inline-start" aria-hidden="true" />
              Ke beranda
            </a>
          </Button>
          <Button asChild variant="outline">
            <a href="/produk.html" onClick={goBack}>
              <ArrowLeft data-icon="inline-start" aria-hidden="true" />
              Kembali
            </a>
          </Button>
        </div>
      </div>
    </section>
  );
}
