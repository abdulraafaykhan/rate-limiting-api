// ----- Shared panel headings and numeric formatting -----
export const number = (value) =>
  Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 1 });
export function SectionTitle({ eyebrow, title, children }) {
  return (
    <div className="section-title">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h2>{title}</h2>
      </div>
      {children}
    </div>
  );
}
