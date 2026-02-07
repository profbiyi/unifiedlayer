"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ReactNode } from "react";
import { pageTransition } from "@/lib/animations";

interface PageTransitionProps {
  children: ReactNode;
  className?: string;
}

export function PageTransition({ children, className }: PageTransitionProps) {
  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={pageTransition}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// Wrapper for AnimatePresence when you need to animate page changes
interface AnimatedPageProps {
  children: ReactNode;
  pageKey?: string;
}

export function AnimatedPage({ children, pageKey }: AnimatedPageProps) {
  return (
    <AnimatePresence mode="wait">
      <PageTransition key={pageKey}>{children}</PageTransition>
    </AnimatePresence>
  );
}

export default PageTransition;
