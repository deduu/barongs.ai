export function MessageSkeleton() {
  return (
    <div className="mb-6 animate-fade-in" role="status" aria-label="Loading message">
      {/* Avatar + name skeleton */}
      <div className="mb-2 flex items-center gap-2">
        <div className="h-7 w-7 rounded-lg shimmer" />
        <div className="h-3 w-20 rounded shimmer" />
      </div>

      {/* Text line skeletons */}
      <div className="space-y-2">
        <div className="h-3.5 w-full rounded shimmer" />
        <div className="h-3.5 w-[85%] rounded shimmer" />
        <div className="h-3.5 w-[60%] rounded shimmer" />
      </div>
    </div>
  );
}
