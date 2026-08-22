import { useEffect, useRef, useState } from 'react';

import { SLIDES } from '@/features/landing_page/constants';
import { cn } from '@/lib/utils';

const AUTOPLAY_MS = 4200;

/**
 * "See it in action" gallery: a swipeable horizontal scroll-snap carousel of product
 * screenshots with dot indicators, used at every breakpoint. Auto-advances, pausing on
 * pointer interaction and disabled under prefers-reduced-motion.
 */
export function ProductShowcase() {
  const [active, setActive] = useState(0);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(false);
  const reduceRef = useRef(false);

  useEffect(() => {
    reduceRef.current = window.matchMedia(
      '(prefers-reduced-motion: reduce)',
    ).matches;
    if (reduceRef.current) return;

    const timer = setInterval(() => {
      const el = scrollerRef.current;
      if (!el || pausedRef.current) return;
      const width = el.clientWidth;
      if (width === 0) return;
      const current = Math.round(el.scrollLeft / width);
      const next = (current + 1) % SLIDES.length;
      el.scrollTo({ left: next * width, behavior: 'smooth' });
    }, AUTOPLAY_MS);

    return () => clearInterval(timer);
  }, []);

  function goTo(index: number) {
    const el = scrollerRef.current;
    if (!el) return;
    el.scrollTo({
      left: index * el.clientWidth,
      behavior: reduceRef.current ? 'auto' : 'smooth',
    });
  }

  function handleScroll() {
    const el = scrollerRef.current;
    if (!el || el.clientWidth === 0) return;
    const index = Math.round(el.scrollLeft / el.clientWidth);
    if (index !== active) setActive(index);
  }

  return (
    <div
      className="mx-auto max-w-4xl"
      onPointerEnter={() => {
        pausedRef.current = true;
      }}
      onPointerLeave={() => {
        pausedRef.current = false;
      }}
    >
      <div
        ref={scrollerRef}
        onScroll={handleScroll}
        className="flex snap-x snap-mandatory items-center overflow-x-auto overscroll-x-contain [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {SLIDES.map((slide) => (
          <div
            key={slide.title}
            className="min-w-0 shrink-0 basis-full snap-center px-0.5"
          >
            <div className="overflow-hidden rounded-xl border border-border bg-card shadow-xl">
              <img src={slide.image} alt={slide.caption} className="w-full" />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 flex justify-center gap-2">
        {SLIDES.map((slide, i) => (
          <button
            key={slide.title}
            type="button"
            aria-label={`Show ${slide.title}`}
            aria-current={i === active}
            onClick={() => goTo(i)}
            className={cn(
              'h-2 cursor-pointer rounded-full transition-all',
              i === active ? 'w-5 bg-primary' : 'w-2 bg-border hover:bg-ring',
            )}
          />
        ))}
      </div>

      <p className="mt-4 text-center text-sm text-muted-foreground">
        {SLIDES[active].caption}
      </p>
    </div>
  );
}
