'use client'

import { useState, useEffect } from 'react'

/**
 * Returns true when the viewport width is less than the given breakpoint (default 768px = md).
 * SSR-safe: defaults to false on the server and during hydration, then updates on the client.
 * Reactive: updates on resize.
 */
export function useIsMobile(breakpoint: number = 768): boolean {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    // window is only available in the browser — never called during SSR
    const check = () => setIsMobile(window.innerWidth < breakpoint)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [breakpoint])

  return isMobile
}
