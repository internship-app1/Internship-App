import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/react';
import { API_BASE_URL } from '../lib/api';

export interface UsageData {
  tailor_resume: {
    limit: number;
    used: number;
    remaining: number;
    reset_at: string | null;
    window_days: number;
  };
}

export function useUsage() {
  const { isSignedIn, getToken } = useAuth();
  const [data, setData] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchUsage = useCallback(async () => {
    if (!isSignedIn) return;
    setLoading(true);
    setError('');
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE_URL}/api/usage`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const json: UsageData = await res.json();
      setData(json);
    } catch (e: any) {
      setError(e.message ?? 'Failed to load usage.');
    } finally {
      setLoading(false);
    }
  }, [isSignedIn, getToken]);

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  return { data, loading, error, refetch: fetchUsage };
}
