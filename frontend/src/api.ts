export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}
const messages: Record<number, string> = {
  401: "Select a valid demo identity to continue.",
  403: "Your role does not have access to this action.",
  404: "This record is no longer available.",
  409: "This record changed or is not ready. Refresh and try again.",
  422: "Check the required fields and try again.",
};
export function createApi(userId: number | null) {
  return async function request<T>(
    path: string,
    method = "GET",
    body?: unknown,
    signal?: AbortSignal,
  ): Promise<T> {
    let response: Response;
    try {
      const multipart = body instanceof FormData;
      response = await fetch(`/api${path}`, {
        method,
        signal,
        headers: {
          ...(userId ? { "x-demo-user-id": String(userId) } : {}),
          ...(body !== undefined && !multipart ? { "Content-Type": "application/json" } : {}),
        },
        body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError")
        throw error;
      throw new ApiError(
        0,
        "Cannot reach the local backend. Check that the mock server is running, then retry.",
      );
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail =
        typeof data?.detail === "string"
          ? data.detail
          : Array.isArray(data?.detail)
            ? data.detail
                .map(
                  (item: { loc?: string[]; msg: string }) =>
                    `${item.loc?.slice(1).join(".")}: ${item.msg}`,
                )
                .join("; ")
            : "";
      throw new ApiError(
        response.status,
        [
          messages[response.status],
          detail ||
            (!messages[response.status] ? "Request failed. Please retry." : ""),
        ]
          .filter(Boolean)
          .join(" "),
      );
    }
    return data as T;
  };
}
export type Api = ReturnType<typeof createApi>;
export function safeUrl(value?: string | null) {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}
