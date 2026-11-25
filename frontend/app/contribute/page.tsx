"use client";
import { useEffect, useState, type FormEvent } from "react";
import { clientRequest, ClientError } from "@/lib/client";

type Unit = { id: string; title: string };
type Entry = { id: string; title: string; unit_title: string; state: string; possible_duplicate: boolean; created_at: string };

const LIMIT = 6000;

export default function ContributePage() {
  const [units, setUnits] = useState<Unit[]>([]);
  const [items, setItems] = useState<Entry[]>([]);
  const [unitId, setUnitId] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [authorDeclaration, setAuthorDeclaration] = useState(false);
  const [allowDisplay, setAllowDisplay] = useState(false);
  const [allowAiUse, setAllowAiUse] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function refresh() {
    const [unitResponse, history] = await Promise.all([
      clientRequest<{items: Unit[]}>("/api/nicat/contributions/units/"),
      clientRequest<{items: Entry[]}>("/api/nicat/contributions/"),
    ]);
    setUnits(unitResponse.items);
    setItems(history.items);
  }

  useEffect(() => {
    let ignore = false;
    Promise.all([
      clientRequest<{items: Unit[]}>("/api/nicat/contributions/units/"),
      clientRequest<{items: Entry[]}>("/api/nicat/contributions/"),
    ]).then(([u, history]) => {
      if (!ignore) { setUnits(u.items); setItems(history.items); }
    }).catch((err: unknown) => {
      if (!ignore) setError(err instanceof ClientError && err.status === 404
        ? "Contributions are not enabled yet."
        : "Could not load contributions. Please sign in and try again.");
    });
    return () => { ignore = true; };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    try {
      await clientRequest<Entry>("/api/nicat/contributions/", {
        method: "POST",
        body: JSON.stringify({
          unit_id: unitId, title, body, author_declaration: authorDeclaration,
          allow_display: allowDisplay, allow_ai_use: allowAiUse,
        }),
      });
      setTitle(""); setBody(""); setAuthorDeclaration(false); setAllowDisplay(false); setAllowAiUse(false);
      setNotice("Submitted privately for rights and academic review. Not publicly visible.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit your notes.");
    } finally { setBusy(false); }
  }

  async function withdraw(id: string) {
    if (busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      await clientRequest(`/api/nicat/contributions/${encodeURIComponent(id)}/withdraw/`, { method: "POST" });
      await refresh();
      setNotice("Submission withdrawn.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not withdraw submission.");
    } finally { setBusy(false); }
  }

  return <main className="container" style={{ maxWidth: 850, margin: "0 auto", padding: 24 }}>
    <h1>Contribute revision notes</h1>
    <p className="muted">Submit your own original notes for private review. This is not an official MMU submission service. Do not upload or paste lecturer handouts, past papers, another person’s work, or personal student data.</p>
    <section className="card" style={{ padding: 20, marginTop: 20 }}>
      <h2>New contribution</h2>
      <form onSubmit={(event) => void submit(event)} style={{ display: "grid", gap: 12 }}>
        <label htmlFor="contrib-unit">Unit</label>
        <select id="contrib-unit" value={unitId} onChange={(e) => setUnitId(e.target.value)} required>
          <option value="">Select a unit</option>
          {units.map(u => <option key={u.id} value={u.id}>{u.title}</option>)}
        </select>
        <label htmlFor="contrib-title">Title</label>
        <input id="contrib-title" required minLength={5} maxLength={160} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Binary search revision notes" />
        <label htmlFor="contrib-body">Your original revision notes</label>
        <textarea id="contrib-body" rows={10} minLength={100} maxLength={LIMIT} required value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write your own explanation (100–6,000 characters)..." />
        <p className="muted tiny">{body.length} / {LIMIT} characters</p>
        <label><input type="checkbox" checked={authorDeclaration} onChange={e=>setAuthorDeclaration(e.target.checked)} required /> I wrote these notes and have the right to submit them.</label>
        <label><input type="checkbox" checked={allowDisplay} onChange={e=>setAllowDisplay(e.target.checked)} required /> I authorize NiCat to review and, only after approval, display this material.</label>
        <label><input type="checkbox" checked={allowAiUse} onChange={e=>setAllowAiUse(e.target.checked)} /> Separately, I authorize approved excerpts to be considered for AI-assisted explanations. (Optional; not enabled by this submission.)</label>
        <button type="submit" className="button" disabled={busy || !unitId || !authorDeclaration || !allowDisplay || body.length < 100}>
          {busy ? "Submitting..." : "Submit for academic review"}
        </button>
      </form>
    </section>
    {error && <p role="alert" style={{ marginTop: 16 }}>{error}</p>}
    {notice && <p role="status" style={{ marginTop: 16 }}>{notice}</p>}
    <section className="card" style={{ padding: 20, marginTop: 24 }}>
      <h2>My submissions</h2>
      {items.length === 0 ? <p className="muted">No submissions yet.</p> : <ul>
        {items.map(entry => <li key={entry.id} style={{ marginBottom: 14 }}>
          <strong>{entry.title}</strong> — {entry.unit_title}
          <p className="muted tiny">Status: {entry.state}{entry.possible_duplicate ? " (possible duplicate: staff review required)" : ""}</p>
          {entry.state !== "withdrawn" && <button type="button" className="button ghost" disabled={busy} onClick={() => void withdraw(entry.id)}>Withdraw</button>}
        </li>)}
      </ul>}
    </section>
  </main>;
}
