import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RagBatchUpload } from "./Admin";
import type { Api } from "./api";

const registry = { sources: [
  { source_id:"SRC_ONE",source_title:"Registered source",source_type:"Training",source_owner:"Test owner",mapped_skill_ids:["RD_A"],availability_status:"Content not supplied" },
  { source_id:"SRC_AMBIG",source_title:"Ambiguous source",source_type:"SOP",source_owner:"Test owner",mapped_skill_ids:["RD_A","RD_B"],availability_status:"Content not supplied" },
], skill_ids:["RD_A","RD_B"], limits:{maximum_files:20,maximum_file_bytes:1000,maximum_batch_bytes:5000} };

describe("bulk RAG upload", () => {
  it("reviews and ingests multiple files with per-file mappings", async () => {
    const api = vi.fn(async (path: string, _method?: string, body?: unknown) => {
      if (path === "/rag/source-registry") return registry;
      if (path === "/rag/batch/validate") {
        const files=(body as {files:{client_id:string}[]}).files;
        return {files:files.map((file)=>({...file,validation_status:"Ready"}))};
      }
      if (path === "/rag/batch/upload") {
        const metadata=JSON.parse((body as FormData).get("metadata") as string);
        return {selected_count:2,successfully_ingested:2,duplicates_skipped:0,pending_validation:0,failed:0,
          files:metadata.map((file:{client_id:string})=>({...file,validation_status:"Ingested"}))};
      }
      throw new Error(`Unexpected ${path}`);
    }) as unknown as Api;
    render(<RagBatchUpload api={api} />); const user=userEvent.setup();
    await waitFor(()=>expect(screen.getByText(/Limits: 20 files/)).toBeInTheDocument());
    const files=[new File(["first"],"one.txt",{type:"text/plain"}),new File(["second"],"two.txt",{type:"text/plain"})];
    await user.upload(screen.getByLabelText("Select source documents"),files);
    const sources=screen.getAllByLabelText(/^Source for /); await user.selectOptions(sources[0],"SRC_ONE"); await user.selectOptions(sources[1],"SRC_ONE");
    const skills=screen.getAllByLabelText(/^Skills for /); await user.selectOptions(skills[0],["RD_A","RD_B"]);
    for (const box of screen.getAllByLabelText(/^Approve /)) await user.click(box);
    await user.click(screen.getByRole("button",{name:"Validate All"})); await waitFor(()=>expect(screen.getAllByText("Ready")).toHaveLength(2));
    await user.click(screen.getByRole("button",{name:"Upload & Ingest All"}));
    await waitFor(()=>expect(screen.getByText(/Ingested 2/)).toBeInTheDocument());
  });

  it("does not guess an ambiguous mapping", async () => {
    const api=vi.fn(async (path:string)=>path==="/rag/source-registry"?registry:{files:[]}) as unknown as Api;
    render(<RagBatchUpload api={api} />); const user=userEvent.setup(); await waitFor(()=>screen.getByText(/Limits: 20 files/));
    await user.upload(screen.getByLabelText("Select source documents"),new File(["x"],"ambiguous.txt"));
    await user.selectOptions(screen.getByLabelText("Source for ambiguous.txt"),"SRC_AMBIG");
    expect(screen.getByText("Mapping required")).toBeInTheDocument();
  });
});
