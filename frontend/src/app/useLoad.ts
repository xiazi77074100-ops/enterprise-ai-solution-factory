import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { useFeedback } from "./feedback";

/** Loads data for a screen; the shared top line shows while it runs. `key` changes trigger a reload. */
export function useLoad<T>(load: () => Promise<T>, key: string) {
  const { track } = useFeedback();
  const [state, setState] = useState<{ key: string; data?: T; error?: ApiError | Error }>({ key });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let alive = true;
    track(load())
      .then((data) => alive && setState({ key, data }))
      .catch((error: Error) => alive && setState({ key, error }));
    return () => {
      alive = false;
    };
    // `load` closes over the same values encoded in `key`
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, version, track]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  const current = state.key === key ? state : { key };
  return { data: current.data, error: current.error, loading: current.data === undefined && !current.error, reload };
}
