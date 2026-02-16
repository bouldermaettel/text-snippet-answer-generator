import { useRef, useState, useEffect } from "react";

type Props = {
  groups: string[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  id?: string;
  disabled?: boolean;
  onClose?: () => void;
  /** Called only when user selects an option from the list (not on every keystroke). */
  onSelect?: (value: string) => void;
};

const UNGROUPED_LABEL = "(ungrouped)";

export function GroupSelector({
  groups,
  value,
  onChange,
  placeholder = "e.g. Policies",
  id = "snippet-group",
  disabled,
  onClose,
  onSelect,
}: Props) {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState(value === "" ? "" : value);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setInputValue(value === "" ? "" : value);
  }, [value]);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        onClose?.();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, onClose]);

  const displayValue = value === "" ? "" : value;
  const normalizedGroups = groups.filter((g) => g !== undefined);
  const showNewOption =
    inputValue.trim() !== "" &&
    !normalizedGroups.includes(inputValue.trim()) &&
    inputValue.trim() !== value;

  function handleSelect(selected: string) {
    const raw = selected === UNGROUPED_LABEL ? "" : selected;
    onChange(raw);
    setInputValue(raw);
    setOpen(false);
    onSelect?.(raw);
    onClose?.();
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value;
    setInputValue(v);
    onChange(v.trim() || "");
  }

  function handleFocus() {
    setOpen(true);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      setOpen(false);
      onClose?.();
      return;
    }
    if (e.key === "Enter") {
      if (open) {
        e.preventDefault();
        const trimmed = inputValue.trim();
        handleSelect(trimmed === "" ? UNGROUPED_LABEL : trimmed);
      } else {
        setOpen(true);
      }
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        id={id}
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onFocus={handleFocus}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
        className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
      />
      {open && (
        <ul
          className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-600 dark:bg-slate-800"
          role="listbox"
        >
          <li
            role="option"
            aria-selected={displayValue === ""}
            className="cursor-pointer px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
            onClick={() => handleSelect(UNGROUPED_LABEL)}
          >
            {UNGROUPED_LABEL}
          </li>
          {normalizedGroups.map((g) => (
            <li
              key={g || "(empty)"}
              role="option"
              aria-selected={value === g}
              className="cursor-pointer px-3 py-2 text-sm text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
              onClick={() => handleSelect(g)}
            >
              {g || UNGROUPED_LABEL}
            </li>
          ))}
          {showNewOption && (
            <li
              role="option"
              className="cursor-pointer px-3 py-2 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-700"
              onClick={() => handleSelect(inputValue.trim())}
            >
              Use &quot;{inputValue.trim()}&quot; as new group
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
