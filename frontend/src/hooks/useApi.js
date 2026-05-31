import { useState, useEffect, useRef, useCallback } from 'react';
import { BASE_URL } from '../constants/teamColors';

export function useApi(url, { pollInterval } = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const fetchData = useCallback(() => {
    if (!url) return;
    fetch(`${BASE_URL}${url}`)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return res.json();
      })
      .then((json) => {
        if (mountedRef.current) {
          setData(json);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error(`Error fetching ${url}:`, err);
        if (mountedRef.current) {
          setError(err.message);
          setLoading(false);
        }
      });
  }, [url]);

  useEffect(() => {
    if (!url) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    fetchData();

    if (!pollInterval) return;
    const id = setInterval(fetchData, pollInterval);
    return () => clearInterval(id);
  }, [url, pollInterval, fetchData]);

  return { data, loading, error };
}
