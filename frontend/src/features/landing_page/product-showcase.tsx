import { useEffect, useRef, useState } from 'react';

import { SLIDES } from '@/features/landing_page/constants';
import { cn } from '@/lib/utils';

const AUTOPLAY_MS = 4200;
const COUNT = SLIDES.length;

// Rendered slides = [clone(last), ...real slides, clone(first)]. The two clones let a
// swipe (or autoplay) continue past either edge; once the scroll settles on a clone we
// silently jump to its identical real slide, giving seamless wraparound in both directions.
const RENDERED = [SLIDES[COUNT - 1], ...SLIDES, SLIDES[0]];

/**
 * "See it in action" gallery: a swipeable horizontal scroll-snap carousel of product
 * screenshots with dot indicators, used at every breakpoint. Auto-advances, pausing on
 * pointer interaction and disabled under prefers-reduced-motion. Swiping wraps around:
 * past the last slide loops to the first, and back from the first loops to the last.
 */
export function ProductShowcase() {
  const [active, setActive] = useState(0);
  const scrollerRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(false);
  const reduceRef = useRef(false);
  const settleRef = useRef<number>(0);

  // Start on the first real slide (index 1), just past the leading clone.
  useEffect(() => {
    const el = scrollerRef.current;
    if (!el || el.clientWidth === 0) return;
    el.scrollLeft = el.clientWidth;
  }, []);

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
      el.scrollTo({ left: (current + 1) * width, behavior: 'smooth' });
    }, AUTOPLAY_MS);

    return () => clearInterval(timer);
  }, []);

  function goTo(index: number) {
    const el = scrollerRef.current;
    if (!el) return;
    // index is a real slide (0..COUNT-1); the leading clone offsets it by one.
    el.scrollTo({
      left: (index + 1) * el.clientWidth,
      behavior: reduceRef.current ? 'auto' : 'smooth',
    });
  }

  function handleScroll() {
    const el = scrollerRef.current;
    if (!el || el.clientWidth === 0) return;
    const width = el.clientWidth;
    const raw = Math.round(el.scrollLeft / width);
    const real = (((raw - 1) % COUNT) + COUNT) % COUNT;
    if (real !== active) setActive(real);

    // Once scrolling settles on a clone, jump instantly to its real counterpart.
    window.clearTimeout(settleRef.current);
    settleRef.current = window.setTimeout(() => {
      const w = el.clientWidth;
      if (w === 0) return;
      const at = Math.round(el.scrollLeft / w);
      if (at === 0) {
        el.scrollLeft = COUNT * w; // leading clone(last) -> real last
      } else if (at === COUNT + 1) {
        el.scrollLeft = w; // trailing clone(first) -> real first
      }
    }, 80);
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
        {RENDERED.map((slide, i) => (
          <div
            key={i}
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
