import { cloneElement, useEffect, useId, useRef, useState } from "react";
import type { ReactNode, ReactElement, FormEvent } from "react";
import { AlertCircle, Inbox, X } from "lucide-react";
export function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="card">
      <div className="card-heading">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Chip({ children }: { children: ReactNode }) {
  return (
    <span className={`chip ${String(children).replaceAll(" ", "_")}`}>
      {String(children).replaceAll("_", " ")}
    </span>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="empty">
      <Inbox size={28} />
      <p>{children}</p>
    </div>
  );
}
export function Loading() {
  return (
    <div role="status" aria-label="Loading" className="skeletons">
      <span />
      <span />
      <span />
    </div>
  );
}
export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="error" role="alert">
      <AlertCircle size={18} />
      <span>{message}</span>
    </div>
  );
}
export function Stat({
  label,
  value,
  note,
}: {
  label: string;
  value: ReactNode;
  note: string;
}) {
  return (
    <div className="card stat">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </div>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {cloneElement(children as ReactElement<{ id?: string }>, { id })}
    </div>
  );
}
export function DataState<T>({
  state,
  children,
}: {
  state: { data?: T; error?: string; loading: boolean };
  children: (data: T) => ReactNode;
}) {
  return state.loading ? (
    <Loading />
  ) : state.error ? (
    <ErrorMessage message={state.error} />
  ) : state.data !== undefined ? (
    children(state.data)
  ) : (
    <Empty>No data available.</Empty>
  );
}
export function ActionForm({
  onSubmit,
  children,
  label = "Save",
  success,
}: {
  onSubmit: (data: FormData) => Promise<unknown>;
  children: ReactNode;
  label?: string;
  success?: () => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [done, setDone] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setBusy(true);
    setError("");
    setDone(false);
    try {
      await onSubmit(data);
      setDone(true);
      success?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit}>
      <fieldset disabled={busy}>
        {children}
        {error && <ErrorMessage message={error} />}
        <button className="primary" type="submit">
          {busy ? "Saving…" : label}
        </button>
        {done && (
          <span className="success" role="status">
            Completed: {label}.
          </span>
        )}
      </fieldset>
    </form>
  );
}
export function Modal({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    const previous = document.activeElement as HTMLElement | null;
    dialog?.showModal();
    return () => {
      dialog?.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog ref={ref} onCancel={close} aria-label={title}>
      <div className="card-heading">
        <h2>{title}</h2>
        <button onClick={close} aria-label="Close dialog">
          <X size={18} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
