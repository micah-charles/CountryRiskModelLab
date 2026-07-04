import { useMemo, useState } from "react";
import type { ImfCountry } from "../types/dataset";
import { filterCountries } from "../utils/countrySearch";

type ImfCountrySelectorProps = {
  countries: ImfCountry[];
  lastModifiedUtc?: string | null;
  refreshing: boolean;
  onRefresh: () => void;
  selected: string[];
  setSelected: (value: string[]) => void;
};

function formatLastModified(value?: string | null): string {
  if (!value) return "Not refreshed yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function ImfCountrySelector({ countries, lastModifiedUtc, refreshing, onRefresh, selected, setSelected }: ImfCountrySelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");

  const countriesByCode = useMemo(() => new Map(countries.map((country) => [country.code, country])), [countries]);
  const selectedCountries = selected.map((code) => countriesByCode.get(code) ?? { code, name: code });
  const filteredCountries = useMemo(() => filterCountries(countries, query), [countries, query]);

  function toggle(code: string) {
    setSelected(selected.includes(code) ? selected.filter((item) => item !== code) : [...selected, code]);
  }

  function remove(code: string) {
    setSelected(selected.filter((item) => item !== code));
  }

  function selectVisible() {
    const visibleCodes = filteredCountries.map((country) => country.code);
    setSelected(Array.from(new Set([...selected, ...visibleCodes])));
  }

  return (
    <section className="panel">
      <h3>Countries</h3>
      <p className="muted">{countries.length ? `${countries.length} IMF countries and territories available from the static catalogue.` : "Loading IMF country catalogue..."}</p>
      <p className="note">Country catalogue last modified: {formatLastModified(lastModifiedUtc)}</p>
      <div className="actions">
        <button onClick={() => setIsOpen(true)}>Choose Countries</button>
        <button className="secondary" onClick={onRefresh} disabled={refreshing}>{refreshing ? "Refreshing..." : "Refresh from IMF API"}</button>
        <button className="secondary" onClick={() => setSelected([])} disabled={!selected.length}>Clear</button>
      </div>
      <div className="chips country-summary">
        {selectedCountries.map((country) => (
          <button key={country.code} className="chip selected" onClick={() => remove(country.code)} title="Remove country">
            {country.name} ({country.code})
          </button>
        ))}
        {!selectedCountries.length && <span className="empty">No countries selected.</span>}
      </div>
      {isOpen && (
        <div className="modal-backdrop" onMouseDown={() => setIsOpen(false)}>
          <section className="modal" role="dialog" aria-modal="true" aria-labelledby="country-picker-title" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h3 id="country-picker-title">Select IMF Countries</h3>
                <p className="muted">{selected.length} selected. Search by country name or IMF code.</p>
              </div>
              <button className="secondary" onClick={() => setIsOpen(false)}>Close</button>
            </div>
            <label className="field">
              <span>Search countries</span>
              <input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Example: Japan, Thailand, JPN, or THA" />
            </label>
            <p className="note">You can search one country or paste several names/codes separated by spaces, commas, or semicolons.</p>
            <div className="modal-toolbar">
              <span className="muted">{filteredCountries.length} matching countries</span>
              <div className="actions compact">
                <button className="secondary" onClick={selectVisible} disabled={!filteredCountries.length}>Select Visible</button>
                <button className="secondary" onClick={() => setSelected([])} disabled={!selected.length}>Clear All</button>
              </div>
            </div>
            <div className="country-picker-list">
              {filteredCountries.map((country) => (
                <label key={country.code} className={selected.includes(country.code) ? "country-option selected" : "country-option"}>
                  <input type="checkbox" checked={selected.includes(country.code)} onChange={() => toggle(country.code)} />
                  <span>
                    <strong>{country.name}</strong>
                    <small>{country.code}</small>
                  </span>
                </label>
              ))}
              {!filteredCountries.length && <p className="empty">No IMF countries match that search.</p>}
            </div>
          </section>
        </div>
      )}
    </section>
  );
}
