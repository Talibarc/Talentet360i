import { describe, it, expect, vi } from "vitest";
import { createApi, ApiError, safeUrl } from "./api";
describe("central API client", () => {
  it("sends the selected identity and JSON payload", async () => {
    const fetcher = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response('{"id":97}', { status: 201 }));
    expect(
      await createApi(418)("/evidence", "POST", { title: "Synthetic" }),
    ).toEqual({ id: 97 });
    expect(fetcher).toHaveBeenCalledWith(
      "/api/evidence",
      expect.objectContaining({
        method: "POST",
        headers: {
          "x-demo-user-id": "418",
          "Content-Type": "application/json",
        },
        body: '{"title":"Synthetic"}',
      }),
    );
  });
  it("omits identity for discovery", async () => {
    const fetcher = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response("{}"));
    await createApi(null)("/demo/identities");
    expect(fetcher.mock.calls[0][1]?.headers).toEqual({});
  });
  it.each([401, 403, 404, 409, 422])(
    "handles status %s with actionable detail",
    async (status) => {
      vi.spyOn(globalThis, "fetch").mockResolvedValue(
        new Response('{"detail":"Synthetic error"}', { status }),
      );
      await expect(createApi(91)("/test")).rejects.toMatchObject({
        status,
        message: expect.stringContaining("Synthetic error"),
      });
    },
  );
  it("formats field validation and network errors", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          '{"detail":[{"loc":["body","comment"],"msg":"Required"}]}',
          { status: 422 },
        ),
      )
      .mockRejectedValueOnce(new TypeError("fetch failed"));
    await expect(createApi(99)("/test")).rejects.toThrow("comment: Required");
    await expect(createApi(99)("/test")).rejects.toBeInstanceOf(ApiError);
  });
  it("only permits supplied HTTP(S) links", () => {
    expect(safeUrl("javascript:alert(1)")).toBeUndefined();
    expect(safeUrl("file:///secret")).toBeUndefined();
    expect(safeUrl("https://example.invalid/course")).toBe(
      "https://example.invalid/course",
    );
    expect(safeUrl(null)).toBeUndefined();
  });
});
