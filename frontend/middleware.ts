import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PRODUCTION_DOMAIN = 'unifiedlayer.io';

/**
 * Next.js middleware for domain redirect and route protection.
 *
 * 1. Redirects Railway URLs to production domain
 * 2. Route protection handled by AuthGuard component (client-side)
 */
export function middleware(request: NextRequest) {
  const host = request.headers.get('host') || '';
  const { pathname, search } = request.nextUrl;

  // Redirect Railway URLs to production domain
  if (host.includes('railway.app') || host.includes('up.railway.app')) {
    const redirectUrl = `https://${PRODUCTION_DOMAIN}${pathname}${search}`;
    return NextResponse.redirect(redirectUrl, { status: 301 });
  }

  // Pass through all other requests
  // Route protection is handled by AuthGuard component
  return NextResponse.next();
}

export const config = {
  // Match all paths for domain redirect
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
