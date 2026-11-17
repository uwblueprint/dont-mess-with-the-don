import "maplibre-gl/dist/maplibre-gl.css";
import React, { useEffect, useRef } from "react";
import Map, {
  MapRef,
  Marker,
  NavigationControl,
  Popup,
} from "react-map-gl/maplibre";

import EventPopupContent from "./EventPopupContent";
import { EventMapProps } from "./types";

// OpenFreeMap serves free vector tiles with no API key. Swapping to Mapbox
// later is mostly changing the import to react-map-gl/mapbox and adding a
// token.
const MAP_STYLE = "https://tiles.openfreemap.org/styles/liberty";

const SELECTED_ZOOM = 14;
const MARKER_COLOR = "#e31d24";

const MapLibreEventMap = ({
  events,
  selectedEventId,
  onSelectEvent,
}: EventMapProps): React.ReactElement => {
  const mapRef = useRef<MapRef>(null);
  const selectedEvent = events.find((e) => e.id === selectedEventId);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedEvent) return;
    map.flyTo({
      center: [selectedEvent.lng, selectedEvent.lat],
      zoom: Math.max(map.getZoom(), SELECTED_ZOOM),
    });
  }, [selectedEvent]);

  const lats = events.map((e) => e.lat);
  const lngs = events.map((e) => e.lng);

  return (
    <Map
      ref={mapRef}
      initialViewState={{
        bounds: [
          [Math.min(...lngs), Math.min(...lats)],
          [Math.max(...lngs), Math.max(...lats)],
        ],
        fitBoundsOptions: { padding: 40 },
      }}
      mapStyle={MAP_STYLE}
      style={{ height: "100%", width: "100%" }}
    >
      <NavigationControl position="top-left" />
      {events.map((event) => (
        <Marker
          key={event.id}
          longitude={event.lng}
          latitude={event.lat}
          anchor="bottom"
          color={MARKER_COLOR}
          onClick={(e) => {
            // Keep the click from reaching the map, which would close the popup.
            e.originalEvent.stopPropagation();
            onSelectEvent(event.id);
          }}
        />
      ))}
      {selectedEvent && (
        <Popup
          key={selectedEvent.id}
          longitude={selectedEvent.lng}
          latitude={selectedEvent.lat}
          anchor="bottom"
          offset={48}
          maxWidth="300px"
          onClose={() => onSelectEvent(null)}
        >
          <EventPopupContent event={selectedEvent} />
        </Popup>
      )}
    </Map>
  );
};

export default MapLibreEventMap;
