import { Variants } from "framer-motion";

// Page transition variants
export const pageTransition: Variants = {
  initial: {
    opacity: 0,
    y: 8,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.25,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: {
      duration: 0.2,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
};

// Fade animations
export const fadeIn: Variants = {
  initial: {
    opacity: 0,
  },
  animate: {
    opacity: 1,
    transition: {
      duration: 0.2,
      ease: "easeOut",
    },
  },
  exit: {
    opacity: 0,
    transition: {
      duration: 0.15,
      ease: "easeIn",
    },
  },
};

export const fadeOut: Variants = {
  initial: {
    opacity: 1,
  },
  animate: {
    opacity: 0,
    transition: {
      duration: 0.15,
      ease: "easeIn",
    },
  },
};

// Slide animations
export const slideUp: Variants = {
  initial: {
    opacity: 0,
    y: 10,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.25,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: {
      duration: 0.2,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
};

export const slideDown: Variants = {
  initial: {
    opacity: 0,
    y: -10,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.25,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
  exit: {
    opacity: 0,
    y: 10,
    transition: {
      duration: 0.2,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
};

// Scale animations for modals and dialogs
export const scaleIn: Variants = {
  initial: {
    opacity: 0,
    scale: 0.95,
  },
  animate: {
    opacity: 1,
    scale: 1,
    transition: {
      duration: 0.2,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: {
      duration: 0.15,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
};

// Stagger children animation
export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
};

export const staggerItem: Variants = {
  initial: {
    opacity: 0,
    y: 8,
  },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.2,
      ease: [0.25, 0.1, 0.25, 1],
    },
  },
};

// Hover animations
export const hoverLift = {
  scale: 1.02,
  y: -2,
  transition: {
    duration: 0.2,
    ease: "easeOut",
  },
};

export const hoverScale = {
  scale: 1.05,
  transition: {
    duration: 0.15,
    ease: "easeOut",
  },
};

// Tap/press animations
export const tapScale = {
  scale: 0.98,
  transition: {
    duration: 0.1,
    ease: "easeInOut",
  },
};

// Progress bar animation
export const progressBar: Variants = {
  initial: {
    scaleX: 0,
    originX: 0,
  },
  animate: {
    scaleX: 1,
    transition: {
      duration: 0.5,
      ease: "easeInOut",
    },
  },
};

// Skeleton loading pulse
export const skeletonPulse: Variants = {
  initial: {
    opacity: 0.5,
  },
  animate: {
    opacity: 1,
    transition: {
      duration: 0.8,
      repeat: Infinity,
      repeatType: "reverse",
      ease: "easeInOut",
    },
  },
};
