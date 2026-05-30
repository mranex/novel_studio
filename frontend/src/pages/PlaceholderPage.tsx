import { Boxes } from "lucide-react";

import { navItems, placeholders } from "../appData";
import type { PageKey } from "../types";

export function PlaceholderPage({ page }: { page: PageKey }) {
  const title = navItems.find((item) => item.key === page)?.label ?? "Page";
  return (
    <section className="page">
      <div className="page-heading">
        <span className="eyebrow">Later phase placeholder</span>
        <h1>{title}</h1>
        <p>{placeholders[page]}</p>
      </div>
      <div className="empty-panel">
        <Boxes size={32} />
        <span>Foundation view ready for later pipeline phases.</span>
      </div>
    </section>
  );
}

