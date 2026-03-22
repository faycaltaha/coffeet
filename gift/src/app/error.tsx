"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="text-6xl">😕</div>
      <h1 className="text-2xl font-bold text-stone-800 dark:text-stone-100">
        Une erreur est survenue
      </h1>
      <p className="text-stone-500 text-sm max-w-xs">
        {error.message || "Quelque chose s'est mal passé."}
      </p>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="px-5 py-2.5 rounded-2xl bg-brand-500 text-white font-semibold shadow-md hover:bg-brand-600 transition-colors text-sm"
        >
          Réessayer
        </button>
        <Link
          href="/"
          className="px-5 py-2.5 rounded-2xl border border-stone-200 dark:border-stone-700 text-stone-700 dark:text-stone-300 font-semibold text-sm hover:bg-stone-50 dark:hover:bg-stone-800 transition-colors"
        >
          Accueil
        </Link>
      </div>
    </div>
  );
}
