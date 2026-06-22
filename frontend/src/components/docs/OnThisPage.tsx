import React from 'react';

export interface TocItem {
  id: string;
  label: string;
  children?: TocItem[];
}

interface OnThisPageProps {
  items: TocItem[];
  activeId: string;
}

const TocLink: React.FC<{ item: TocItem; activeId: string; depth: number }> = ({ item, activeId, depth }) => (
  <>
    <li>
      <a
        href={`#${item.id}`}
        className={`block py-1 font-sans text-[13px] leading-5 transition-colors ${
          activeId === item.id
            ? 'text-[var(--docs-accent)] font-medium'
            : 'text-text-tertiary hover:text-text-primary'
        }`}
        style={{ paddingLeft: depth * 12 }}
      >
        {item.label}
      </a>
    </li>
    {item.children?.map((child) => (
      <TocLink key={child.id} item={child} activeId={activeId} depth={depth + 1} />
    ))}
  </>
);

const OnThisPage: React.FC<OnThisPageProps> = ({ items, activeId }) => (
  <aside className="hidden xl:block w-52 shrink-0">
    <nav className="sticky top-10">
      <div className="font-sans text-[11px] font-semibold uppercase tracking-wide text-text-tertiary mb-3">
        On this page
      </div>
      <ul className="space-y-0.5">
        {items.map((item) => (
          <TocLink key={item.id} item={item} activeId={activeId} depth={0} />
        ))}
      </ul>
    </nav>
  </aside>
);

export default OnThisPage;
