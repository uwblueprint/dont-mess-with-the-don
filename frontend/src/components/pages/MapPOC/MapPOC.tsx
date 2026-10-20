import React, { useState } from "react";
import { Nav } from "react-bootstrap";

import MainPageButton from "../../common/MainPageButton";
import { formatEventTime } from "./EventPopupContent";
import GoogleEventMap from "./GoogleEventMap";
import LeafletEventMap from "./LeafletEventMap";
import MapLibreEventMap from "./MapLibreEventMap";
import { SAMPLE_EVENTS } from "./sampleEvents";
import { EventMapProps } from "./types";

type MapProvider = {
  key: string;
  label: string;
  Map: React.ComponentType<EventMapProps>;
};

const PROVIDERS: MapProvider[] = [
  { key: "leaflet", label: "Leaflet + OpenStreetMap", Map: LeafletEventMap },
  { key: "google", label: "Google Maps", Map: GoogleEventMap },
  { key: "maplibre", label: "MapLibre + OpenFreeMap", Map: MapLibreEventMap },
];

const MAP_HEIGHT = 600;

const MapPOC = (): React.ReactElement => {
  const [providerKey, setProviderKey] = useState(PROVIDERS[0].key);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const provider = PROVIDERS.find((p) => p.key === providerKey) ?? PROVIDERS[0];

  return (
    <div className="container-fluid py-4">
      <div className="text-center">
        <MainPageButton />
        <h1 className="mb-1 mt-3">Map POC</h1>
        <p className="text-muted">
          The same sample events rendered by each map provider.
        </p>
      </div>

      <Nav
        variant="tabs"
        className="mb-3"
        activeKey={provider.key}
        onSelect={(key) => key && setProviderKey(key)}
      >
        {PROVIDERS.map((p) => (
          <Nav.Item key={p.key}>
            <Nav.Link eventKey={p.key}>{p.label}</Nav.Link>
          </Nav.Item>
        ))}
      </Nav>

      <div className="row">
        <div className="col-lg-4 mb-3">
          <div
            className="list-group"
            style={{ maxHeight: MAP_HEIGHT, overflowY: "auto" }}
          >
            {SAMPLE_EVENTS.map((event) => (
              <button
                key={event.id}
                type="button"
                className={`list-group-item list-group-item-action ${
                  event.id === selectedEventId ? "active" : ""
                }`}
                onClick={() => setSelectedEventId(event.id)}
              >
                <div className="font-weight-bold">{event.name}</div>
                <div className="small">{event.location}</div>
                <div className="small">{formatEventTime(event)}</div>
              </button>
            ))}
          </div>
        </div>
        <div className="col-lg-8 mb-3">
          <div style={{ height: MAP_HEIGHT }}>
            <provider.Map
              key={provider.key}
              events={SAMPLE_EVENTS}
              selectedEventId={selectedEventId}
              onSelectEvent={setSelectedEventId}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default MapPOC;
