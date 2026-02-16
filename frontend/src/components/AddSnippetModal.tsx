import { useRef, useState } from "react";
import { uploadSnippets } from "../api";
import { AddSnippetForm } from "./AddSnippetForm";

type Props = { onClose: () => void; onAdded: () => void; defaultGroup?: string; groups: string[] };

export function AddSnippetModal({ onClose, onAdded, defaultGroup, groups }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [uploadMessage, setUploadMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [anonymize, setAnonymize] = useState(false);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>, group?: string) {
    const files = e.target.files;
    if (!files?.length) return;
    setUploadMessage(null);
    setUploading(true);
    try {
      const list = Array.from(files).filter(
        (f) =>
          f.name.toLowerCase().endsWith(".txt") ||
          f.name.toLowerCase().endsWith(".docx") ||
          f.name.toLowerCase().endsWith(".pdf")
      );
      if (list.length === 0) {
        setUploadMessage({ type: "err", text: "Select .txt, .docx, or .pdf files only." });
        setUploading(false);
        return;
      }
      const result = await uploadSnippets(list, group, anonymize);
      setUploadMessage({
        type: "ok",
        text: `Added ${result.count} snippet(s) from files.${anonymize ? " (PII anonymized)" : ""}${result.errors?.length ? ` ${result.errors.join(" ")}` : ""}`,
      });
      onAdded();
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (folderInputRef.current) folderInputRef.current.value = "";
    } catch (err) {
      setUploadMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Upload failed.",
      });
    } finally {
      setUploading(false);
    }
  }

  function handleFolderChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files?.length) return;
    const group =
      (files[0] as File & { webkitRelativePath?: string }).webkitRelativePath?.split("/")[0] ?? undefined;
    handleFileChange(e, group);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-snippet-modal-title"
    >
      <div
        className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-700">
          <h2 id="add-snippet-modal-title" className="text-lg font-semibold text-slate-900 dark:text-white">
            Add snippet
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-700 dark:hover:text-slate-300"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="space-y-6 px-6 py-4">
          <AddSnippetForm onAdded={onAdded} defaultGroup={defaultGroup} groups={groups} />
          <div className="border-t border-slate-200 pt-4 dark:border-slate-700">
            <p className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
              Or upload documents (.txt, .docx, or .pdf)
            </p>
            <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
              Each file becomes one snippet; the filename (without extension) is used as the title.
            </p>
            <label className="mb-3 flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={anonymize}
                onChange={(e) => setAnonymize(e.target.checked)}
                className="h-4 w-4 rounded border-slate-300 text-slate-700 focus:ring-slate-500 dark:border-slate-600 dark:bg-slate-700"
              />
              <span>Anonymize PII</span>
              <span className="text-xs text-slate-500 dark:text-slate-400">
                (names, addresses, companies, etc.)
              </span>
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.docx,.pdf"
              multiple
              onChange={(e) => handleFileChange(e)}
              disabled={uploading}
              className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-slate-700 dark:text-slate-400 file:dark:bg-slate-700 file:dark:text-slate-200"
            />
            <p className="mb-2 mt-4 text-sm font-medium text-slate-700 dark:text-slate-300">
              Or upload from a folder
            </p>
            <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
              Snippets will be assigned to a group named after the folder.
            </p>
            <input
              ref={folderInputRef}
              type="file"
              accept=".txt,.docx,.pdf"
              multiple
              {...({ webkitdirectory: "" } as React.InputHTMLAttributes<HTMLInputElement>)}
              onChange={handleFolderChange}
              disabled={uploading}
              className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-slate-700 dark:text-slate-400 file:dark:bg-slate-700 file:dark:text-slate-200"
            />
            {uploadMessage && (
              <p
                className={
                  uploadMessage.type === "ok"
                    ? "text-sm text-emerald-600 dark:text-emerald-400"
                    : "text-sm text-red-600 dark:text-red-400"
                }
              >
                {uploadMessage.text}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
