import { useEffect, useState } from "react";
import type { Api } from "./api";
export function useResource<T>(api: Api, path: string, version = 0) {
  const [state, setState] = useState<{
    data?: T;
    error?: string;
    loading: boolean;
    key?: string;
  }>({ loading: true });
  useEffect(() => {
    const controller = new AbortController();
    api<T>(path, "GET", undefined, controller.signal)
      .then((data) =>
        setState({ data, loading: false, key: `${path}:${version}` }),
      )
      .catch((error) => {
        if (!controller.signal.aborted)
          setState({
            error: error.message,
            loading: false,
            key: `${path}:${version}`,
          });
      });
    return () => controller.abort();
  }, [api, path, version]);
  return state.key === `${path}:${version}` ? state : { loading: true };
}
