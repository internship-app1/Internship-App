const UTM_KEY = 'iam_utm';
const UTM_PARAMS = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'] as const;

export type UTMData = {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_content?: string;
  utm_term?: string;
  first_seen_at: string;
};

/** Read UTM params from the URL and write to localStorage (first-touch only — never overwrites). */
export function captureUTM(search: string): void {
  if (localStorage.getItem(UTM_KEY)) return;
  const params = new URLSearchParams(search);
  if (!UTM_PARAMS.some(p => params.has(p))) return;
  const data: UTMData = { first_seen_at: new Date().toISOString() };
  UTM_PARAMS.forEach(p => {
    const v = params.get(p);
    if (v) (data as Record<string, string>)[p] = v;
  });
  localStorage.setItem(UTM_KEY, JSON.stringify(data));
}

export function getStoredUTM(): UTMData | null {
  const raw = localStorage.getItem(UTM_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export function clearUTM(): void {
  localStorage.removeItem(UTM_KEY);
}
