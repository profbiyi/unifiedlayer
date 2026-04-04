"use client";

import { motion } from "framer-motion";
import { staggerContainer, staggerItem, hoverLift, tapScale } from "@/lib/animations";
import { getPopularSources } from "@/lib/connector-icons";
import { ArrowRight, Plug } from "lucide-react";
import Link from "next/link";

/**
 * Quick Connect section for the dashboard.
 * Shows popular connector cards that link directly to /connect?source=<id>.
 * Only renders when the user has fewer than 3 sources (for new users).
 */
export default function QuickConnect() {
  const popular = getPopularSources();

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Plug className="h-5 w-5 text-primary" />
          <h3 className="font-semibold">Quick Connect</h3>
        </div>
        <Link
          href="/connect"
          className="flex items-center gap-1 text-sm text-primary hover:underline"
        >
          View all
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4"
      >
        {popular.map((connector) => {
          const Icon = connector.icon;
          return (
            <motion.div key={connector.id} variants={staggerItem}>
              <Link href={`/connect?source=${connector.id}`}>
                <motion.div
                  whileHover={hoverLift}
                  whileTap={tapScale}
                  className="group flex items-center gap-3 rounded-xl border p-4 transition-all hover:border-primary/30 hover:bg-accent/50 hover:shadow-sm cursor-pointer"
                >
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${connector.color} shadow-sm`}>
                    <Icon className={`h-5 w-5 ${connector.textColor}`} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">
                      Connect {connector.name}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {connector.description}
                    </p>
                  </div>
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </motion.div>
              </Link>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
}
