const PREFIX = "barongsai_";

export function getItem<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function getString(key: string, fallback: string): string {
  return localStorage.getItem(PREFIX + key) ?? fallback;
}

export function setItem(key: string, value: unknown): void {
  try {
    localStorage.setItem(
      PREFIX + key,
      typeof value === "string" ? value : JSON.stringify(value),
    );
  } catch (e) {
    console.warn("storage.setItem:", e);
  }
}

export function removeItem(key: string): void {
  localStorage.removeItem(PREFIX + key);
}
