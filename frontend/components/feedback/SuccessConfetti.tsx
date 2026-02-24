"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface Particle {
  id: number;
  x: number;
  y: number;
  rotation: number;
  color: string;
  scale: number;
  shape: "square" | "circle" | "triangle";
}

const COLORS = [
  "#6366f1", // indigo
  "#8b5cf6", // violet
  "#a855f7", // purple
  "#22c55e", // green
  "#eab308", // yellow
  "#f97316", // orange
  "#ec4899", // pink
  "#06b6d4", // cyan
];

interface SuccessConfettiProps {
  isActive: boolean;
  onComplete?: () => void;
  duration?: number;
  particleCount?: number;
}

export function SuccessConfetti({
  isActive,
  onComplete,
  duration = 3000,
  particleCount = 50,
}: SuccessConfettiProps) {
  const [particles, setParticles] = useState<Particle[]>([]);

  const generateParticles = useCallback(() => {
    const newParticles: Particle[] = [];
    const shapes: Array<"square" | "circle" | "triangle"> = ["square", "circle", "triangle"];

    for (let i = 0; i < particleCount; i++) {
      newParticles.push({
        id: i,
        x: Math.random() * 100,
        y: -10 - Math.random() * 20,
        rotation: Math.random() * 360,
        color: COLORS[Math.floor(Math.random() * COLORS.length)],
        scale: 0.5 + Math.random() * 0.5,
        shape: shapes[Math.floor(Math.random() * shapes.length)],
      });
    }
    return newParticles;
  }, [particleCount]);

  useEffect(() => {
    if (isActive) {
      setParticles(generateParticles());
      const timer = setTimeout(() => {
        setParticles([]);
        onComplete?.();
      }, duration);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [isActive, duration, generateParticles, onComplete]);

  const renderShape = (shape: "square" | "circle" | "triangle", color: string) => {
    switch (shape) {
      case "circle":
        return (
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: color }}
          />
        );
      case "triangle":
        return (
          <div
            className="w-0 h-0"
            style={{
              borderLeft: "6px solid transparent",
              borderRight: "6px solid transparent",
              borderBottom: `10px solid ${color}`,
            }}
          />
        );
      default:
        return (
          <div
            className="w-3 h-3"
            style={{ backgroundColor: color }}
          />
        );
    }
  };

  return (
    <AnimatePresence>
      {particles.length > 0 && (
        <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
          {particles.map((particle) => (
            <motion.div
              key={particle.id}
              initial={{
                x: `${particle.x}vw`,
                y: `${particle.y}vh`,
                rotate: particle.rotation,
                scale: particle.scale,
                opacity: 1,
              }}
              animate={{
                y: "110vh",
                rotate: particle.rotation + 720,
                opacity: [1, 1, 0],
              }}
              exit={{ opacity: 0 }}
              transition={{
                duration: 2 + Math.random() * 2,
                ease: [0.25, 0.1, 0.25, 1],
              }}
              className="absolute"
            >
              {renderShape(particle.shape, particle.color)}
            </motion.div>
          ))}
        </div>
      )}
    </AnimatePresence>
  );
}

// Hook to manage confetti state
export function useConfetti() {
  const [isActive, setIsActive] = useState(false);

  const trigger = useCallback(() => {
    setIsActive(true);
  }, []);

  const reset = useCallback(() => {
    setIsActive(false);
  }, []);

  return { isActive, trigger, reset };
}

// Compact success animation with checkmark
interface SuccessCheckmarkProps {
  isVisible: boolean;
  size?: "sm" | "md" | "lg";
  onComplete?: () => void;
}

export function SuccessCheckmark({
  isVisible,
  size = "md",
  onComplete,
}: SuccessCheckmarkProps) {
  const sizeClasses = {
    sm: "w-12 h-12",
    md: "w-16 h-16",
    lg: "w-24 h-24",
  };

  const checkSizes = {
    sm: { strokeWidth: 3, pathLength: 20 },
    md: { strokeWidth: 3, pathLength: 24 },
    lg: { strokeWidth: 4, pathLength: 32 },
  };

  useEffect(() => {
    if (isVisible && onComplete) {
      const timer = setTimeout(onComplete, 1500);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [isVisible, onComplete]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className={`${sizeClasses[size]} rounded-full bg-success flex items-center justify-center`}
        >
          <motion.svg
            viewBox="0 0 24 24"
            fill="none"
            className="w-1/2 h-1/2"
          >
            <motion.path
              d="M5 12l5 5L19 7"
              stroke="white"
              strokeWidth={checkSizes[size].strokeWidth}
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
            />
          </motion.svg>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default SuccessConfetti;
