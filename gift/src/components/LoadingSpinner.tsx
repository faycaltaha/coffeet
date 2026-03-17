"use client";

import { motion, AnimatePresence } from "framer-motion";

export default function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-7">
      {/* Orbital ring system */}
      <div className="relative w-24 h-24 flex items-center justify-center">
        {/* Outer ring */}
        <motion.div
          className="absolute inset-0 rounded-full border-[2.5px] border-brand-200/60"
          animate={{ rotate: 360 }}
          transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
        >
          <motion.div
            className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-brand-500 shadow-[0_0_10px_2px_rgba(217,70,239,0.6)]"
            animate={{ scale: [1, 1.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
          />
        </motion.div>

        {/* Middle ring — counter-rotate */}
        <motion.div
          className="absolute inset-[14px] rounded-full border-[2px] border-purple-300/70"
          animate={{ rotate: -360 }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "linear" }}
        >
          <motion.div
            className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 w-2.5 h-2.5 rounded-full bg-purple-400 shadow-[0_0_8px_2px_rgba(168,85,247,0.5)]"
            animate={{ scale: [1, 1.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
          />
        </motion.div>

        {/* Inner ring */}
        <motion.div
          className="absolute inset-[28px] rounded-full border-[2px] border-pink-300/60"
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        >
          <motion.div
            className="absolute right-0 top-1/2 translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-pink-400 shadow-[0_0_6px_2px_rgba(244,114,182,0.5)]"
            animate={{ scale: [1, 1.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
          />
        </motion.div>

        {/* Pulsing core */}
        <motion.div
          className="absolute inset-[40px] rounded-full bg-gradient-to-br from-brand-400 to-purple-500"
          animate={{ scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
          style={{ boxShadow: "0 0 20px 4px rgba(192,38,211,0.3)" }}
        />
      </div>

      {/* Animated message */}
      <AnimatePresence mode="wait">
        <motion.p
          key={message}
          className="text-brand-700 font-semibold text-sm text-center px-4"
          initial={{ opacity: 0, y: 10, filter: "blur(4px)" }}
          animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
          exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
          transition={{ duration: 0.35, ease: "easeInOut" }}
        >
          {message ?? "Analyzing profiles…"}
        </motion.p>
      </AnimatePresence>

      {/* Bouncing dots */}
      <div className="flex gap-2">
        {[0, 1, 2, 3].map((i) => (
          <motion.div
            key={i}
            className="w-2 h-2 rounded-full bg-gradient-to-br from-brand-400 to-purple-400"
            animate={{ y: [0, -10, 0], scale: [1, 1.2, 1] }}
            transition={{
              duration: 0.9,
              repeat: Infinity,
              delay: i * 0.15,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>
    </div>
  );
}
