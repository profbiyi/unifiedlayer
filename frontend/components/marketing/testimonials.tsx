"use client";

import { useEffect, useState } from "react";
import { Quote } from "lucide-react";

interface PublicTestimonial {
  id: number;
  quote: string;
  attribution: string;
}

/**
 * Testimonials from trial participants. Only approved testimonials whose
 * authors ticked the publishing consent are returned by the API. Renders
 * nothing until at least one exists, so the home page is unchanged until then.
 */
export function Testimonials() {
  const [items, setItems] = useState<PublicTestimonial[]>([]);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/trial-feedback/testimonials`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => setItems(Array.isArray(data) ? data : []))
      .catch(() => setItems([]));
  }, []);

  if (!items.length) return null;

  return (
    <section className="border-t py-20 md:py-28">
      <div className="container">
        <div className="mx-auto mb-12 max-w-2xl text-center">
          <h2 className="mb-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">
            From teams who trialled UnifiedLayer
          </h2>
        </div>
        <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-2 lg:grid-cols-3">
          {items.slice(0, 6).map((t) => (
            <figure key={t.id} className="flex flex-col rounded-xl border bg-card p-6 shadow-sm">
              <Quote className="mb-3 h-6 w-6 text-primary/60" aria-hidden />
              <blockquote className="flex-1 text-base leading-relaxed">{t.quote}</blockquote>
              <figcaption className="mt-4 text-sm text-muted-foreground">{t.attribution}</figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}
