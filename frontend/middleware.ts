import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js middleware (currently disabled).
 *
 * NOTE: With cross-origin setup (frontend on :3001, backend on :8000),
 * middleware cannot access HTTPOnly cookies set by the backend.
 *
 * Route protection is handled by:
 * 1. AuthGuard component (client-side redirect)
 * 2. Backend API validation (all endpoints require valid JWT)
 *
 * This provides defense-in-depth:
 * - AuthGuard = UX (prevents unnecessary API calls)
 * - Backend = Security (cannot be bypassed)
 */
export function middleware(request: NextRequest) {
  // Pass through all requests
  // Protection is handled by AuthGuard component
  return NextResponse.next();
}

export const config = {
  matcher: [
    '/overview/:path*',
    '/pipelines/:path*',
    '/sources/:path*',
    '/destinations/:path*',
    '/runs/:path*',
    '/lineage/:path*',
    '/settings/:path*',
  ],
};
