import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';

interface McpDropdownItem<T extends string> {
  id: T;
  label: string;
  group?: string;
  icon?: string;
}

interface McpSetupDropdownProps<T extends string> {
  label: string;
  value: T;
  items: McpDropdownItem<T>[];
  onChange: (value: T) => void;
  searchPlaceholder?: string;
}

function McpSetupDropdown<T extends string>({
  label,
  value,
  items,
  onChange,
  searchPlaceholder = 'Search...',
}: McpSetupDropdownProps<T>) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = items.find((item) => item.id === value) ?? items[0];

  useEffect(() => {
    if (!open) return undefined;

    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', closeOnOutsideClick);
    document.addEventListener('keydown', closeOnEscape);
    return () => {
      document.removeEventListener('mousedown', closeOnOutsideClick);
      document.removeEventListener('keydown', closeOnEscape);
    };
  }, [open]);

  const filteredGroups = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const matches = normalizedQuery
      ? items.filter((item) => item.label.toLowerCase().includes(normalizedQuery))
      : items;

    return matches.reduce<Record<string, McpDropdownItem<T>[]>>((groups, item) => {
      const group = item.group ?? 'Options';
      return { ...groups, [group]: [...(groups[group] ?? []), item] };
    }, {});
  }, [items, query]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="h-9 min-w-[210px] inline-flex items-center gap-2 rounded-md border border-lp-border bg-surface px-3 text-left shadow-sm transition-colors hover:border-text-tertiary focus:outline-none focus-visible:ring-1 focus-visible:ring-text-primary"
      >
        <span className="font-sans text-[12px] text-text-tertiary">{label}</span>
        <span className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-sm bg-bg border border-lp-border font-mono text-[8px] text-text-secondary">
          {selected.icon ?? selected.label.slice(0, 1)}
        </span>
        <span className="font-sans text-[14px] text-text-primary truncate">{selected.label}</span>
        <ChevronDown className={`ml-auto h-3.5 w-3.5 text-text-tertiary transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute left-0 z-30 mt-1 w-[248px] overflow-hidden rounded-md border border-lp-border bg-[#242222] text-[#f3f0eb] shadow-2xl">
          <div className="flex items-center gap-2 border-b border-white/10 px-3 py-2">
            <Search className="h-3.5 w-3.5 text-white/35" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              autoFocus
              placeholder={searchPlaceholder}
              className="min-w-0 flex-1 bg-transparent font-sans text-[13px] text-white/80 placeholder:text-white/35 focus:outline-none"
            />
          </div>

          <div className="max-h-[320px] overflow-y-auto py-2" role="listbox">
            {Object.entries(filteredGroups).map(([group, groupItems]) => (
              <div key={group}>
                <div className="px-3 pb-1 pt-2 font-mono text-[10px] uppercase tracking-widest text-white/25">
                  {group}
                </div>
                {groupItems.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    role="option"
                    aria-selected={item.id === value}
                    onClick={() => {
                      onChange(item.id);
                      setOpen(false);
                      setQuery('');
                    }}
                    className={`flex w-full items-center gap-2 px-3 py-2 text-left font-sans text-[13px] transition-colors ${
                      item.id === value ? 'bg-white/5 text-white' : 'text-white/65 hover:bg-white/5 hover:text-white'
                    }`}
                  >
                    <span className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-white/15 bg-black/20 font-mono text-[8px] text-white/75">
                      {item.icon ?? item.label.slice(0, 1)}
                    </span>
                    <span className="min-w-0 flex-1 truncate">{item.label}</span>
                    {item.id === value && <Check className="h-3.5 w-3.5 text-white/70" />}
                  </button>
                ))}
              </div>
            ))}
            {Object.keys(filteredGroups).length === 0 && (
              <div className="px-3 py-5 text-center font-sans text-[13px] text-white/40">
                No matches
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default McpSetupDropdown;
