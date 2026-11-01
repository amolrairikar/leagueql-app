import { useEffect, useRef, useState } from 'react';

/**
 * Tracks which `[data-section]` heading is active inside the content's own scroll
 * container. Attach the returned `contentRef` to that container.
 */
export function useScrollSpy(initialId: string) {
  const [activeId, setActiveId] = useState(initialId);
  const contentRef = useRef<HTMLDivElement>(null);

  // Scroll-spy against the content's own scroll container (not the viewport):
  // the active section is the last heading scrolled to within the
  // `scroll-mt-24` (96px) jump offset, so a TOC click highlights its target.
  // At the bottom of the content, the last heading in view wins, since
  // trailing short sections can never scroll up to the offset.
  useEffect(() => {
    const container = contentRef.current;
    if (!container) return;
    const headings = Array.from(
      container.querySelectorAll<HTMLElement>('[data-section]'),
    );
    const updateActive = () => {
      const containerRect = container.getBoundingClientRect();
      const atBottom =
        container.scrollTop + container.clientHeight >=
        container.scrollHeight - 2;
      let current = headings[0]?.id;
      for (const heading of headings) {
        const top = heading.getBoundingClientRect().top - containerRect.top;
        const threshold = atBottom ? container.clientHeight : 100;
        if (top <= threshold) current = heading.id;
        else break;
      }
      if (current) setActiveId(current);
    };
    updateActive();
    container.addEventListener('scroll', updateActive, { passive: true });
    return () => container.removeEventListener('scroll', updateActive);
  }, []);

  return { activeId, contentRef };
}
