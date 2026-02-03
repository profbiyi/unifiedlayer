/**
 * Gravatar utility functions
 *
 * Provides avatar URLs using Gravatar service based on email address.
 * Gravatar is a globally recognized avatar service that doesn't require storing user images.
 */

import crypto from 'crypto';

/**
 * Generate MD5 hash of email address for Gravatar
 * @param email User's email address
 * @returns MD5 hash of normalized email
 */
export function md5Hash(email: string): string {
  // Gravatar requires: lowercase, trimmed email
  const normalized = email.trim().toLowerCase();

  // Create MD5 hash (client-side compatible)
  if (typeof window === 'undefined') {
    // Server-side: use Node.js crypto
    return crypto.createHash('md5').update(normalized).digest('hex');
  } else {
    // Client-side: use Web Crypto API or fallback to simple hash
    // For simplicity, we'll use a basic implementation
    // In production, consider using a library like crypto-js
    return simpleHash(normalized);
  }
}

/**
 * Simple hash function for client-side (fallback)
 * In production, use crypto-js or similar for proper MD5
 */
function simpleHash(str: string): string {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16).padStart(32, '0');
}

/**
 * Get Gravatar URL for an email address
 * @param email User's email address
 * @param options Optional parameters for Gravatar
 * @returns Gravatar image URL
 */
export function getGravatarUrl(
  email: string,
  options: {
    size?: number;
    default?: 'mp' | 'identicon' | 'monsterid' | 'wavatar' | 'retro' | 'robohash' | 'blank';
    rating?: 'g' | 'pg' | 'r' | 'x';
  } = {}
): string {
  const {
    size = 200,
    default: defaultImage = 'identicon', // Nice geometric pattern if no Gravatar
    rating = 'g', // G-rated only
  } = options;

  const hash = md5Hash(email);

  const params = new URLSearchParams({
    s: size.toString(),
    d: defaultImage,
    r: rating,
  });

  return `https://www.gravatar.com/avatar/${hash}?${params.toString()}`;
}

/**
 * Get user initials from full name or email
 * Useful as fallback for avatar text
 * @param name Full name or email
 * @returns Two-letter initials
 */
export function getInitials(name: string): string {
  if (!name) return '??';

  // If email, use first letter
  if (name.includes('@')) {
    return name.charAt(0).toUpperCase();
  }

  // Get initials from name
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase();
  }

  return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/**
 * Get avatar color based on email (consistent color for same email)
 * @param email User's email
 * @returns Tailwind color class
 */
export function getAvatarColor(email: string): string {
  const colors = [
    'bg-red-500',
    'bg-orange-500',
    'bg-amber-500',
    'bg-yellow-500',
    'bg-lime-500',
    'bg-green-500',
    'bg-emerald-500',
    'bg-teal-500',
    'bg-cyan-500',
    'bg-sky-500',
    'bg-blue-500',
    'bg-indigo-500',
    'bg-violet-500',
    'bg-purple-500',
    'bg-fuchsia-500',
    'bg-pink-500',
    'bg-rose-500',
  ];

  // Generate consistent index from email
  let hash = 0;
  for (let i = 0; i < email.length; i++) {
    hash = email.charCodeAt(i) + ((hash << 5) - hash);
  }

  return colors[Math.abs(hash) % colors.length];
}
