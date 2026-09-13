import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RagBatchUpload } from "./Admin";
import { ApiError, type Api } from "./api";

const registry = { sources: [
  { source_id:"SRC_ONE",source_title:"Registered source",source_type:"Training",source_owner:"Test owner",mapped_skill_ids:["RD_A"],availability_status:"Content not supplied" },
  { source_id:"SRC_AMBIG",source_title:"Ambiguous source",source_type:"SOP",source_owner:"Test owner",mapped_skill_ids:["RD_A","RD_B"],availability_status:"Content not supplied" },
], skill_ids:["RD_A","RD_B"], skills:[{skill_id:"RD_A",skill_name:"Alpha skill"},{skill_id:"RD_B",skill_name:"Beta skill"}], limits:{maximum_files:20,maximum_file_bytes:1000,maximum_batch_bytes:5000} };

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
    const skills=screen.getAllByRole("group",{name:/Skills for /}); await user.click(within(skills[0]).getByLabelText(/RD_B — Beta skill/));
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

  it("keeps successful rows visible beside failed, duplicate and pending rows", async () => {
    const statuses=["Ingested","Failed","Duplicate skipped","Pending source validation"];
    const api=vi.fn(async (path:string,_method?:string,body?:unknown)=>{
      if(path==="/rag/source-registry") return registry;
      const metadata=JSON.parse((body as FormData).get("metadata") as string);
      return {selected_count:4,successfully_ingested:1,duplicates_skipped:1,pending_validation:1,failed:1,
        files:metadata.map((file:{client_id:string},index:number)=>({...file,validation_status:statuses[index]}))};
    }) as unknown as Api;
    render(<RagBatchUpload api={api}/>); const user=userEvent.setup(); await waitFor(()=>screen.getByText(/Limits: 20 files/));
    await user.upload(screen.getByLabelText("Select source documents"),["a","b","c","d"].map((name)=>new File([name],`${name}.txt`)));
    for(const select of screen.getAllByLabelText(/^Source for /)) await user.selectOptions(select,"SRC_ONE");
    for(const box of screen.getAllByLabelText(/^Approve /)) await user.click(box);
    await user.click(screen.getByRole("button",{name:"Upload & Ingest All"}));
    await waitFor(()=>expect(screen.getByText(/Ingested 1.*Duplicates 1.*Pending 1.*Failed 1/)).toBeInTheDocument());
    for(const status of statuses) expect(screen.getAllByText(status).length).toBeGreaterThan(0);
  });

  it("shows authorization failures and allows removal before upload", async () => {
    const api=vi.fn(async (path:string)=>{ if(path==="/rag/source-registry") return registry; throw new ApiError(403,"Your role does not have access to this action."); }) as unknown as Api;
    render(<RagBatchUpload api={api}/>); const user=userEvent.setup(); await waitFor(()=>screen.getByText(/Limits: 20 files/));
    await user.upload(screen.getByLabelText("Select source documents"),[new File(["a"],"a.txt"),new File(["b"],"b.txt")]);
    await user.click(screen.getAllByRole("button",{name:"Remove"})[0]); expect(screen.queryByText("a.txt")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button",{name:"Validate All"}));
    await waitFor(()=>expect(screen.getByText(/does not have access/)).toBeInTheDocument());
  });
});
