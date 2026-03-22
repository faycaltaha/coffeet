import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="text-6xl">🎁</div>
      <h1 className="text-2xl font-bold text-stone-800 dark:text-stone-100">Page introuvable</h1>
      <p className="text-stone-500 text-sm max-w-xs">
        Cette page n&apos;existe pas ou a été déplacée.
      </p>
      <Link
        href="/"
        className="px-6 py-3 rounded-2xl bg-brand-500 text-white font-semibold shadow-md hover:bg-brand-600 transition-colors"
      >
        Retour à l&apos;accueil
      </Link>
    </div>
  );
}
