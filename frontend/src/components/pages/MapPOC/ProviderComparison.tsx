import React from "react";

// Pricing and free tiers change often; check each provider's pricing page
// before relying on these for a production decision.
type ComparisonRow = {
  label: string;
  leaflet: string;
  google: string;
  maplibre: string;
};

const ROWS: ComparisonRow[] = [
  {
    label: "API key",
    leaflet: "None",
    google:
      "Required for production (needs a Google Cloud billing account). Keyless only in watermarked dev mode.",
    maplibre: "None with OpenFreeMap",
  },
  {
    label: "Cost",
    leaflet: "Free, open source",
    google: "Free monthly usage, then pay per map load",
    maplibre: "Free, open source; OpenFreeMap is donation-funded",
  },
  {
    label: "Production tiles",
    leaflet:
      "OSM's public tile server is not for production traffic; needs a tile provider (e.g. MapTiler, Stadia)",
    google: "Included",
    maplibre:
      "OpenFreeMap (no SLA), a paid vector tile provider, or self-hosted tiles",
  },
  {
    label: "Geocoding / place search",
    leaflet: "Not included; needs a separate service",
    google: "Best-in-class Geocoding and Places APIs (billed separately)",
    maplibre: "Not included; needs a separate service",
  },
  {
    label: "Look and styling",
    leaflet: "Raster tiles; styling limited to the tile provider",
    google: "Familiar Google look; cloud styling via map IDs",
    maplibre: "Smooth vector maps; fully customizable style JSON",
  },
  {
    label: "Bundle size (gzip)",
    leaflet: "~41 KB",
    google: "~21 KB wrapper; Maps JS loads from Google at runtime",
    maplibre: "~206 KB",
  },
  {
    label: "React integration",
    leaflet: "react-leaflet: mature and simple",
    google: "@vis.gl/react-google-maps: maintained with Google",
    maplibre: "react-map-gl: same API as Mapbox, easy to switch",
  },
];

const ProviderComparison = (): React.ReactElement => (
  <div className="mt-4">
    <h4>Provider comparison</h4>
    <div className="table-responsive">
      <table className="table table-sm table-bordered small">
        <thead className="thead-light">
          <tr>
            <th scope="col" aria-label="Criteria" />
            <th scope="col">Leaflet + OpenStreetMap</th>
            <th scope="col">Google Maps</th>
            <th scope="col">MapLibre + OpenFreeMap</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.label}>
              <th scope="row">{row.label}</th>
              <td>{row.leaflet}</td>
              <td>{row.google}</td>
              <td>{row.maplibre}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

export default ProviderComparison;
