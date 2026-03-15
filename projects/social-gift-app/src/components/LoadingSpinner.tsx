"use client";

export default function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-4">
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-4 border-brand-200" />
        <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-brand-500 animate-spin" />
      </div>
      <p className="text-brand-700 font-medium text-sm animate-pulse">
        {message ?? "Analyzing profiles…"}
      </p>
    </div>
  );
}
