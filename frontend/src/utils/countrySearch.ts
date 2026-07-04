import type { ImfCountry } from "../types/dataset";

type RankedCountry = {
  country: ImfCountry;
  score: number;
};

export function normalizeCountrySearch(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function searchTerms(query: string): string[] {
  return normalizeCountrySearch(query).split(" ").filter((term) => term.length >= 2);
}

function editDistanceWithin(left: string, right: string, maxDistance: number): boolean {
  if (Math.abs(left.length - right.length) > maxDistance) return false;

  const previous = Array.from({ length: right.length + 1 }, (_, index) => index);
  const current = Array.from({ length: right.length + 1 }, () => 0);

  for (let leftIndex = 1; leftIndex <= left.length; leftIndex += 1) {
    current[0] = leftIndex;
    let rowMinimum = current[0];

    for (let rightIndex = 1; rightIndex <= right.length; rightIndex += 1) {
      const substitutionCost = left[leftIndex - 1] === right[rightIndex - 1] ? 0 : 1;
      current[rightIndex] = Math.min(
        previous[rightIndex] + 1,
        current[rightIndex - 1] + 1,
        previous[rightIndex - 1] + substitutionCost,
      );
      rowMinimum = Math.min(rowMinimum, current[rightIndex]);
    }

    if (rowMinimum > maxDistance) return false;
    for (let index = 0; index < previous.length; index += 1) {
      previous[index] = current[index];
    }
  }

  return previous[right.length] <= maxDistance;
}

function countryScore(country: ImfCountry, query: string): number {
  const normalizedQuery = normalizeCountrySearch(query);
  if (!normalizedQuery) return 1;

  const searchable = normalizeCountrySearch(`${country.name} ${country.code}`);
  if (searchable.includes(normalizedQuery)) return 4;

  const terms = searchTerms(query);
  if (!terms.length) return 0;
  if (terms.every((term) => searchable.includes(term))) return 3;
  if (terms.length > 1 && terms.some((term) => searchable.includes(term))) return 2;

  const countryTokens = searchable.split(" ");
  const hasFuzzyMatch = terms.some((term) => {
    if (term.length < 5) return false;
    const maxDistance = term.length >= 6 ? 2 : 1;
    return countryTokens.some((token) => token.length >= 4 && editDistanceWithin(term, token, maxDistance));
  });

  return hasFuzzyMatch ? 1 : 0;
}

export function filterCountries(countries: ImfCountry[], query: string): ImfCountry[] {
  const normalizedQuery = normalizeCountrySearch(query);
  if (!normalizedQuery) return countries;

  return countries
    .map<RankedCountry>((country) => ({ country, score: countryScore(country, query) }))
    .filter((item) => item.score > 0)
    .sort((left, right) => {
      if (right.score !== left.score) return right.score - left.score;
      return left.country.name.localeCompare(right.country.name);
    })
    .map((item) => item.country);
}
