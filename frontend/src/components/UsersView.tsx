import { useCallback, useEffect, useState } from "react";
import { approveUser, createUser, deleteUser, listUsers } from "../api";
import type { User } from "../types";

export function UsersView() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [addEmail, setAddEmail] = useState("");
  const [addPassword, setAddPassword] = useState("");
  const [addRole, setAddRole] = useState<"user" | "admin">("user");
  const [adding, setAdding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [approvingId, setApprovingId] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await listUsers();
      setUsers(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const email = addEmail.trim();
    const password = addPassword.trim();
    if (!email || !password) {
      setError("Email and password are required.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setAdding(true);
    setError(null);
    try {
      await createUser(email, password, addRole);
      setAddEmail("");
      setAddPassword("");
      setAddRole("user");
      setShowAdd(false);
      await loadUsers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create user");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(userId: string) {
    setDeletingId(userId);
    setError(null);
    try {
      await deleteUser(userId);
      await loadUsers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete user");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleApprove(userId: string) {
    setApprovingId(userId);
    setError(null);
    try {
      await approveUser(userId);
      await loadUsers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to approve user");
    } finally {
      setApprovingId(null);
    }
  }

  return (
    <>
      <h2 className="mb-2 text-xl font-semibold text-slate-900 dark:text-white">
        User management
      </h2>
      <p className="mb-6 text-slate-600 dark:text-slate-400">
        Add or remove users. Approve pending registrations so they can log in.
      </p>

      {error && (
        <div
          className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-red-800 dark:border-red-800 dark:bg-red-900/20 dark:text-red-200"
          role="alert"
        >
          {error}
        </div>
      )}

      <div className="mb-6">
        {!showAdd ? (
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600"
          >
            Add user
          </button>
        ) : (
          <form
            onSubmit={handleAdd}
            className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-800/50"
          >
            <h3 className="mb-3 text-sm font-medium text-slate-900 dark:text-white">
              New user
            </h3>
            <div className="mb-3">
              <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">
                Email
              </label>
              <input
                type="email"
                value={addEmail}
                onChange={(e) => setAddEmail(e.target.value)}
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
                placeholder="user@example.com"
              />
            </div>
            <div className="mb-3">
              <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">
                Password (min 8)
              </label>
              <input
                type="password"
                value={addPassword}
                onChange={(e) => setAddPassword(e.target.value)}
                className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              />
            </div>
            <div className="mb-4">
              <label className="mb-1 block text-sm text-slate-600 dark:text-slate-400">
                Role
              </label>
              <select
                value={addRole}
                onChange={(e) => setAddRole(e.target.value as "user" | "admin")}
                className="rounded border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              >
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={adding}
                className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {adding ? "Adding…" : "Create"}
              </button>
              <button
                type="button"
                onClick={() => setShowAdd(false)}
                className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 dark:hover:bg-slate-600"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent dark:border-indigo-400 dark:border-t-transparent" />
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-700">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
            <thead className="bg-slate-50 dark:bg-slate-800/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
                  Email
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
                  Role
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
                  Created
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-slate-500 dark:text-slate-400">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-700 dark:bg-slate-800/30">
              {users.map((u) => (
                <tr
                  key={u.id}
                  className={u.status === "pending" ? "bg-amber-50/50 dark:bg-amber-900/10" : undefined}
                >
                  <td className="px-4 py-3 text-sm text-slate-900 dark:text-white">
                    {u.email}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600 dark:text-slate-300">
                    {u.role}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                    {u.status ?? "active"}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500 dark:text-slate-400">
                    {u.created_at ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="inline-flex gap-2">
                      {u.status === "pending" && (
                        <button
                          type="button"
                          onClick={() => handleApprove(u.id)}
                          disabled={approvingId === u.id}
                          className="text-sm font-medium text-indigo-600 hover:text-indigo-700 disabled:opacity-50 dark:text-indigo-400 dark:hover:text-indigo-300"
                        >
                          {approvingId === u.id ? "Approving…" : "Approve"}
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => handleDelete(u.id)}
                        disabled={deletingId === u.id}
                        className="text-sm font-medium text-red-600 hover:text-red-700 disabled:opacity-50 dark:text-red-400 dark:hover:text-red-300"
                      >
                        {deletingId === u.id ? "Deleting…" : "Delete"}
                      </button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
